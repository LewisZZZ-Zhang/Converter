import sys
from PyQt5.QtWidgets import (
    QApplication, QWidget, QLabel, QPushButton, QVBoxLayout,
    QFileDialog, QComboBox, QMessageBox, QHBoxLayout, QListWidget,
    QProgressBar
)
from PyQt5.QtCore import Qt
import os

from vc_modules.ffmpeg_progress import MediaInfoWorker
from vc_modules.bin_info import detect_binary_info, get_bin_path
from vc_modules.debug_section import DebugSection
from vc_modules.media_details_dialog import MediaDetailsDialog
from vc_modules.media_utils import (
    build_audio_stream_desc,
    build_subtitle_stream_desc,
    build_summary,
    build_video_stream_desc,
)

class vc_pre(QWidget):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("视频格式转换")
        self.resize(800, 600)

        self.supported_formats = ["mp4", "avi", "mov", "mkv", "wmv"]
        self.single_track_formats = ["avi", "wmv"]
        self.multi_track_formats = ["mp4", "mov", "mkv"]

        self.input_file = None 
        self.media_payload = None

        self.input_select_instruction = QLabel("选择要转换的视频文件")
        self.input_select_btn = QPushButton("选择文件")
        self.input_select_btn.clicked.connect(self.select_file)
        self.input_select_result = QLabel("未选择文件")
        self.input_select_result.setWordWrap(True)

        # 新增：视频总信息显示区
        self.summary_label = QLabel("")
        self.summary_label.setWordWrap(True)

        self.format_label = QLabel("选择输出格式")
        self.format_combo = QComboBox()
        self.format_combo.addItems(self.supported_formats)


        self.video_list = QListWidget()
        self.audio_list = QListWidget()
        self.subtitle_list = QListWidget()

        self.loading_label = QLabel("")
        self.loading_label.setVisible(False)
        self.loading_progress = QProgressBar()
        self.loading_progress.setRange(0, 0)
        self.loading_progress.setVisible(False)

        ffmpeg_info = detect_binary_info("ffmpeg")
        ffprobe_info = detect_binary_info("ffprobe")
        self.debug_section = DebugSection(
            f"ffmpeg: {ffmpeg_info['arch']}  {ffmpeg_info['path']}\n"
            f"ffprobe: {ffprobe_info['arch']}  {ffprobe_info['path']}",
            self,
        )

        self.confirm_btn = QPushButton("确认")
        self.confirm_btn.clicked.connect(self.go_to_confirm_page)
        self.confirm_btn.setEnabled(False)
        self.details_btn = QPushButton("查看详情")
        self.details_btn.clicked.connect(self.show_details)
        self.details_btn.setEnabled(False)

# 新增：三个列表和分组框
        video_col = QVBoxLayout()
        video_label = QLabel("视频轨道")
        video_label.setStyleSheet("font-weight: bold; margin-bottom: 4px;")
        video_col.addWidget(video_label)
        video_col.addWidget(self.video_list)

        audio_col = QVBoxLayout()
        audio_label = QLabel("音频轨道")
        audio_label.setStyleSheet("font-weight: bold; margin-bottom: 4px;")
        audio_col.addWidget(audio_label)
        audio_col.addWidget(self.audio_list)

        subtitle_col = QVBoxLayout()
        subtitle_label = QLabel("字幕轨道")
        subtitle_label.setStyleSheet("font-weight: bold; margin-bottom: 4px;")
        subtitle_col.addWidget(subtitle_label)
        subtitle_col.addWidget(self.subtitle_list)

        tracks_line = QHBoxLayout()
        tracks_line.setSpacing(16)
        tracks_line.addLayout(video_col)
        tracks_line.addLayout(audio_col)
        tracks_line.addLayout(subtitle_col)

        file_input_line = QHBoxLayout()
        file_input_line.addWidget(self.input_select_instruction)
        file_input_line.addWidget(self.input_select_btn)

        output_format_line = QHBoxLayout()
        output_format_line.addWidget(self.format_label)
        output_format_line.addWidget(self.format_combo)

        layout = QVBoxLayout()
        layout.addLayout(file_input_line)
        layout.addWidget(self.input_select_result)
        layout.addWidget(self.summary_label)  # 新增：总信息显示区
        layout.addWidget(self.loading_label)
        layout.addWidget(self.loading_progress)
        layout.addLayout(tracks_line)
        layout.addLayout(output_format_line)
        layout.addWidget(self.details_btn)
        layout.addWidget(self.confirm_btn)
        layout.addStretch()
        layout.addWidget(self.debug_section)
        self.setLayout(layout)

    def select_file(self):
        file, _ = QFileDialog.getOpenFileName(self, "选择视频文件", "", "视频文件 (*.mp4 *.avi *.mov *.mkv *.flv *.wmv)")
        if file:
            self.input_file = file
            # self.select_result.setText(f"已选择文件: {os.path.basename(file)}")
            self.input_select_result.setText(f"已选择文件: {os.path.abspath(file)}")
            self.update_track_lists(file)

    def update_track_lists(self, file):
        self.video_list.clear()
        self.audio_list.clear()
        self.subtitle_list.clear()
        self.summary_label.setText("")
        self.media_payload = None
        self.input_select_btn.setEnabled(False)
        self.format_combo.setEnabled(False)
        self.confirm_btn.setEnabled(False)
        self.details_btn.setEnabled(False)
        self.loading_label.setText("正在加载轨道信息，请稍候...")
        self.loading_label.setVisible(True)
        self.loading_progress.setVisible(True)

        self.media_worker = MediaInfoWorker(file, include_format=True, parent=self)
        self.media_worker.status_changed.connect(self.loading_label.setText)
        self.media_worker.finished.connect(self.on_track_lists_loaded)
        self.media_worker.start()

    def on_track_lists_loaded(self, success, payload, err_msg):
        self.input_select_btn.setEnabled(True)
        self.format_combo.setEnabled(True)
        self.loading_progress.setVisible(False)

        if not success:
            self.loading_label.setVisible(False)
            self.summary_label.setText("")
            QMessageBox.warning(self, "错误", f"无法解析轨道信息：{err_msg}")
            return

        self.media_payload = payload
        info_streams = payload
        info_format = payload

        self.summary_label.setText(build_summary(info_streams, info_format))

        for stream in info_streams.get('streams', []):
            if stream['codec_type'] == 'video':
                self.video_list.addItem(build_video_stream_desc(stream))
            elif stream['codec_type'] == 'audio':
                self.audio_list.addItem(build_audio_stream_desc(stream))
            elif stream['codec_type'] == 'subtitle':
                self.subtitle_list.addItem(build_subtitle_stream_desc(stream))

        self.loading_label.setText("轨道信息加载完成")
        self.confirm_btn.setEnabled(True)
        self.details_btn.setEnabled(True)

    def show_details(self):
        if not self.input_file or not self.media_payload:
            QMessageBox.information(self, "提示", "请先选择并解析一个视频文件。")
            return
        dialog = MediaDetailsDialog(self.input_file, self.media_payload, self)
        dialog.exec_()

    def go_to_confirm_page(self):
        if not hasattr(self, "input_file") or not self.input_file:
            QMessageBox.warning(self, "提示", "请先选择文件")
            return
        file_ext = os.path.splitext(self.input_file)[1][1:].lower()
        target_format = self.format_combo.currentText().lower()

        # 跳转到不同的模块窗口（假设这些类在其他文件中定义）
        if target_format in self.multi_track_formats:
            from vc_modules.vc_multi import window1 as sub_window1
            self.next_page = sub_window1(self.input_file, target_format)
        elif target_format in self.single_track_formats:
            from vc_modules.vc_single import window1 as sub_window2
            self.next_page = sub_window2(self.input_file, target_format)
        # else:
        #     from page_transcode import PageTranscode
        #     self.next_page = PageTranscode(self.input_file, target_format)

        self.next_page.show()
        self.close()


if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = vc_pre()
    window.show()
    sys.exit(app.exec_())
