import sys
from PyQt5.QtWidgets import (
    QApplication, QWidget, QLabel, QPushButton, QVBoxLayout,
    QFileDialog, QComboBox, QMessageBox
)
from PyQt5.QtCore import QThread, pyqtSignal
import ffmpeg
import os

class ExtractThread(QThread):
    finished = pyqtSignal(bool, str)

    def __init__(self, input_file, track_index, output_file, output_format):
        super().__init__()
        self.input_file = input_file
        self.track_index = track_index
        self.output_file = output_file
        self.output_format = output_format

    def run(self):
        try:
            # 提取指定音轨
            stream = ffmpeg.input(self.input_file)
            audio = stream.audio.filter('atrim', start=0)
            (
                ffmpeg
                .output(stream['a:{}'.format(self.track_index)], self.output_file, format=self.output_format)
                .run(overwrite_output=True)
            )
            self.finished.emit(True, self.output_file)
        except Exception as e:
            self.finished.emit(False, str(e))

class AudioExtractor(QWidget):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("音轨提取器")
        self.resize(500, 400)

        self.input_file = ""
        self.audio_tracks = []
        self.selected_track = 0
        self.supported_formats = ["mp3", "aac", "wav", "flac", "m4a", "ogg"]

        self.label = QLabel("选择要提取音轨的视频文件")
        self.select_btn = QPushButton("选择文件")
        self.select_btn.clicked.connect(self.select_file)

        self.track_label = QLabel("选择音轨")
        self.track_combo = QComboBox()

        self.format_label = QLabel("选择导出格式")
        self.format_combo = QComboBox()
        self.format_combo.addItems(self.supported_formats)

        self.extract_btn = QPushButton("开始提取")
        self.extract_btn.clicked.connect(self.extract_audio)

        layout = QVBoxLayout()
        layout.addWidget(self.label)
        layout.addWidget(self.select_btn)
        layout.addWidget(self.track_label)
        layout.addWidget(self.track_combo)
        layout.addWidget(self.format_label)
        layout.addWidget(self.format_combo)
        layout.addWidget(self.extract_btn)
        layout.addStretch()
        self.setLayout(layout)

    def select_file(self):
        file, _ = QFileDialog.getOpenFileName(self, "选择视频文件", "", "视频文件 (*.mp4 *.avi *.mov *.mkv *.flv *.wmv)")
        if file:
            self.input_file = file
            self.label.setText(f"已选择文件: {os.path.basename(file)}")
            self.list_audio_tracks()

    def list_audio_tracks(self):
        # 使用 ffprobe 获取音轨信息
        try:
            probe = ffmpeg.probe(self.input_file)
            self.audio_tracks = [
                stream for stream in probe['streams'] if stream['codec_type'] == 'audio'
            ]
            self.track_combo.clear()
            for idx, track in enumerate(self.audio_tracks):
                lang = track.get('tags', {}).get('language', '未知')
                codec = track.get('codec_name', '未知')
                desc = f"音轨{idx+1} - {codec} ({lang})"
                self.track_combo.addItem(desc, idx)
            if not self.audio_tracks:
                self.track_combo.addItem("未检测到音轨")
        except Exception as e:
            QMessageBox.critical(self, "错误", f"无法读取音轨信息: {e}")

    def extract_audio(self):
        if not self.input_file or not self.audio_tracks:
            QMessageBox.warning(self, "警告", "请先选择包含音轨的视频文件！")
            return
        track_index = self.track_combo.currentData()
        if track_index is None:
            QMessageBox.warning(self, "警告", "请选择有效的音轨！")
            return
        output_format = self.format_combo.currentText()
        base, _ = os.path.splitext(self.input_file)
        output_file = f"{base}_track{track_index+1}.{output_format}"

        self.extract_btn.setEnabled(False)
        self.thread = ExtractThread(self.input_file, track_index, output_file, output_format)
        self.thread.finished.connect(self.on_extract_finished)
        self.thread.start()

    def on_extract_finished(self, success, info):
        self.extract_btn.setEnabled(True)
        if success:
            QMessageBox.information(self, "成功", f"音轨提取完成！输出文件：{info}")
        else:
            QMessageBox.critical(self, "错误", f"提取失败：{info}")

if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = AudioExtractor()
    window.show()
    sys.exit(app.exec_())