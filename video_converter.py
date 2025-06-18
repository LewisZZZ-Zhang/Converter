import sys
from PyQt5.QtWidgets import (
    QApplication, QWidget, QLabel, QPushButton, QVBoxLayout,
    QFileDialog, QComboBox, QMessageBox, QHBoxLayout
)
from PyQt5.QtCore import QThread, pyqtSignal
import ffmpeg
import os

class ConvertThread(QThread):
    finished = pyqtSignal(bool, str)

    def __init__(self, input_file, output_file, output_kwargs):
        super().__init__()
        self.input_file = input_file
        self.output_file = output_file
        self.output_kwargs = output_kwargs

    def run(self):
        import ffmpeg
        try:
            (
                ffmpeg
                .input(self.input_file)
                .output(self.output_file, **self.output_kwargs)
                .run(overwrite_output=True)
            )
            self.finished.emit(True, self.output_file)
        except Exception as e:
            self.finished.emit(False, str(e))

class VideoConverter(QWidget):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("视频格式转换器")
        self.resize(500, 500)

        self.supported_formats = ["mp4", "avi", "mov", "mkv", "flv", "wmv"]

        self.input_file = ""
        self.output_file = ""

        self.label = QLabel("选择要转换的视频文件")
        self.select_btn = QPushButton("选择文件")
        self.select_btn.clicked.connect(self.select_file)

        self.format_label = QLabel("选择输出格式")
        self.format_combo = QComboBox()
        self.format_combo.addItems(self.supported_formats)
        self.format_combo.currentTextChanged.connect(self.update_core_options)  # 新增

        self.corenumber_label = QLabel("使用核心数量")
        self.corenumber_combo = QComboBox()
        # self.corenumber_combo.addItems([str(i) for i in range(1, 11)])  
        core_count = os.cpu_count() or 1
        self.corenumber_combo.addItems([str(i) for i in range(1, core_count + 1)])

        self.convert_btn = QPushButton("开始转换")
        self.convert_btn.clicked.connect(self.convert_video)


        # lines:
        file_input_line = QHBoxLayout()
        file_input_line.addWidget(self.label)
        # file_input_line.addStretch()  # 让label和按钮之间有弹性空间
        file_input_line.addWidget(self.select_btn)

        file_output_type_line = QHBoxLayout()
        file_output_type_line.addWidget(self.format_label)
        file_output_type_line.addWidget(self.format_combo)

        core_counter_line = QHBoxLayout()
        core_counter_line.addWidget(self.corenumber_label)
        core_counter_line.addWidget(self.corenumber_combo)

        layout = QVBoxLayout()
        # layout.addWidget(self.label)
        layout.addLayout(file_input_line)
        layout.addLayout(file_output_type_line)
        layout.addLayout(core_counter_line)
        layout.addWidget(self.convert_btn)
        layout.addStretch()  # 让控件都靠上，剩余空间在底部
        self.setLayout(layout)


        self.update_core_options(self.format_combo.currentText())  # 初始化时调用
        
    def update_core_options(self, format_text):
        if format_text in ["mp4", "mov"]:
            self.corenumber_combo.clear()
            self.corenumber_combo.addItem("硬件加速")
            self.corenumber_combo.setEnabled(False)
        else:
            self.corenumber_combo.setEnabled(True)
            self.corenumber_combo.clear()
            self.corenumber_combo.addItems([str(i) for i in range(1, 11)])


    def select_file(self):
        file, _ = QFileDialog.getOpenFileName(self, "选择视频文件", "", "视频文件 (*.mp4 *.avi *.mov *.mkv *.flv *.wmv)")
        if file:
            self.input_file = file
            self.label.setText(f"已选择文件: {os.path.basename(file)}")

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
                # 'threads': self.corenumber_combo.currentText(),
            }
        else:
            output_kwargs = {    
                # 'vcodec': 'libx264',
                'threads': self.corenumber_combo.currentText(),
            }

        self.convert_btn.setEnabled(False)
        self.thread = ConvertThread(self.input_file, self.output_file, output_kwargs)
        self.thread.finished.connect(self.on_convert_finished)
        self.thread.start()

    def on_convert_finished(self, success, info):
        self.convert_btn.setEnabled(True)
        if success:
            QMessageBox.information(self, "成功", f"转换完成！输出文件：{info}")
        else:
            QMessageBox.critical(self, "错误", f"转换失败：{info}")

# ...existing code...

if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = VideoConverter()
    window.show()
    sys.exit(app.exec_())