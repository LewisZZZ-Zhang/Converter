
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
    detect_binary_info,
    get_bin_path,
    probe_duration,
)
from vc_modules.media_utils import (
    build_audio_stream_desc,
    build_subtitle_stream_desc,
    build_video_stream_desc,
)

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
        ffmpeg_info = detect_binary_info("ffmpeg")
        binary_label = QLabel(
            f"当前 ffmpeg: {ffmpeg_info['arch']}  ({os.path.basename(ffmpeg_info['path'])})"
        )
        binary_label.setWordWrap(True)

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

        self.select_output_btn = QPushButton("更改输出文件")
        self.select_output_btn.clicked.connect(self.select_output_file)
        self.output_file = self._default_output_file()
        self.output_label = QLabel(f"输出文件: {os.path.abspath(self.output_file)}")

        self.confirm_btn = QPushButton("开始重新打包")
        self.confirm_btn.clicked.connect(self.remux)
        self.confirm_btn.setEnabled(False)
        self.select_output_btn.setEnabled(False)
        self.add_sub_btn.setEnabled(False)

        self.progress_bar = QProgressBar()
        self.progress_bar.setRange(0, 100)
        self.progress_bar.setValue(0)
        self.progress_bar.setVisible(False)

        self.status_label = QLabel("")
        self.status_label.setVisible(False)

        layout = QVBoxLayout()
        layout.addWidget(file_label)
        layout.addWidget(format_label)
        layout.addWidget(binary_label)
        layout.addLayout(tracks_line)
        layout.addWidget(self.select_output_btn)
        layout.addWidget(self.output_label)
        layout.addWidget(self.confirm_btn)
        layout.addWidget(self.progress_bar)
        layout.addWidget(self.status_label)
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
        self.video_list.setEnabled(False)
        self.audio_list.setEnabled(False)
        self.subtitle_list.setEnabled(False)
        self.custom_sub_list.setEnabled(False)
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

        target_fmt = self.target_format.lower()
        for stream in payload.get('streams', []):
            idx = stream.get('index', -1)
            codec = stream.get('codec_name', '未知')
            if stream['codec_type'] == 'video':
                item = QListWidgetItem(build_video_stream_desc(stream))
                item.setData(Qt.UserRole, idx)
                if codec == 'mjpeg':
                    item.setFlags(item.flags() & ~Qt.ItemIsSelectable & ~Qt.ItemIsEnabled)
                    item.setText(item.text() + " (图片流,不可选)")
                self.video_list.addItem(item)
            elif stream['codec_type'] == 'audio':
                item = QListWidgetItem(build_audio_stream_desc(stream))
                item.setData(Qt.UserRole, idx)
                self.audio_list.addItem(item)
            elif stream['codec_type'] == 'subtitle':
                item = QListWidgetItem(build_subtitle_stream_desc(stream))
                item.setData(Qt.UserRole, idx)
                if codec in ('hdmv_pgs_subtitle', 'pgssub') and target_fmt == 'mp4':
                    item.setFlags(item.flags() & ~Qt.ItemIsSelectable & ~Qt.ItemIsEnabled)
                    item.setText(item.text() + " (PGS字幕,mp4不支持)")
                self.subtitle_list.addItem(item)

        self.video_list.setEnabled(True)
        self.audio_list.setEnabled(True)
        self.subtitle_list.setEnabled(True)
        self.custom_sub_list.setEnabled(True)
        self.select_output_btn.setEnabled(True)
        self.confirm_btn.setEnabled(True)
        self.add_sub_btn.setEnabled(True)
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
        return f"{base}_remux.{self.target_format}"

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
        target_fmt = self.target_format.lower()
        for f, codec in [c[:2] for c in custom_subs]:
            if target_fmt == 'mp4' and codec in ('pgs', 'vobsub'):
                QMessageBox.warning(self, "不支持的字幕", f"{os.path.basename(f)} 为PGS/VobSub字幕，mp4不支持。请移除。")
                return
        ffprobe_path = get_bin_path('ffprobe')
        cmd_probe = [ffprobe_path, '-v', 'error', '-show_streams', '-print_format', 'json', self.input_file]
        try:
            result = subprocess.run(cmd_probe, stdout=subprocess.PIPE, stderr=subprocess.PIPE, check=True)
            info = json.loads(result.stdout.decode(errors='ignore'))
            stream_by_index = {
                stream.get('index', -1): stream
                for stream in info.get('streams', [])
            }
            subtitle_codecs = []
            for idx in subtitle_idxs:
                stream = stream_by_index.get(idx, {})
                subtitle_codecs.append(stream.get('codec_name', 'unknown'))

            mp4_supported_audio_codecs = {'aac', 'alac', 'ac3', 'eac3', 'mp3', 'mp2'}
            audio_transcode_jobs = []
            for out_audio_idx, idx in enumerate(audio_idxs):
                stream = stream_by_index.get(idx, {})
                codec_name = stream.get('codec_name', 'unknown').lower()
                if target_fmt != 'mp4' or codec_name in mp4_supported_audio_codecs:
                    continue

                try:
                    channels = int(stream.get('channels', 2) or 2)
                except (TypeError, ValueError):
                    channels = 2

                if channels >= 6:
                    bitrate = '384k'
                elif channels >= 3:
                    bitrate = '256k'
                else:
                    bitrate = '192k'

                audio_transcode_jobs.append((out_audio_idx, bitrate))

            stream_args = []
            for idx in video_idxs:
                stream_args += ['-map', f'0:v:{self._stream_subidx(idx, "video")}' ]
            for idx in audio_idxs:
                stream_args += ['-map', f'0:a:{self._stream_subidx(idx, "audio")}' ]
            need_transcode_sub = []
            for i, idx in enumerate(subtitle_idxs):
                stream_args += ['-map', f'0:s:{self._stream_subidx(idx, "subtitle")}' ]
                if target_fmt == 'mp4' and subtitle_codecs[i] != 'mov_text':
                    need_transcode_sub.append(i)
            input_files = [self.input_file] + [c[0] for c in custom_subs]
            for i, (f, codec) in enumerate(custom_subs):
                if target_fmt == 'mp4' and codec in ('pgs', 'vobsub'):
                    continue
                stream_args += ['-map', f'{i+1}:0']
                if target_fmt == 'mp4':
                    need_transcode_sub.append(len(subtitle_idxs) + i)

            ffmpeg_path = get_bin_path('ffmpeg')
            cmd = [ffmpeg_path, '-y']
            for f in input_files:
                cmd += ['-i', f]
            cmd += stream_args

            if target_fmt == 'mp4' and (subtitle_idxs or custom_subs):
                cmd += ['-c', 'copy']
                for i in need_transcode_sub:
                    cmd += [f'-c:s:{i}', 'mov_text']
                for out_audio_idx, bitrate in audio_transcode_jobs:
                    cmd += [f'-c:a:{out_audio_idx}', 'aac', f'-b:a:{out_audio_idx}', bitrate]
                cmd += [self.output_file]
            elif target_fmt == 'mp4' and audio_transcode_jobs:
                cmd += ['-c', 'copy']
                for out_audio_idx, bitrate in audio_transcode_jobs:
                    cmd += [f'-c:a:{out_audio_idx}', 'aac', f'-b:a:{out_audio_idx}', bitrate]
                cmd += [self.output_file]
            else:
                cmd += ['-c', 'copy', self.output_file]
            self._start_ffmpeg_job(cmd)
        except Exception as e:
            err_msg = str(e)
            if hasattr(e, 'stderr') and e.stderr:
                err_msg += f"\nffprobe stderr:\n{e.stderr.decode(errors='ignore') if hasattr(e.stderr, 'decode') else str(e.stderr)}"
            QMessageBox.warning(self, "错误", f"重新打包出错：{err_msg}")

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
        self.add_sub_btn.setEnabled(False)
        self.video_list.setEnabled(False)
        self.audio_list.setEnabled(False)
        self.subtitle_list.setEnabled(False)
        self.custom_sub_list.setEnabled(False)
        self.progress_bar.setVisible(True)
        self.status_label.setVisible(True)
        self.status_label.setText("正在启动重新打包...")

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
        self.status_label.setText(f"正在重新打包... {value}%")

    def on_remux_finished(self, success, message):
        self.confirm_btn.setEnabled(True)
        self.select_output_btn.setEnabled(True)
        self.add_sub_btn.setEnabled(True)
        self.video_list.setEnabled(True)
        self.audio_list.setEnabled(True)
        self.subtitle_list.setEnabled(True)
        self.custom_sub_list.setEnabled(True)
        self.progress_bar.setRange(0, 100)
        self.status_label.setVisible(True)

        if success:
            self.progress_bar.setValue(100)
            self.status_label.setText("重新打包完成")
            QMessageBox.information(self, "成功", f"重新打包完成！\n输出文件：{message}")
        else:
            self.progress_bar.setValue(0)
            self.status_label.setText("重新打包失败")
            QMessageBox.warning(self, "失败", f"重新打包失败，请检查文件和格式。\n{message}")

# 测试用
if __name__ == "__main__":
    app = QApplication(sys.argv)
    # 这里请替换为实际文件和格式
    w = window1("test.mp4", "mkv")
    w.show()
    sys.exit(app.exec_())
