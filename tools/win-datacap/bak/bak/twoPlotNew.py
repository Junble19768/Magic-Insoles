#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import rospy
from xela_acquiring_data.msg import TactileData16x3
from scipy import interpolate 

import torch
import numpy as np
import os, sys
import cv2
import random
import time

from PyQt5 import QtCore, QtWidgets
from PyQt5.QtWidgets import QApplication, QMainWindow, QMenu, QVBoxLayout, QSizePolicy, QMessageBox, QWidget, QPushButton
from PyQt5.QtGui import QIcon

from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg as FigureCanvas
from matplotlib.figure import Figure
import matplotlib.pyplot as plt

from plantar_sensor.msg import two_plantar_data



class App(QMainWindow):
    def __init__(self):
        super().__init__()
        self.left = 10
        self.top = 10
        self.title = 'SingleTapping'
        self.width = 800
        self.height = 400
        self.initUI()
    def initUI(self):
        self.setWindowTitle(self.title)
        self.setGeometry(self.left, self.top, self.width, self.height)
        m = PlotCanvas(self, width=8, height=4)
        m.move(0,0)
        self.show()

class PlotCanvas(FigureCanvas):
    def __init__(self, parent=None,width=5, height=4, dpi=100):
        fig=Figure(figsize=(width,height),dpi=dpi)
        
        self.ax1 = fig.add_subplot(121)
        self.ax2 = fig.add_subplot(122)
        
        # self.ax1 = self.fig.add_subplot(121,projection = '3d')
        # self.ax2 = self.fig.add_subplot(122,projection = '3d')
            
        self.x_inter = np.linspace(0,1,25)
        self.y_inter = np.linspace(0,1,60)
        self.Ax_inter, self.Ay_inter  = np.meshgrid(self.x_inter, self.y_inter)
        
        self.ax1.get_xaxis().set_visible(False)
        self.ax1.get_yaxis().set_visible(False)

        self.ax2.get_xaxis().set_visible(False)
        self.ax2.get_yaxis().set_visible(False)
        
        self.shape_data_1 = np.zeros((25, 60))
        self.shape_data_2 = np.zeros((25, 60))
        
        FigureCanvas.__init__(self,fig)
        self.setParent(parent)
        FigureCanvas.setSizePolicy(self,
                                   QtWidgets.QSizePolicy.Expanding,
                                   QtWidgets.QSizePolicy.Expanding)
        FigureCanvas.updateGeometry(self)
        
        #------------------#
        # 订阅触觉数据topic
        #------------------#
        rospy.init_node("plot_tactile")
        rospy.Subscriber("two_plantar_data",two_plantar_data,self.ploting_callback, queue_size=1, tcp_nodelay=True)
        self.test()
        rospy.loginfo("RUNING MAIN FUNC ... ")

    def test(self):
        timer = QtCore.QTimer(self)
        timer.timeout.connect(self.plotData)
        timer.start(100)
    
    def ploting_callback(self, two_plantar_data):
        data = np.array(two_plantar_data.data, dtype=float)     #
        # print(data.max())
        # if np.isnan(data.max()):
        data += 0.3
        data[16:32] += 0.02
        self.shape_data_1[8:15, 47:57]   = data[0]
        self.shape_data_1[16:23,47:57]   = data[1]
        self.shape_data_1[8:15, 36:46]   = data[2]
        self.shape_data_1[16:23, 36:46]  = data[3]
        self.shape_data_1[6:12, 25:35]   = data[4]
        self.shape_data_1[14:18, 25:35]  = data[5]
        self.shape_data_1[20:24, 29:35]  = data[6]
        self.shape_data_1[20:24, 21:28]  = data[7]
        self.shape_data_1[2:6, 14:24]    = data[8]
        self.shape_data_1[8:12, 14:24]   = data[9]
        self.shape_data_1[14:18, 14:24]  = data[10]
        self.shape_data_1[20:24, 14:20]  = data[11]
        self.shape_data_1[2:6, 3:13]     = data[12]
        self.shape_data_1[8:12, 1:13]    = data[13]
        self.shape_data_1[14:18, 1:13]   = data[14]
        self.shape_data_1[20:24, 3:13]   = data[15]
        
        self.shape_data_2[8:15, 47:57]   = data[16+0]
        self.shape_data_2[16:23,47:57]   = data[16+1]
        self.shape_data_2[8:15, 36:46]   = data[16+2]
        self.shape_data_2[16:23, 36:46]  = data[16+3]
        self.shape_data_2[6:12, 25:35]   = data[16+4]
        self.shape_data_2[14:18, 25:35]  = data[16+5]
        self.shape_data_2[20:24, 29:35]  = data[16+6]
        self.shape_data_2[20:24, 21:28]  = data[16+7]
        self.shape_data_2[2:6, 14:24]    = data[16+8]
        self.shape_data_2[8:12, 14:24]   = data[16+9]
        self.shape_data_2[14:18, 14:24]  = data[16+10]
        self.shape_data_2[20:24, 14:20]  = data[16+11]
        self.shape_data_2[2:6, 3:13]     = data[16+12]
        self.shape_data_2[8:12, 1:13]    = data[16+13]
        self.shape_data_2[14:18, 1:13]   = data[16+14]
        self.shape_data_2[20:24, 3:13]   = data[16+15]
        
        

    def plotData(self):
        if self.shape_data_1 is not None:
            if self.shape_data_1.max() > 4 or self.shape_data_2.max() > 4:
                print('pass')
            else:
                data_1 = cv2.GaussianBlur(self.shape_data_1.T, (5,5), 10)
                data_2 = cv2.GaussianBlur(np.fliplr(self.shape_data_2.T), (5,5), 10)
                self.ax1.cla()
                self.ax2.cla()
                cmap = 'winter'
                self.ax1.imshow(data_1, cmap=cmap, vmin=0+0.2 , vmax=0.5+0.2)
                self.ax2.imshow(data_2, cmap=cmap, vmin=0+0.2 , vmax=0.5+0.2)

                self.ax1.axis('off')
                self.ax2.axis('off')
                
                self.draw()
        


if __name__ == '__main__':
    app = QApplication(sys.argv)
    ex = App()
    sys.exit(app.exec_())