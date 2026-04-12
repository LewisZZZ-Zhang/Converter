from PyQt5.QtCore import Qt
from PyQt5.QtWidgets import QLabel, QToolButton, QVBoxLayout, QWidget


class DebugSection(QWidget):
    def __init__(self, text, parent=None):
        super().__init__(parent)

        self.toggle_btn = QToolButton()
        self.toggle_btn.setText("调试")
        self.toggle_btn.setCheckable(True)
        self.toggle_btn.setChecked(False)
        self.toggle_btn.setArrowType(Qt.RightArrow)
        self.toggle_btn.setToolButtonStyle(Qt.ToolButtonTextBesideIcon)
        self.toggle_btn.setStyleSheet("QToolButton { border: none; padding: 0; }")

        self.content_label = QLabel(text)
        self.content_label.setWordWrap(True)

        self.content = QWidget()
        content_layout = QVBoxLayout()
        content_layout.setContentsMargins(18, 0, 0, 0)
        content_layout.addWidget(self.content_label)
        self.content.setLayout(content_layout)
        self.content.setVisible(False)

        layout = QVBoxLayout()
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(2)
        layout.addWidget(self.toggle_btn)
        layout.addWidget(self.content)
        self.setLayout(layout)

        self.toggle_btn.toggled.connect(self._set_expanded)

    def _set_expanded(self, visible):
        self.toggle_btn.setArrowType(Qt.DownArrow if visible else Qt.RightArrow)
        self.content.setVisible(visible)

    def set_text(self, text):
        self.content_label.setText(text)
