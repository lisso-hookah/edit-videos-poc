"""PyInstaller runtime hook — add bundled ffmpeg/ffprobe to PATH."""
import os
import sys

if getattr(sys, "frozen", False):
    # When running as a PyInstaller bundle, _MEIPASS is the temp dir with bundled files.
    bin_dir = os.path.join(sys._MEIPASS, "bin")  # type: ignore[attr-defined]
    os.environ["PATH"] = bin_dir + os.pathsep + os.environ.get("PATH", "")
