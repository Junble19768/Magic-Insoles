import pyqtgraph as pg

from .app_capture import FsrCaptureApp


def main() -> None:
    app = pg.mkQApp("FsrCapture")
    window = FsrCaptureApp()
    app.aboutToQuit.connect(window.close)
    window.show()
    pg.exec()
