#!/usr/bin/env python3

import socket
import struct
import numpy as np
import os, sys


import numpy as np
import os, sys
import cv2
import random
import time

from PyQt5 import QtCore, QtWidgets
from PyQt5.QtWidgets import (
    QApplication,
    QMainWindow,
    QMenu,
    QVBoxLayout,
    QSizePolicy,
    QMessageBox,
    QWidget,
    QPushButton,
)
from PyQt5.QtGui import QIcon

from matplotlib.backends.backend_qtagg import FigureCanvasQTAgg as FigureCanvas
from matplotlib.figure import Figure
import matplotlib.pyplot as plt


class App(QMainWindow):
    def __init__(self):
        super().__init__()
        # self.left = 10
        # self.top = 10
        self.title = "SingleTapping"
        # self.width = 800 # type: ignore
        # self.height = 400 # type: ignore
        self.initUI()

    def initUI(self):
        left, top, w, h = 100, 100, 800, 400
        self.setWindowTitle(self.title)
        self.setGeometry(left, top, w, h)  # type: ignore
        self.m = PlotCanvas(self, width=8, height=4)
        self.m.move(0, 0)
        self.show()

"""
以右脚为例，从上往下看，传感器分布如下：

12  13  14  15

             3
  0   1   2
            11

    4   5   6
   
     9     10

    7      8

左脚和右脚的传感器完全一致，只不过翻面
"""

def draw_one_foot(data):
    img = np.zeros((25, 60))
    
    img[2:6, 3:13] = data[12]
    img[8:12, 1:13] = data[13]
    img[14:18, 1:13] = data[14]
    img[20:24, 3:13] = data[15]

    img[20:24, 21:28] = data[11]
    img[2:6, 14:24] = data[0]
    img[8:12, 14:24] = data[1]
    img[14:18, 14:24] = data[2]
    img[16:23, 36:46] = data[10]

    img[6:12, 25:35] = data[4]
    img[14:18, 25:35] = data[5]
    img[20:24, 29:35] = data[6]

    img[16:23, 47:57] = data[8]
    img[8:15, 36:46] = data[9]
    img[20:24, 14:20] = data[3]
    img[8:15, 47:57] = data[7]

    img = cv2.GaussianBlur(img.T, (5, 5), 10)
    return img

class PlotCanvas(FigureCanvas):
    def __init__(self, parent=None, width=5, height=4, dpi=100):
        fig = Figure(figsize=(width, height), dpi=dpi)
        self.data_list = []
        self.data_mean = None

        self.ax1 = fig.add_subplot(121)
        self.ax2 = fig.add_subplot(122)

        # self.ax1 = self.fig.add_subplot(121,projection = '3d')
        # self.ax2 = self.fig.add_subplot(122,projection = '3d')

        self.x_inter = np.linspace(0, 1, 25)
        self.y_inter = np.linspace(0, 1, 60)
        self.Ax_inter, self.Ay_inter = np.meshgrid(self.x_inter, self.y_inter)

        self.ax1.get_xaxis().set_visible(False)
        self.ax1.get_yaxis().set_visible(False)

        self.ax2.get_xaxis().set_visible(False)
        self.ax2.get_yaxis().set_visible(False)

        self.shape_data_1 = np.zeros((25, 60))
        self.shape_data_2 = np.zeros((25, 60))

        FigureCanvas.__init__(self, fig)
        self.setParent(parent)
        FigureCanvas.setSizePolicy(
            self, QtWidgets.QSizePolicy.Expanding, QtWidgets.QSizePolicy.Expanding
        )
        FigureCanvas.updateGeometry(self)

        self.test()

    def test(self):
        timer = QtCore.QTimer(self)
        timer.timeout.connect(self.plotData)
        timer.start(100)

    def ploting_callback(self, data):
        self.shape_data_1 = draw_one_foot(data[0:16])
        self.shape_data_2 = draw_one_foot(data[16:32])

    def plotData(self):
        if self.shape_data_1 is not None:
            if self.shape_data_1.max() > 4 or self.shape_data_2.max() > 4:
                print("pass")
            else:
                
                self.ax1.cla()
                self.ax2.cla()
                cmap = "winter"
                self.ax1.imshow(self.shape_data_1, cmap=cmap, vmin=0 + 0.2, vmax=0.5 + 0.2)
                self.ax2.imshow(self.shape_data_2, cmap=cmap, vmin=0 + 0.2, vmax=0.5 + 0.2)

                self.ax1.axis("off")
                self.ax2.axis("off")

                self.draw()


def read_socket(ex):
    global mySocket
    try:
        msg = mySocket.recv(320)
    except BlockingIOError:
        return

    tac_data = []
    for i in range(40):
        msg_single = msg[i * 8 : (i + 1) * 8]
        try:
            data_single = struct.unpack("d", msg_single)
            tac_data.append(float(data_single[0]))
        except struct.error:
            tac_data.append(0.0)
    stamp = tac_data[32] * 1e3
    now_stamp = time.time_ns() * 1e-6
    lat = now_stamp - stamp
    # print(
    #     f"stamp: {stamp:.2f} ms, now: {now_stamp:.2f} ms, latency: {lat:.2f} ms"
    # )
    tac_data = np.array(tac_data[:32])
    # print(tac_data[:16].round(2))  # 保留小数点后2位


    ex.m.ploting_callback(tac_data)


if __name__ == "__main__":
    host = "127.0.0.1"
    port = 6543

    mySocket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    while mySocket.connect((host, port)) == socket.error:
        print("Connection ERROR! Now re-try to get connected ...")
    print("running main func")

    app = QApplication(sys.argv)
    ex = App()

    timer = QtCore.QTimer()
    timer.timeout.connect(lambda: read_socket(ex))
    timer.start(10)

    sys.exit(app.exec_())
