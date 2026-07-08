import pyqtgraph as pg

from .app_visualize import FsrVisualizeApp


def main() -> None:
    app = pg.mkQApp("FsrVisualize")
    window = FsrVisualizeApp()
    app.aboutToQuit.connect(window.close)
    window.show()
    pg.exec()
