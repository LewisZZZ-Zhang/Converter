import sys
import os
import subprocess, json
def get_bin_path(bin_name):
    import sys, os
    if getattr(sys, 'frozen', False):
        return os.path.join(sys._MEIPASS, 'bin', bin_name)
    else:
        return os.path.join(os.path.dirname(__file__), '..', 'bin', bin_name)
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
        ffprobe_path = get_bin_path('ffprobe')
        cmd = [ffprobe_path, '-v', 'error', '-show_streams', '-print_format', 'json', self.input_file]
        try:
            result = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, check=True)
            info = json.loads(result.stdout.decode(errors='ignore'))
            for stream in info.get('streams', []):
                idx = stream.get('index', -1)
                codec = stream.get('codec_name', '未知')
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
                    item = QListWidgetItem(desc)
                    item.setData(Qt.UserRole, idx)
                    self.video_list.addItem(item)
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
                    item = QListWidgetItem(desc)
                    item.setData(Qt.UserRole, idx)
                    self.audio_list.addItem(item)
        except Exception as e:
            err_msg = str(e)
            if hasattr(e, 'stderr') and e.stderr:
                err_msg += f"\nffprobe stderr:\n{e.stderr.decode(errors='ignore') if hasattr(e.stderr, 'decode') else str(e.stderr)}"
            QMessageBox.warning(self, "错误", f"无法解析轨道信息：{err_msg}")

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
            try:
                ret = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
                if ret.returncode == 0:
                    QMessageBox.information(self, "成功", "打包完成！")
                else:
                    QMessageBox.warning(self, "失败", f"打包失败，请检查文件和格式。\n{ret.stderr.decode(errors='ignore')}")
            except Exception as e2:
                QMessageBox.warning(self, "错误", f"ffmpeg执行出错：{e2}")
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

# 测试用
if __name__ == "__main__":
    app = QApplication(sys.argv)
    w = window1("test.mkv", "avi")
    w.show()
    sys.exit(app.exec_())
