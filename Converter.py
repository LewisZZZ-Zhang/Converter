from PyQt5.QtWidgets import QWidget, QPushButton, QVBoxLayout, QApplication, QLabel
from PyQt5.QtGui import QPixmap
from video_converter_pre import vc_pre
from extract_tracks import AudioExtractor  # 假设音轨提取器在extract_tracks.py中定义

class HomePage(QWidget):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Home Page")
        self.resize(400, 600)

        self.layout = QVBoxLayout()

        # 添加图片
        self.image_label = QLabel()
        pixmap = QPixmap("assets/logo.png")  # 请确保logo.png在同目录下或写绝对路径
        self.image_label.setPixmap(pixmap)
        self.image_label.setScaledContents(True)
        self.image_label.setFixedHeight(100)
        self.layout.addWidget(self.image_label)

        # 添加文本
        self.text_label = QLabel("导航")
        self.text_label.setStyleSheet("font-size: 16px; margin: 10px;")
        self.text_label.setAlignment(Qt.AlignCenter)
        self.layout.addWidget(self.text_label)

        self.open_converter_btn = QPushButton("视频格式转换 Video Format Converter")
        self.open_converter_btn.clicked.connect(self.open_converter)

        self.open_extractor_btn = QPushButton("音轨提取 Audio Track Extractor")
        self.open_extractor_btn.clicked.connect(self.open_extractor)


        self.layout.addWidget(self.open_converter_btn)
        self.layout.addWidget(self.open_extractor_btn)
        self.layout.addStretch()
        self.setLayout(self.layout)

    def open_converter(self):
        self.converter_window = vc_pre()
        self.converter_window.show()

    def open_extractor(self):
        self.extractor_window = AudioExtractor()
        self.extractor_window.show()

if __name__ == "__main__":
    import sys
    from PyQt5.QtCore import Qt
    app = QApplication(sys.argv)
    home = HomePage()
    home.show()
    sys.exit(app.exec_())