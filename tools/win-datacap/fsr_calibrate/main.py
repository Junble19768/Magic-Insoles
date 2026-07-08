import pyqtgraph as pg

from .app import FsrCalibrateApp


def main() -> None:
    app = pg.mkQApp("FsrCalibrate")
    window = FsrCalibrateApp()
    app.aboutToQuit.connect(window.close)
    window.show()
    pg.exec()
