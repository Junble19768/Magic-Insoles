import pyqtgraph as pg

from .app_reference import FsrReferenceApp


def main() -> None:
    app = pg.mkQApp("FsrReference")
    window = FsrReferenceApp()
    app.aboutToQuit.connect(window.close)
    window.show()
    pg.exec()
