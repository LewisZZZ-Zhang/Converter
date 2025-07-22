
def get_ffprobe_path():
    import sys, os
    if getattr(sys, 'frozen', False):
        # PyInstaller打包后
        return os.path.join(sys._MEIPASS, 'bin', 'ffprobe')
    else:
        # 开发环境
        return os.path.join(os.path.dirname(__file__), 'bin', 'ffprobe')
    
import sys
from PyQt5.QtWidgets import (
    QApplication, QWidget, QLabel, QPushButton, QVBoxLayout,
    QFileDialog, QComboBox, QMessageBox, QHBoxLayout, QListWidget, QGroupBox
)
from PyQt5.QtCore import QThread, pyqtSignal
# import ffmpeg
import os

class vc_pre(QWidget):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("视频格式转换")
        self.resize(800, 600)

        self.supported_formats = ["mp4", "avi", "mov", "mkv", "wmv"]
        self.single_track_formats = ["avi", "wmv"]
        self.multi_track_formats = ["mp4", "mov", "mkv"]

        self.input_file = None 

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

        self.confirm_btn = QPushButton("确认")
        self.confirm_btn.clicked.connect(self.go_to_confirm_page)

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
        layout.addLayout(tracks_line)
        layout.addLayout(output_format_line)
        layout.addWidget(self.confirm_btn)
        layout.addStretch()
        self.setLayout(layout)

    def select_file(self):
        file, _ = QFileDialog.getOpenFileName(self, "选择视频文件", "", "视频文件 (*.mp4 *.avi *.mov *.mkv *.flv *.wmv)")
        if file:
            self.input_file = file
            # self.select_result.setText(f"已选择文件: {os.path.basename(file)}")
            self.input_select_result.setText(f"已选择文件: {os.path.abspath(file)}")
            self.update_track_lists(file)

    def update_track_lists(self, file):
        import subprocess, json
        self.video_list.clear()
        self.audio_list.clear()
        self.subtitle_list.clear()
        self.summary_label.setText("")
        ffprobe_path = get_ffprobe_path()
        cmd_streams = [ffprobe_path, '-v', 'error', '-show_streams', '-print_format', 'json', file]
        cmd_format = [ffprobe_path, '-v', 'error', '-show_format', '-print_format', 'json', file]
        try:
            # 获取流信息
            result_streams = subprocess.run(cmd_streams, stdout=subprocess.PIPE, stderr=subprocess.PIPE, check=True)
            info_streams = json.loads(result_streams.stdout.decode(errors='ignore'))
            # 获取文件整体信息
            result_format = subprocess.run(cmd_format, stdout=subprocess.PIPE, stderr=subprocess.PIPE, check=True)
            info_format = json.loads(result_format.stdout.decode(errors='ignore'))

            # 总比特率
            overall_bitrate = info_format.get('format', {}).get('bit_rate', '')
            if overall_bitrate:
                try:
                    overall_bitrate_disp = f"{int(overall_bitrate)//1000} kbps"
                except:
                    overall_bitrate_disp = str(overall_bitrate)
            else:
                overall_bitrate_disp = ''

            # 分辨率和色彩深度（取第一个视频流）
            width = height = pix_fmt = color_depth = ''
            for stream in info_streams.get('streams', []):
                if stream.get('codec_type') == 'video':
                    width = stream.get('width', '')
                    height = stream.get('height', '')
                    pix_fmt = stream.get('pix_fmt', '')
                    color_depth = stream.get('bits_per_raw_sample', '')
                    break

            # 色彩深度补充（部分视频流可能没有 bits_per_raw_sample）
            if not color_depth and pix_fmt:
                # 常见像素格式推断色深
                pix_fmt_map = {
                    'yuv420p': '8', 'yuv422p': '8', 'yuv444p': '8',
                    'yuv420p10le': '10', 'yuv422p10le': '10', 'yuv444p10le': '10',
                    'yuv420p12le': '12', 'yuv422p12le': '12', 'yuv444p12le': '12',
                }
                color_depth = pix_fmt_map.get(pix_fmt, '')

            summary = f"总比特率: {overall_bitrate_disp}"
            if width and height:
                summary += f"  分辨率: {width}x{height}"
            if color_depth:
                summary += f"  色深: {color_depth}bit"
            if pix_fmt:
                summary += f"  像素格式: {pix_fmt}"
            self.summary_label.setText(summary)

            for stream in info_streams.get('streams', []):
                codec = stream.get('codec_name', '未知')
                idx = stream.get('index', -1)
                lang = stream.get('tags', {}).get('language', '')
                if stream['codec_type'] == 'video':
                    fr = stream.get('r_frame_rate', '')
                    try:
                        if fr and '/' in fr:
                            num, den = fr.split('/')
                            fr_val = float(num) / float(den) if float(den) != 0 else 0
                        else:
                            fr_val = float(fr) if fr else 0
                    except:
                        fr_val = 0
                    width = stream.get('width', '')
                    height = stream.get('height', '')
                    br = stream.get('bit_rate', '')
                    if not br:
                        br = stream.get('tags', {}).get('BPS', '')
                    if br:
                        try:
                            br_disp = f"{int(br)//1000} kbps"
                        except:
                            br_disp = str(br)
                    else:
                        br_disp = ''
                    desc = f"#{idx} {codec} {lang} {width}x{height} {fr_val:.2f}fps {br_disp}".strip()
                    self.video_list.addItem(desc)
                elif stream['codec_type'] == 'audio':
                    sr = stream.get('sample_rate', '')
                    ch = stream.get('channels', '')
                    br = stream.get('bit_rate', '')
                    if not br:
                        br = stream.get('tags', {}).get('BPS', '')
                    if br:
                        try:
                            br_disp = f"{int(br)//1000} kbps"
                        except:
                            br_disp = str(br)
                    else:
                        br_disp = ''
                    desc = f"#{idx} {codec} {lang} {sr}Hz {ch}ch {br_disp}".strip()
                    self.audio_list.addItem(desc)
                elif stream['codec_type'] == 'subtitle':
                    desc = f"#{idx} {codec} {lang}".strip()
                    self.subtitle_list.addItem(desc)
        except Exception as e:
            err_msg = str(e)
            if hasattr(e, 'stderr') and e.stderr:
                err_msg += f"\nffprobe stderr:\n{e.stderr.decode(errors='ignore') if hasattr(e.stderr, 'decode') else str(e.stderr)}"
            elif isinstance(e, subprocess.CalledProcessError):
                err_msg += f"\nffprobe stderr:\n{e.stderr.decode(errors='ignore') if hasattr(e.stderr, 'decode') else str(e.stderr)}"
            self.summary_label.setText("")
            QMessageBox.warning(self, "错误", f"无法解析轨道信息：{err_msg}")

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