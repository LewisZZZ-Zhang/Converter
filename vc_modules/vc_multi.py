
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
        self.setWindowTitle("多轨道重新打包")
        self.resize(800, 600)
        self.input_file = input_file
        self.target_format = target_format
        self.output_file = None

        self.video_list = QListWidget()
        self.audio_list = QListWidget()
        self.subtitle_list = QListWidget()
        self.video_list.setSelectionMode(QListWidget.MultiSelection)
        self.audio_list.setSelectionMode(QListWidget.MultiSelection)
        self.subtitle_list.setSelectionMode(QListWidget.MultiSelection)

        self.custom_subs = []  # [(path, desc, codec)]
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

        subtitle_col = QVBoxLayout()
        subtitle_col.addWidget(QLabel("字幕轨道"))
        subtitle_col.addWidget(self.subtitle_list)

        # 新增：自定义字幕添加按钮和列表
        self.add_sub_btn = QPushButton("添加外部字幕文件")
        self.add_sub_btn.clicked.connect(self.add_custom_sub)
        self.custom_sub_list = QListWidget()
        self.custom_sub_list.setSelectionMode(QListWidget.MultiSelection)

        subtitle_col.addWidget(self.add_sub_btn)
        subtitle_col.addWidget(QLabel("已添加外部字幕："))
        subtitle_col.addWidget(self.custom_sub_list)

        tracks_line = QHBoxLayout()
        tracks_line.addLayout(video_col)
        tracks_line.addLayout(audio_col)
        tracks_line.addLayout(subtitle_col)

        self.select_output_btn = QPushButton("选择输出文件")
        self.select_output_btn.clicked.connect(self.select_output_file)
        self.output_label = QLabel("未选择输出文件")

        self.confirm_btn = QPushButton("开始重新打包")
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
    def add_custom_sub(self):
        files, _ = QFileDialog.getOpenFileNames(self, "选择字幕文件", "", "字幕文件 (*.srt *.ass *.ssa *.vtt *.sub *.sup *.pgs *.idx *.txt)")
        if not files:
            return
        target_fmt = self.target_format.lower()
        for f in files:
            ext = os.path.splitext(f)[1].lower()
            # 简单判断字幕类型
            if ext in ['.srt', '.ass', '.ssa', '.vtt', '.sub', '.txt']:
                codec = 'text'
            elif ext in ['.sup', '.pgs']:
                codec = 'pgs'
            elif ext == '.idx':
                codec = 'vobsub'
            else:
                codec = 'unknown'
            # mp4不支持pgs/vobsub
            if target_fmt == 'mp4' and codec in ('pgs', 'vobsub'):
                QMessageBox.warning(self, "不支持的字幕", f"{os.path.basename(f)} 为PGS/VobSub字幕，mp4不支持，未添加。")
                continue
            desc = f"{os.path.basename(f)} ({codec})"
            item = QListWidgetItem(desc)
            item.setData(Qt.UserRole, (f, codec))
            self.custom_sub_list.addItem(item)
            self.custom_subs.append((f, desc, codec))

    def load_tracks(self):
        self.video_list.clear()
        self.audio_list.clear()
        self.subtitle_list.clear()
        try:
            info = ffmpeg.probe(self.input_file)
            target_fmt = self.target_format.lower()
            for stream in info.get('streams', []):
                idx = stream.get('index', -1)
                codec = stream.get('codec_name', '未知')
                lang = stream.get('tags', {}).get('language', '')
                desc = f"#{idx} {codec} {lang}".strip()
                item = QListWidgetItem(desc)
                item.setData(Qt.UserRole, idx)
                # 视频流：mjpeg为封面图片，禁用
                if stream['codec_type'] == 'video':
                    if codec == 'mjpeg':
                        item.setFlags(item.flags() & ~Qt.ItemIsSelectable & ~Qt.ItemIsEnabled)
                        item.setText(desc + " (图片流,不可选)")
                    self.video_list.addItem(item)
                # 音频流
                elif stream['codec_type'] == 'audio':
                    self.audio_list.addItem(item)
                # 字幕流：PGS字幕且目标为mp4时禁用
                elif stream['codec_type'] == 'subtitle':
                    if codec in ('hdmv_pgs_subtitle', 'pgssub') and target_fmt == 'mp4':
                        item.setFlags(item.flags() & ~Qt.ItemIsSelectable & ~Qt.ItemIsEnabled)
                        item.setText(desc + " (PGS字幕,mp4不支持)")
                    self.subtitle_list.addItem(item)
        except Exception as e:
            QMessageBox.warning(self, "错误", f"无法解析轨道信息：{e}")

    def select_output_file(self):
        file, _ = QFileDialog.getSaveFileName(self, "选择输出文件", os.path.splitext(self.input_file)[0] + f"_remux.{self.target_format}", f"*.{self.target_format}")
        if file:
            self.output_file = file
            self.output_label.setText(f"输出文件: {os.path.abspath(file)}")

    def remux(self):
        if not self.output_file:
            QMessageBox.warning(self, "提示", "请先选择输出文件")
            return
        video_idxs = [item.data(Qt.UserRole) for item in self.video_list.selectedItems()]
        audio_idxs = [item.data(Qt.UserRole) for item in self.audio_list.selectedItems()]
        subtitle_idxs = [item.data(Qt.UserRole) for item in self.subtitle_list.selectedItems()]
        custom_sub_items = [self.custom_sub_list.item(i) for i in range(self.custom_sub_list.count()) if self.custom_sub_list.item(i).isSelected()]
        custom_subs = [item.data(Qt.UserRole) for item in custom_sub_items]
        if not (video_idxs or audio_idxs or subtitle_idxs or custom_subs):
            QMessageBox.warning(self, "提示", "请至少选择一个轨道或外部字幕")
            return
        # 检查外部字幕兼容性
        target_fmt = self.target_format.lower()
        for f, codec in [c[:2] for c in custom_subs]:
            if target_fmt == 'mp4' and codec in ('pgs', 'vobsub'):
                QMessageBox.warning(self, "不支持的字幕", f"{os.path.basename(f)} 为PGS/VobSub字幕，mp4不支持。请移除。")
                return
        try:
            # 获取原视频所有字幕流的codec
            info = ffmpeg.probe(self.input_file)
            subtitle_codecs = []  # 与subtitle_idxs顺序一致
            for idx in subtitle_idxs:
                for stream in info.get('streams', []):
                    if stream['codec_type'] == 'subtitle' and stream.get('index', -1) == idx:
                        subtitle_codecs.append(stream.get('codec_name', 'unknown'))
                        break
                else:
                    subtitle_codecs.append('unknown')

            stream_args = []
            for idx in video_idxs:
                stream_args += ['-map', f'0:v:{self._stream_subidx(idx, "video")}' ]
            for idx in audio_idxs:
                stream_args += ['-map', f'0:a:{self._stream_subidx(idx, "audio")}' ]
            # 记录需要转码的字幕流序号
            need_transcode_sub = []
            for i, idx in enumerate(subtitle_idxs):
                stream_args += ['-map', f'0:s:{self._stream_subidx(idx, "subtitle")}' ]
                if target_fmt == 'mp4' and subtitle_codecs[i] != 'mov_text':
                    need_transcode_sub.append(i)
            # 外部字幕追加为新输入
            input_files = [self.input_file] + [c[0] for c in custom_subs]
            # map外部字幕
            for i, (f, codec) in enumerate(custom_subs):
                if target_fmt == 'mp4' and codec in ('pgs', 'vobsub'):
                    continue
                stream_args += ['-map', f'{i+1}:0']
                if target_fmt == 'mp4':
                    need_transcode_sub.append(len(subtitle_idxs) + i)

            # 构建ffmpeg命令
            cmd = ['ffmpeg', '-y']
            for f in input_files:
                cmd += ['-i', f]
            cmd += stream_args

            # 生成-c参数
            if target_fmt == 'mp4' and (subtitle_idxs or custom_subs):
                # -c copy -c:s mov_text 或 -c:s:0 mov_text -c:s:1 mov_text ...
                cmd += ['-c', 'copy']
                for i in need_transcode_sub:
                    cmd += [f'-c:s:{i}', 'mov_text']
                cmd += [self.output_file]
            else:
                cmd += ['-c', 'copy', self.output_file]

            ret = os.system(' '.join([f'"{c}"' if ' ' in str(c) else str(c) for c in cmd]))
            if ret == 0:
                QMessageBox.information(self, "成功", "重新打包完成！")
            else:
                QMessageBox.warning(self, "失败", "重新打包失败，请检查文件和格式。")
        except Exception as e:
            QMessageBox.warning(self, "错误", f"重新打包出错：{e}")

    def _stream_subidx(self, idx, typ):
        # 计算同类型流的子序号
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
    # 这里请替换为实际文件和格式
    w = window1("test.mp4", "mkv")
    w.show()
    sys.exit(app.exec_())
