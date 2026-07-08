#!/usr/bin/env python3

import matplotlib
from matplotlib import pyplot as plt
from mpl_toolkits.mplot3d import Axes3D
import numpy as np
from scipy import interpolate
import cv2

import rospy
# from lab_tactile_ros.msg import tactile_data
# from plantar_sensor.msg import plantar_data
from plantar_sensor.msg import two_plantar_data

class Plot_tactile():
    def __init__(self):
        rospy.init_node("plot_tactile")
        rospy.Subscriber("two_plantar_data",two_plantar_data,self.getdata_callback_3D, queue_size=1, tcp_nodelay=True)
        # rospy.Subscriber("two_plantar_data",two_plantar_data,self.getdata_callback, queue_size=1)
        print("running main func")
        self.shape_data_1 = np.zeros((25, 60))
        self.shape_data_2 = np.zeros((25, 60))
        self.plt_flag = True
        self.cmap = 'Greys'   # rainbow
        
        rospy.spin()

    def data2shape(self, data):
        shape_data = np.zeros((25, 60))
        
        shape_data[8:15, 47:57] = data[0]
        shape_data[16:23,47:57] = data[1]
        
        shape_data[8:15, 36:46] = data[2]
        shape_data[16:23, 36:46] = data[3]
        
        shape_data[6:12, 25:35] = data[4]
        shape_data[14:18, 25:35] = data[5]
        shape_data[20:24, 29:35] = data[6]
        
        shape_data[20:24, 21:28] = data[7]
        
        shape_data[2:6, 14:24] = data[8]
        shape_data[8:12, 14:24] = data[9]
        shape_data[14:18, 14:24] = data[10]
        shape_data[20:24, 14:20] = data[11]
        
        shape_data[2:6, 3:13] = data[12]
        shape_data[8:12, 1:13] = data[13]
        shape_data[14:18, 1:13] = data[14]
        shape_data[20:24, 3:13] = data[15]
        return shape_data.T

    def getdata_callback(self, two_plantar_data):
        if self.plt_flag:
            self.fig = plt.figure()
            self.ax1 = self.fig.add_subplot(121)
            self.ax2 = self.fig.add_subplot(122)
            self.plt_flag = False
        self.ax1.cla()
        self.ax2.cla()
        data = np.array(two_plantar_data.data, dtype=float)     #
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
        
        self.ax1.imshow(np.fliplr(self.shape_data_1.T), vmin=-0.1, vmax=0.5, cmap='Greys')
        self.ax2.imshow(self.shape_data_2.T, vmin=-0.1, vmax=0.5, cmap='Greys')
        plt.pause(0.01)
        
    def getdata_callback_3D(self, two_plantar_data):
        if self.plt_flag:
            self.fig = plt.figure()
            self.ax1 = self.fig.add_subplot(121,projection = '3d')
            self.ax2 = self.fig.add_subplot(122,projection = '3d')
            
            self.x_inter = np.linspace(0,1,25)
            self.y_inter = np.linspace(0,1,60)
            self.Ax_inter, self.Ay_inter  = np.meshgrid(self.x_inter, self.y_inter)
            
            self.plt_flag = False
        self.ax1.cla()
        self.ax2.cla()
        data = np.array(two_plantar_data.data, dtype=float)     #
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
        
        # data_1 = cv2.GaussianBlur(np.fliplr(self.shape_data_1.T), (5,5), 10)
        # data_2 = cv2.GaussianBlur(self.shape_data_2.T, (5,5), 10)
        
        data_1 = cv2.GaussianBlur(self.shape_data_1.T, (5,5), 10)
        data_2 = cv2.GaussianBlur(np.fliplr(self.shape_data_2.T), (5,5), 10)
        
        self.ax1.plot_surface(self.Ax_inter, self.Ay_inter,data_1, cmap=self.cmap, vmin=0+0.2 , vmax=0.5+0.2)
        self.ax2.plot_surface(self.Ax_inter, self.Ay_inter,data_2, cmap=self.cmap, vmin=0+0.2 , vmax=0.5+0.2)
        
        self.ax1.set_zlim([0.2,0.7])
        self.ax2.set_zlim([0.2,0.7])

        self.ax1.set_box_aspect((25, 60, 10))
        self.ax2.set_box_aspect((25, 60, 10))
        self.ax1.axis('off')
        self.ax2.axis('off')
        
        elev = 60    # 仰角
        azim = 90    # 方位角
        self.ax1.view_init(elev=elev, azim=azim)
        self.ax2.view_init(elev=elev, azim=azim)
        
        # self.ax1.imshow(np.fliplr(self.shape_data_1.T), vmin=-0.1, vmax=0.5, cmap='Greys')
        # self.ax2.imshow(self.shape_data_2.T, vmin=-0.1, vmax=0.5, cmap='Greys')
        plt.pause(0.01)
        


if __name__ == "__main__":
    Plot_tactile()
