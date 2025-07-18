import sys
import os
import ffmpeg
from PyQt5.QtWidgets import (
    QWidget, QLabel, QPushButton, QVBoxLayout, QHBoxLayout, QListWidget, QListWidgetItem,
    QMessageBox, QFileDialog, QApplication
)
from PyQt5.QtCore import Qt

class window1(QWidget):
    def __init__(self, input_file, target_format):
        super().__init__()
        self.setWindowTitle("单轨道格式打包")
        self.resize(600, 400)
        self.input_file = input_file
        self.target_format = target_format
        self.output_file = None

        self.video_list = QListWidget()
        self.audio_list = QListWidget()
        self.video_list.setSelectionMode(QListWidget.SingleSelection)
        self.audio_list.setSelectionMode(QListWidget.SingleSelection)

        self.init_ui()
        self.load_tracks()

    def init_ui(self):
        file_label = QLabel(f"输入文件: {os.path.abspath(self.input_file)}")
        format_label = QLabel(f"目标格式: {self.target_format}")

        video_col = QVBoxLayout()
        video_col.addWidget(QLabel("视频轨道"))
        video_col.addWidget(self.video_list)

        audio_col = QVBoxLayout()
        audio_col.addWidget(QLabel("音频轨道"))
        audio_col.addWidget(self.audio_list)

        tracks_line = QHBoxLayout()
        tracks_line.addLayout(video_col)
        tracks_line.addLayout(audio_col)

        self.select_output_btn = QPushButton("选择输出文件")
        self.select_output_btn.clicked.connect(self.select_output_file)
        self.output_label = QLabel("未选择输出文件")

        self.confirm_btn = QPushButton("开始打包")
        self.confirm_btn.clicked.connect(self.remux)

        layout = QVBoxLayout()
        layout.addWidget(file_label)
        layout.addWidget(format_label)
        layout.addLayout(tracks_line)
        layout.addWidget(self.select_output_btn)
        layout.addWidget(self.output_label)
        layout.addWidget(self.confirm_btn)
        layout.addStretch()
        self.setLayout(layout)

    def load_tracks(self):
        self.video_list.clear()
        self.audio_list.clear()
        try:
            info = ffmpeg.probe(self.input_file)
            for stream in info.get('streams', []):
                idx = stream.get('index', -1)
                codec = stream.get('codec_name', '未知')
                lang = stream.get('tags', {}).get('language', '')
                desc = f"#{idx} {codec} {lang}".strip()
                item = QListWidgetItem(desc)
                item.setData(Qt.UserRole, idx)
                if stream['codec_type'] == 'video':
                    self.video_list.addItem(item)
                elif stream['codec_type'] == 'audio':
                    self.audio_list.addItem(item)
        except Exception as e:
            QMessageBox.warning(self, "错误", f"无法解析轨道信息：{e}")

    def select_output_file(self):
        file, _ = QFileDialog.getSaveFileName(self, "选择输出文件", os.path.splitext(self.input_file)[0] + f"_single.{self.target_format}", f"*.{self.target_format}")
        if file:
            self.output_file = file
            self.output_label.setText(f"输出文件: {os.path.abspath(file)}")

    def remux(self):
        if not self.output_file:
            QMessageBox.warning(self, "提示", "请先选择输出文件")
            return
        video_items = self.video_list.selectedItems()
        audio_items = self.audio_list.selectedItems()
        if not video_items or not audio_items:
            QMessageBox.warning(self, "提示", "请各选择一个视频和音频轨道")
            return
        v_idx = video_items[0].data(Qt.UserRole)
        a_idx = audio_items[0].data(Qt.UserRole)
        try:
            info = ffmpeg.probe(self.input_file)
            v_codec = None
            a_codec = None
            for stream in info.get('streams', []):
                if stream['codec_type'] == 'video' and stream.get('index', -1) == v_idx:
                    v_codec = stream.get('codec_name', '').lower()
                if stream['codec_type'] == 'audio' and stream.get('index', -1) == a_idx:
                    a_codec = stream.get('codec_name', '').lower()
            # 目标编码判断
            target_fmt = self.target_format.lower()
            # avi: 视频mpeg4/xvid/divx，音频mp3/ac3
            # wmv: 视频wmv1/wmv2/wmv3，音频wmav1/wmav2
            need_vcodec = None
            need_acodec = None
            if target_fmt == 'avi':
                if v_codec not in ('mpeg4', 'msmpeg4v2', 'msmpeg4v3', 'xvid', 'divx'):
                    need_vcodec = 'mpeg4'
                if a_codec not in ('mp3', 'ac3'):
                    need_acodec = 'mp3'
            elif target_fmt == 'wmv':
                if v_codec not in ('wmv1', 'wmv2', 'wmv3'):
                    need_vcodec = 'wmv2'
                if a_codec not in ('wmav1', 'wmav2'):
                    need_acodec = 'wmav2'
            # 构建ffmpeg命令
            cmd = [
                'ffmpeg', '-y', '-i', self.input_file,
                '-map', f'0:v:{self._stream_subidx(v_idx, "video")}',
                '-map', f'0:a:{self._stream_subidx(a_idx, "audio")}'
            ]
            if need_vcodec:
                cmd += ['-c:v', need_vcodec]
            else:
                cmd += ['-c:v', 'copy']
            if need_acodec:
                cmd += ['-c:a', need_acodec]
            else:
                cmd += ['-c:a', 'copy']
            cmd += [self.output_file]
            ret = os.system(' '.join([f'"{c}"' if ' ' in str(c) else str(c) for c in cmd]))
            if ret == 0:
                QMessageBox.information(self, "成功", "打包完成！")
            else:
                QMessageBox.warning(self, "失败", "打包失败，请检查文件和格式。")
        except Exception as e:
            QMessageBox.warning(self, "错误", f"打包出错：{e}")

    def _stream_subidx(self, idx, typ):
        try:
            info = ffmpeg.probe(self.input_file)
            subidx = -1
            for stream in info.get('streams', []):
                if stream['codec_type'] == typ:
                    subidx += 1
                if stream.get('index', -1) == idx:
                    return subidx
            return 0
        except:
            return 0

# 测试用
if __name__ == "__main__":
    app = QApplication(sys.argv)
    w = window1("test.mkv", "avi")
    w.show()
    sys.exit(app.exec_())
