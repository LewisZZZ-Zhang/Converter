from PyQt5.QtWidgets import QWidget, QPushButton, QVBoxLayout, QApplication, QLabel
from PyQt5.QtGui import QPixmap
from video_converter import VideoConverter

class HomePage(QWidget):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Home Page")
        self.resize(400, 600)

        self.layout = QVBoxLayout()

        # 添加图片
        self.image_label = QLabel()
        pixmap = QPixmap("logo.png")  # 请确保logo.png在同目录下或写绝对路径
        self.image_label.setPixmap(pixmap)
        self.image_label.setScaledContents(True)
        self.image_label.setFixedHeight(100)
        self.layout.addWidget(self.image_label)

        # 添加文本
        self.text_label = QLabel("欢迎使用多功能视频格式转换器！")
        self.text_label.setStyleSheet("font-size: 16px; margin: 10px;")
        self.text_label.setAlignment(Qt.AlignCenter)
        self.layout.addWidget(self.text_label)

        self.open_converter_btn = QPushButton("视频格式转换 Video Format Converter")
        self.open_converter_btn.clicked.connect(self.open_converter)

        self.layout.addWidget(self.open_converter_btn)
        self.setLayout(self.layout)

    def open_converter(self):
        self.converter_window = VideoConverter()
        self.converter_window.show()

if __name__ == "__main__":
    import sys
    from PyQt5.QtCore import Qt
    app = QApplication(sys.argv)
    home = HomePage()
    home.show()
    sys.exit(app.exec_())