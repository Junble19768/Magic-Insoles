"""Backward-compatible re-exports; use app_capture / app_reference / app_visualize."""

from .app_capture import FsrCaptureApp
from .hub import DataHub, fsr_label

# Legacy name used by external imports.
FsrCalibrateApp = FsrCaptureApp

__all__ = ["DataHub", "FsrCalibrateApp", "FsrCaptureApp", "fsr_label"]
