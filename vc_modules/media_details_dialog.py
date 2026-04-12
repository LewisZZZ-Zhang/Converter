import json

from PyQt5.QtWidgets import (
    QDialog,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QPlainTextEdit,
    QTabWidget,
    QVBoxLayout,
)


def _format_value(value, indent=0):
    prefix = " " * indent
    lines = []

    if isinstance(value, dict):
        for key, item in value.items():
            if isinstance(item, (dict, list)):
                lines.append(f"{prefix}{key}:")
                lines.extend(_format_value(item, indent + 2))
            else:
                lines.append(f"{prefix}{key}: {item}")
        return lines

    if isinstance(value, list):
        for idx, item in enumerate(value):
            if isinstance(item, (dict, list)):
                lines.append(f"{prefix}- [{idx}]")
                lines.extend(_format_value(item, indent + 2))
            else:
                lines.append(f"{prefix}- [{idx}] {item}")
        if not value:
            lines.append(f"{prefix}[]")
        return lines

    lines.append(f"{prefix}{value}")
    return lines


def build_detail_text(input_file, payload):
    sections = [f"文件: {input_file}"]

    format_info = payload.get("format")
    if format_info:
        sections.append("")
        sections.append("[容器信息]")
        sections.extend(_format_value(format_info, 2))

    streams_info = payload.get("streams")
    if streams_info:
        sections.append("")
        sections.append("[轨道信息]")
        sections.extend(_format_value(streams_info, 2))

    chapters = payload.get("chapters")
    if chapters:
        sections.append("")
        sections.append("[章节信息]")
        sections.extend(_format_value(chapters, 2))

    programs = payload.get("programs")
    if programs:
        sections.append("")
        sections.append("[Programs]")
        sections.extend(_format_value(programs, 2))

    stream_groups = payload.get("stream_groups")
    if stream_groups:
        sections.append("")
        sections.append("[Stream Groups]")
        sections.extend(_format_value(stream_groups, 2))

    return "\n".join(sections)


class MediaDetailsDialog(QDialog):
    def __init__(self, input_file, payload, parent=None):
        super().__init__(parent)
        self.setWindowTitle("媒体详情")
        self.resize(1000, 720)

        title_label = QLabel(f"当前文件: {input_file}")
        title_label.setWordWrap(True)

        tabs = QTabWidget()

        details_text = QPlainTextEdit()
        details_text.setReadOnly(True)
        details_text.setPlainText(build_detail_text(input_file, payload))
        tabs.addTab(details_text, "整理视图")

        raw_json_text = QPlainTextEdit()
        raw_json_text.setReadOnly(True)
        raw_json_text.setPlainText(
            json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=False)
        )
        tabs.addTab(raw_json_text, "原始 JSON")

        close_btn = QPushButton("关闭")
        close_btn.clicked.connect(self.accept)

        btn_row = QHBoxLayout()
        btn_row.addStretch()
        btn_row.addWidget(close_btn)

        layout = QVBoxLayout()
        layout.addWidget(title_label)
        layout.addWidget(tabs)
        layout.addLayout(btn_row)
        self.setLayout(layout)
