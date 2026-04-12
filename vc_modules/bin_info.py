import os
import subprocess


def get_bin_path(bin_name):
    import sys

    if getattr(sys, "frozen", False):
        base_dir = os.path.join(sys._MEIPASS, "bin")
    else:
        base_dir = os.path.join(os.path.dirname(__file__), "..", "bin")

    arch = os.uname().machine
    arch_candidates = []
    if arch == "arm64":
        arch_candidates = [f"{bin_name}-arm64", f"{bin_name}-aarch64"]
    elif arch in ("x86_64", "amd64"):
        arch_candidates = [f"{bin_name}-x86_64", f"{bin_name}-amd64"]

    for name in arch_candidates + [bin_name]:
        candidate = os.path.join(base_dir, name)
        if os.path.exists(candidate):
            return candidate

    return os.path.join(base_dir, bin_name)


def detect_binary_info(bin_name):
    path = get_bin_path(bin_name)
    arch = "unknown"
    try:
        result = subprocess.run(
            ["file", path],
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
        "path": os.path.abspath(path),
        "arch": arch,
    }
