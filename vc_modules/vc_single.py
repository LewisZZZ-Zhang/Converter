import sys
import os
import subprocess, json
from PyQt5.QtWidgets import (
    QWidget, QLabel, QPushButton, QVBoxLayout, QHBoxLayout, QListWidget, QListWidgetItem,
    QMessageBox, QFileDialog, QApplication, QProgressBar
)
from PyQt5.QtCore import Qt

from vc_modules.ffmpeg_progress import (
    FFmpegWorker,
    MediaInfoWorker,
    probe_duration,
)
from vc_modules.bin_info import detect_binary_info, get_bin_path
from vc_modules.debug_section import DebugSection
from vc_modules.media_utils import build_audio_stream_desc, build_video_stream_desc

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
        ffmpeg_info = detect_binary_info("ffmpeg")
        ffprobe_info = detect_binary_info("ffprobe")
        self.debug_section = DebugSection(
            f"ffmpeg: {ffmpeg_info['arch']}  {ffmpeg_info['path']}\n"
            f"ffprobe: {ffprobe_info['arch']}  {ffprobe_info['path']}",
            self,
        )

        video_col = QVBoxLayout()
        video_col.addWidget(QLabel("视频轨道"))
        video_col.addWidget(self.video_list)

        audio_col = QVBoxLayout()
        audio_col.addWidget(QLabel("音频轨道"))
        audio_col.addWidget(self.audio_list)

        tracks_line = QHBoxLayout()
        tracks_line.addLayout(video_col)
        tracks_line.addLayout(audio_col)

        self.select_output_btn = QPushButton("更改输出文件")
        self.select_output_btn.clicked.connect(self.select_output_file)
        self.output_file = self._default_output_file()
        self.output_label = QLabel(f"输出文件: {os.path.abspath(self.output_file)}")

        self.confirm_btn = QPushButton("开始打包")
        self.confirm_btn.clicked.connect(self.remux)
        self.confirm_btn.setEnabled(False)
        self.select_output_btn.setEnabled(False)

        self.progress_bar = QProgressBar()
        self.progress_bar.setRange(0, 100)
        self.progress_bar.setValue(0)
        self.progress_bar.setVisible(False)

        self.status_label = QLabel("")
        self.status_label.setVisible(False)

        layout = QVBoxLayout()
        layout.addWidget(file_label)
        layout.addWidget(format_label)
        layout.addLayout(tracks_line)
        layout.addWidget(self.select_output_btn)
        layout.addWidget(self.output_label)
        layout.addWidget(self.confirm_btn)
        layout.addWidget(self.progress_bar)
        layout.addWidget(self.status_label)
        layout.addStretch()
        layout.addWidget(self.debug_section)
        self.setLayout(layout)

    def load_tracks(self):
        self.video_list.clear()
        self.audio_list.clear()
        self.video_list.setEnabled(False)
        self.audio_list.setEnabled(False)
        self.progress_bar.setVisible(True)
        self.progress_bar.setRange(0, 0)
        self.status_label.setVisible(True)
        self.status_label.setText("正在加载轨道信息，请稍候...")

        self.media_worker = MediaInfoWorker(self.input_file, parent=self)
        self.media_worker.status_changed.connect(self.status_label.setText)
        self.media_worker.finished.connect(self.on_tracks_loaded)
        self.media_worker.start()

    def on_tracks_loaded(self, success, payload, err_msg):
        self.progress_bar.setVisible(False)
        self.progress_bar.setRange(0, 100)
        self.progress_bar.setValue(0)

        if not success:
            self.status_label.setText("轨道信息加载失败")
            QMessageBox.warning(self, "错误", f"无法解析轨道信息：{err_msg}")
            return

        for stream in payload.get('streams', []):
            idx = stream.get('index', -1)
            if stream['codec_type'] == 'video':
                item = QListWidgetItem(build_video_stream_desc(stream))
                item.setData(Qt.UserRole, idx)
                self.video_list.addItem(item)
            elif stream['codec_type'] == 'audio':
                item = QListWidgetItem(build_audio_stream_desc(stream))
                item.setData(Qt.UserRole, idx)
                self.audio_list.addItem(item)

        self.video_list.setEnabled(True)
        self.audio_list.setEnabled(True)
        self.select_output_btn.setEnabled(True)
        self.confirm_btn.setEnabled(True)
        self.status_label.setText("轨道信息加载完成")

    def select_output_file(self):
        file, _ = QFileDialog.getSaveFileName(
            self,
            "选择输出文件",
            self.output_file,
            f"*.{self.target_format}",
        )
        if file:
            self.output_file = file
            self.output_label.setText(f"输出文件: {os.path.abspath(file)}")

    def _default_output_file(self):
        base, _ = os.path.splitext(self.input_file)
        return f"{base}_single.{self.target_format}"

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
        ffprobe_path = get_bin_path('ffprobe')
        cmd_probe = [ffprobe_path, '-v', 'error', '-show_streams', '-print_format', 'json', self.input_file]
        try:
            result = subprocess.run(cmd_probe, stdout=subprocess.PIPE, stderr=subprocess.PIPE, check=True)
            info = json.loads(result.stdout.decode(errors='ignore'))
            v_codec = None
            a_codec = None
            for stream in info.get('streams', []):
                if stream['codec_type'] == 'video' and stream.get('index', -1) == v_idx:
                    v_codec = stream.get('codec_name', '').lower()
                if stream['codec_type'] == 'audio' and stream.get('index', -1) == a_idx:
                    a_codec = stream.get('codec_name', '').lower()
            target_fmt = self.target_format.lower()
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
            ffmpeg_path = get_bin_path('ffmpeg')
            cmd = [
                ffmpeg_path, '-y', '-i', self.input_file,
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
            self._start_ffmpeg_job(cmd)
        except Exception as e:
            err_msg = str(e)
            if hasattr(e, 'stderr') and e.stderr:
                err_msg += f"\nffprobe stderr:\n{e.stderr.decode(errors='ignore') if hasattr(e.stderr, 'decode') else str(e.stderr)}"
            QMessageBox.warning(self, "错误", f"打包出错：{err_msg}")

    def _stream_subidx(self, idx, typ):
        ffprobe_path = get_bin_path('ffprobe')
        cmd = [ffprobe_path, '-v', 'error', '-show_streams', '-print_format', 'json', self.input_file]
        try:
            result = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, check=True)
            info = json.loads(result.stdout.decode(errors='ignore'))
            subidx = -1
            for stream in info.get('streams', []):
                if stream['codec_type'] == typ:
                    subidx += 1
                if stream.get('index', -1) == idx:
                    return subidx
            return 0
        except:
            return 0

    def _start_ffmpeg_job(self, cmd):
        duration = probe_duration(self.input_file)
        self.confirm_btn.setEnabled(False)
        self.select_output_btn.setEnabled(False)
        self.video_list.setEnabled(False)
        self.audio_list.setEnabled(False)
        self.progress_bar.setVisible(True)
        self.status_label.setVisible(True)
        self.status_label.setText("正在启动转换...")

        if duration:
            self.progress_bar.setRange(0, 100)
            self.progress_bar.setValue(0)
        else:
            self.progress_bar.setRange(0, 0)

        self.worker = FFmpegWorker(cmd, self.output_file, duration_seconds=duration, parent=self)
        self.worker.progress_changed.connect(self.on_progress_changed)
        self.worker.status_changed.connect(self.status_label.setText)
        self.worker.finished.connect(self.on_remux_finished)
        self.worker.start()

    def on_progress_changed(self, value):
        if self.progress_bar.maximum() == 0:
            self.progress_bar.setRange(0, 100)
        self.progress_bar.setValue(value)
        self.status_label.setText(f"正在转换... {value}%")

    def on_remux_finished(self, success, message):
        self.confirm_btn.setEnabled(True)
        self.select_output_btn.setEnabled(True)
        self.video_list.setEnabled(True)
        self.audio_list.setEnabled(True)
        self.progress_bar.setRange(0, 100)
        self.status_label.setVisible(True)

        if success:
            self.progress_bar.setValue(100)
            self.status_label.setText("转换完成")
            QMessageBox.information(self, "成功", f"打包完成！\n输出文件：{message}")
        else:
            self.progress_bar.setValue(0)
            self.status_label.setText("转换失败")
            QMessageBox.warning(self, "失败", f"打包失败，请检查文件和格式。\n{message}")

# 测试用
if __name__ == "__main__":
    app = QApplication(sys.argv)
    w = window1("test.mkv", "avi")
    w.show()
    sys.exit(app.exec_())
