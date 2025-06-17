# ...existing code...
from PyQt5.QtWidgets import QListWidget, QListWidgetItem

class VideoConverter(QWidget):
    def __init__(self):
        super().__init__()
        # ...existing code...

        self.track_list = QListWidget()
        self.track_list.setSelectionMode(QListWidget.MultiSelection)
        self.track_list.setMinimumHeight(120)

        # ...existing code...
        layout.addWidget(QLabel("选择要保留的轨道（可多选）"))
        layout.addWidget(self.track_list)
        # ...existing code...

        self.update_core_options(self.format_combo.currentText())  # 初始化时调用

    def select_file(self):
        file, _ = QFileDialog.getOpenFileName(self, "选择视频文件", "", "视频文件 (*.mp4 *.avi *.mov *.mkv *.flv *.wmv)")
        if file:
            self.input_file = file
            self.label.setText(f"已选择文件: {os.path.basename(file)}")
            self.populate_tracks()

    def populate_tracks(self):
        import ffmpeg
        self.track_list.clear()
        try:
            probe = ffmpeg.probe(self.input_file)
            streams = probe.get('streams', [])
            for stream in streams:
                idx = stream.get('index')
                codec_type = stream.get('codec_type')
                lang = stream.get('tags', {}).get('language', '')
                desc = f"{codec_type.upper()} #{idx}"
                if lang:
                    desc += f" ({lang})"
                item = QListWidgetItem(desc)
                item.setData(32, idx)  # 32 = Qt.UserRole
                item.setCheckState(2)  # 2 = Qt.Checked
                self.track_list.addItem(item)
        except Exception as e:
            QMessageBox.warning(self, "轨道获取失败", f"无法获取轨道信息：{e}")

    def convert_video(self):
        if not self.input_file:
            QMessageBox.warning(self, "警告", "请先选择一个视频文件！")
            return

        output_format = self.format_combo.currentText()
        base, _ = os.path.splitext(self.input_file)
        self.output_file = f"{base}_converted.{output_format}"

        # 使用硬件加速和多线程
        output_kwargs = {}
        if output_format in ["mp4", "mov"]:
            output_kwargs = {
                'vcodec': 'h264_videotoolbox',
            }
        else:
            output_kwargs = {    
                'threads': self.corenumber_combo.currentText(),
            }

        # 获取用户选择的轨道
        selected_indexes = []
        for i in range(self.track_list.count()):
            item = self.track_list.item(i)
            if item.checkState() == 2:  # Qt.Checked
                selected_indexes.append(item.data(32))

        if not selected_indexes:
            QMessageBox.warning(self, "警告", "请至少选择一个轨道！")
            return

        # 生成 map 参数
        map_args = []
        for idx in selected_indexes:
            map_args.extend(['-map', f'0:{idx}'])

        self.convert_btn.setEnabled(False)
        self.thread = ConvertThreadWithMap(self.input_file, self.output_file, output_kwargs, map_args)
        self.thread.finished.connect(self.on_convert_finished)
        self.thread.start()

# 新增线程类，支持 map 参数
class ConvertThreadWithMap(QThread):
    finished = pyqtSignal(bool, str)

    def __init__(self, input_file, output_file, output_kwargs, map_args):
        super().__init__()
        self.input_file = input_file
        self.output_file = output_file
        self.output_kwargs = output_kwargs
        self.map_args = map_args

    def run(self):
        import ffmpeg
        import subprocess
        try:
            # 构造 ffmpeg 命令行
            cmd = ['ffmpeg', '-y', '-i', self.input_file]
            cmd += self.map_args
            for k, v in self.output_kwargs.items():
                cmd += [f'-{k}', str(v)]
            cmd += [self.output_file]
            subprocess.run(cmd, check=True)
            self.finished.emit(True, self.output_file)
        except Exception as e:
            self.finished.emit(False, str(e))

# ...existing code...