import os
import json
import subprocess

from PyQt5.QtCore import QThread, pyqtSignal


def get_bin_path(bin_name):
    import sys

    arch = os.uname().machine
    if getattr(sys, "frozen", False):
        base_dir = os.path.join(sys._MEIPASS, "bin")
    else:
        base_dir = os.path.join(os.path.dirname(__file__), "..", "bin")

    arch_candidates = []
    if arch == "arm64":
        arch_candidates = [f"{bin_name}-arm64", f"{bin_name}-aarch64"]
    elif arch in ("x86_64", "amd64"):
        arch_candidates = [f"{bin_name}-x86_64", f"{bin_name}-amd64"]

    candidates = [os.path.join(base_dir, name) for name in arch_candidates]
    candidates.append(os.path.join(base_dir, bin_name))

    for candidate in candidates:
        if os.path.exists(candidate):
            return candidate

    return os.path.join(base_dir, bin_name)


def detect_binary_info(bin_name):
    bin_path = get_bin_path(bin_name)
    arch = "unknown"
    try:
        result = subprocess.run(
            ["file", bin_path],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            check=True,
        )
        output = result.stdout.lower()
        if "arm64" in output:
            arch = "arm64"
        elif "x86_64" in output:
            arch = "x86_64"
    except Exception:
        pass

    return {
        "name": bin_name,
        "path": os.path.abspath(bin_path),
        "arch": arch,
    }


def probe_duration(input_file):
    ffprobe_path = get_bin_path("ffprobe")
    cmd = [
        ffprobe_path,
        "-v",
        "error",
        "-show_entries",
        "format=duration",
        "-of",
        "default=noprint_wrappers=1:nokey=1",
        input_file,
    ]
    try:
        result = subprocess.run(
            cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            check=True,
            text=True,
        )
        duration = float(result.stdout.strip())
        return duration if duration > 0 else None
    except Exception:
        return None


class MediaInfoWorker(QThread):
    finished = pyqtSignal(bool, object, str)
    status_changed = pyqtSignal(str)

    def __init__(self, input_file, include_format=False, parent=None):
        super().__init__(parent)
        self.input_file = input_file
        self.include_format = include_format

    def run(self):
        ffprobe_path = get_bin_path("ffprobe")
        self.status_changed.emit("正在读取轨道信息...")

        try:
            if self.include_format:
                cmd = [
                    ffprobe_path,
                    "-v",
                    "error",
                    "-show_streams",
                    "-show_format",
                    "-show_chapters",
                    "-show_programs",
                    "-show_stream_groups",
                    "-print_format",
                    "json",
                    self.input_file,
                ]
            else:
                cmd = [
                    ffprobe_path,
                    "-v",
                    "error",
                    "-show_streams",
                    "-print_format",
                    "json",
                    self.input_file,
                ]

            result = subprocess.run(
                cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                check=True,
            )
            payload = json.loads(result.stdout.decode(errors="ignore"))

            self.finished.emit(True, payload, "")
        except Exception as exc:
            err_msg = str(exc)
            stderr = getattr(exc, "stderr", b"")
            if stderr:
                decoded = stderr.decode(errors="ignore") if hasattr(stderr, "decode") else str(stderr)
                err_msg += f"\nffprobe stderr:\n{decoded}"
            self.finished.emit(False, None, err_msg)


class FFmpegWorker(QThread):
    progress_changed = pyqtSignal(int)
    status_changed = pyqtSignal(str)
    finished = pyqtSignal(bool, str)

    def __init__(self, cmd, output_file, duration_seconds=None, parent=None):
        super().__init__(parent)
        self.cmd = cmd
        self.output_file = output_file
        self.duration_seconds = duration_seconds

    def run(self):
        progress_cmd = [
            self.cmd[0],
            "-progress",
            "pipe:1",
            "-nostats",
            "-loglevel",
            "error",
            *self.cmd[1:],
        ]

        try:
            process = subprocess.Popen(
                progress_cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                text=True,
                bufsize=1,
                universal_newlines=True,
            )
        except Exception as exc:
            self.finished.emit(False, f"无法启动 ffmpeg：{exc}")
            return

        last_progress = -1
        extra_output = []

        if process.stdout is not None:
            for raw_line in process.stdout:
                line = raw_line.strip()
                if not line:
                    continue

                if "=" not in line:
                    extra_output.append(line)
                    continue

                key, value = line.split("=", 1)
                if key == "out_time_ms":
                    self._emit_progress(value, 1000000.0, last_progress)
                    last_progress = self._progress_value(value, 1000000.0, last_progress)
                elif key == "out_time_us":
                    self._emit_progress(value, 1000000.0, last_progress)
                    last_progress = self._progress_value(value, 1000000.0, last_progress)
                elif key == "out_time":
                    self._emit_hms_progress(value, last_progress)
                    last_progress = self._hms_progress_value(value, last_progress)
                elif key == "progress":
                    if value == "continue":
                        self.status_changed.emit("正在转换，请稍候...")
                    elif value == "end":
                        if last_progress < 100:
                            self.progress_changed.emit(100)
                        self.status_changed.emit("转换完成，正在收尾...")

        return_code = process.wait()
        if return_code == 0:
            self.progress_changed.emit(100)
            self.finished.emit(True, self.output_file)
            return

        error_message = "\n".join(extra_output).strip() or f"ffmpeg 退出码：{return_code}"
        self.finished.emit(False, error_message)

    def _emit_progress(self, raw_value, divisor, last_progress):
        progress = self._progress_value(raw_value, divisor, last_progress)
        if progress != last_progress:
            self.progress_changed.emit(progress)

    def _progress_value(self, raw_value, divisor, last_progress):
        try:
            current_seconds = float(raw_value) / divisor
        except (TypeError, ValueError):
            return last_progress
        return self._percent_from_seconds(current_seconds, last_progress)

    def _emit_hms_progress(self, raw_value, last_progress):
        progress = self._hms_progress_value(raw_value, last_progress)
        if progress != last_progress:
            self.progress_changed.emit(progress)

    def _hms_progress_value(self, raw_value, last_progress):
        try:
            hours, minutes, seconds = raw_value.split(":")
            current_seconds = (
                float(hours) * 3600 + float(minutes) * 60 + float(seconds)
            )
        except (TypeError, ValueError):
            return last_progress
        return self._percent_from_seconds(current_seconds, last_progress)

    def _percent_from_seconds(self, current_seconds, last_progress):
        if not self.duration_seconds:
            return last_progress
        percent = int((current_seconds / self.duration_seconds) * 100)
        return max(0, min(percent, 99))
