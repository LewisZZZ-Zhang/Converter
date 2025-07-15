import sys
from PyQt5.QtWidgets import (
    QApplication, QWidget, QLabel, QVBoxLayout, QListWidget, QHBoxLayout, QListWidgetItem, QPushButton, QMessageBox
)
from PyQt5.QtCore import Qt
import ffmpeg
import os

class window1(QWidget):
    def __init__(self, input_file, target_format):
        super().__init__()
        self.setWindowTitle("视频格式转换")
        self.resize(800, 600)
        self.input_file = input_file
        self.target_format = target_format

        self.conversion_hint = QLabel(f"{input_file} => {target_format}")

        # 多选列表
        self.video_list = QListWidget()
        self.video_list.setSelectionMode(QListWidget.MultiSelection)
        self.audio_list = QListWidget()
        self.audio_list.setSelectionMode(QListWidget.MultiSelection)
        self.subtitle_list = QListWidget()
        self.subtitle_list.setSelectionMode(QListWidget.MultiSelection)

        # 标题
        video_label = QLabel("选择要打包的视频轨道")
        video_label.setStyleSheet("font-weight: bold; margin-bottom: 4px;")
        audio_label = QLabel("选择要打包的音频轨道")
        audio_label.setStyleSheet("font-weight: bold; margin-bottom: 4px;")
        subtitle_label = QLabel("选择要打包的字幕轨道")
        subtitle_label.setStyleSheet("font-weight: bold; margin-bottom: 4px;")

        # 横向布局
        tracks_line = QHBoxLayout()
        video_col = QVBoxLayout()
        video_col.addWidget(video_label)
        video_col.addWidget(self.video_list)
        audio_col = QVBoxLayout()
        audio_col.addWidget(audio_label)
        audio_col.addWidget(self.audio_list)
        subtitle_col = QVBoxLayout()
        subtitle_col.addWidget(subtitle_label)
        subtitle_col.addWidget(self.subtitle_list)
        tracks_line.addLayout(video_col)
        tracks_line.addLayout(audio_col)
        tracks_line.addLayout(subtitle_col)

        # 新增：开始转换按钮
        self.start_btn = QPushButton("开始转换")
        self.start_btn.clicked.connect(self.start_conversion)

        layout = QVBoxLayout()
        layout.addWidget(self.conversion_hint)
        layout.addLayout(tracks_line)
        layout.addWidget(self.start_btn)  # 添加按钮
        layout.addStretch()
        self.setLayout(layout)

        self.populate_tracks()

    def populate_tracks(self):
        # 填充轨道信息
        self.video_list.clear()
        self.audio_list.clear()
        self.subtitle_list.clear()
        try:
            info = ffmpeg.probe(self.input_file)
            for stream in info.get('streams', []):
                codec = stream.get('codec_name', '未知')
                idx = stream.get('index', -1)
                lang = stream.get('tags', {}).get('language', '')
                desc = f"#{idx} {codec} {lang}".strip()
                item = QListWidgetItem(desc)
                item.setCheckState(Qt.Checked)  # 默认选中
                if stream['codec_type'] == 'video':
                    self.video_list.addItem(item)
                elif stream['codec_type'] == 'audio':
                    self.audio_list.addItem(item)
                elif stream['codec_type'] == 'subtitle':
                    self.subtitle_list.addItem(item)
        except Exception as e:
            self.conversion_hint.setText(f"轨道信息读取失败：{e}")

    def start_conversion(self):
        selected_video_idx = self._checked_indexes(self.video_list)
        selected_audio_idx = self._checked_indexes(self.audio_list)
        selected_subtitle_idx = self._checked_indexes(self.subtitle_list)

        if not (selected_video_idx or selected_audio_idx or selected_subtitle_idx):
            QMessageBox.warning(self, "提示", "请至少选择一个轨道！")
            return

        # 输出文件名
        base, _ = os.path.splitext(self.input_file)
        output_file = f"{base}_selected.{self.target_format}"

        # 构造 map 参数
        maps = []
        for idx in selected_video_idx + selected_audio_idx + selected_subtitle_idx:
            maps.extend(['-map', f'0:{idx}'])

        # ffmpeg-python 构造输入和输出
# ...existing code...
        try:
            stream = ffmpeg.input(self.input_file)
            # 用 global_args 传递所有 -map 参数
            stream = ffmpeg.output(stream, output_file)
            stream = stream.global_args(*maps)
            stream = stream.overwrite_output()
            stream.run()
            QMessageBox.information(self, "成功", f"转换完成！输出文件：{output_file}")
        except Exception as e:
            QMessageBox.critical(self, "错误", f"转换失败：{e}")
# ...existing code...
        
    def _checked_indexes(self, qlistwidget):
    # 返回用户勾选的轨道编号（index）
        indexes = []
        for i in range(qlistwidget.count()):
            item = qlistwidget.item(i)
            if item.checkState() == Qt.Checked:
                # 轨道描述如 "#0 h264 und"，取 #0 里的数字
                idx = int(item.text().split()[0][1:])
                indexes.append(idx)
        return indexes


if __name__ == "__main__":
    app = QApplication(sys.argv)
    # 传入示例参数
    window = window1("/Users/Lewis/Movies/gqx10.mkv", "mkv")
    window.show()
    sys.exit(app.exec_())