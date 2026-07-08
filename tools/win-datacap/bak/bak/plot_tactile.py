#!/usr/bin/env python3

import matplotlib
from matplotlib import pyplot as plt
from mpl_toolkits.mplot3d import Axes3D
import numpy as np
from scipy import interpolate
import cv2

import rospy
# from lab_tactile_ros.msg import tactile_data
from plantar_sensor.msg import plantar_data

class Plot_tactile():
    def __init__(self):
        rospy.init_node("plot_tactile")
        rospy.Subscriber("plantar_data",plantar_data,self.getdata_callback, queue_size=1, tcp_nodelay=True)
        # rospy.Subscriber("plantar_data",plantar_data,self.getdata_callback, queue_size=1)
        print("running main func")
        
        self.plt_flag = True
        
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

    def getdata_callback(self, plantar_data):
        if self.plt_flag:
            self.fig = plt.figure()
            self.ax1 = self.fig.add_subplot(111)
            self.plt_flag = False
        self.ax1.cla()
        data = np.array(plantar_data.data, dtype=float)     #
        # data = data.reshape((4,4))
        shape_data = self.data2shape(data)
        self.ax1.imshow(shape_data, vmin=-0.1, vmax=0.5, cmap='Greys')
        plt.pause(0.01)
        
    def ploting_callback(self, tactile_data):
        if self.plt_flag:
            self.fig = plt.figure()
            self.ax1 = self.fig.add_subplot(121)
            self.ax2 = self.fig.add_subplot(122,projection = '3d')
            
            self.x = np.arange(0,7,1)
            self.y = np.arange(0,4,1)
            self.Ax, self.Ay = np.meshgrid(self.x, self.y)

            self.x_inter = np.linspace(0,7,700)
            self.y_inter = np.linspace(0,4,400)
            self.Ax_inter, self.Ay_inter  = np.meshgrid(self.x_inter, self.y_inter)
            self.newshape = (self.Ax_inter.shape[0]) * (self.Ay_inter.shape[0])
            self.plt_flag = False
            
        data = np.array(tactile_data.data, dtype=float)     #
        # print("running call back func")
        sensor_1 = np.zeros((4,7),dtype=float)
        for i in range(4):
            for j in range(7):
                sensor_1[i][j] = data[i+4*j]
        # print(sensor_1)

        self.ax1.cla()
        self.ax2.cla()
        self.ax1.imshow(sensor_1, vmin=-0.1, vmax=0.5, cmap='hot')

        f1 = interpolate.interp2d(self.x, self.y, sensor_1, kind='linear')
        # f1 = interpolate.interp2d(self.x, self.y, sensor_1, kind='quintic')
        sensor_1_inter = f1(self.x_inter, self.y_inter)

        self.ax2.plot_surface(self.Ax_inter, self.Ay_inter,sensor_1_inter, cmap = 'hot', vmin=0 , vmax=0.5)
        self.ax2.set_zlim([0,0.5])
        plt.gca().set_box_aspect((7, 4, 3))
        
        self.ax1.axis('off')
        self.ax2.axis('off')
        elev = 45    # 仰角
        azim = 90    # 方位角
        self.ax2.view_init(elev=elev, azim=azim)
        plt.pause(0.1)


    def ploting_callback_single3D(self, tactile_data):
        if self.plt_flag:
            self.fig = plt.figure()
            self.ax1 = self.fig.add_subplot(111,projection = '3d')
            
            self.x = np.arange(0,7,1)
            self.y = np.arange(0,4,1)
            self.Ax, self.Ay = np.meshgrid(self.x, self.y)

            self.x_inter = np.linspace(0,7,70)
            self.y_inter = np.linspace(0,4,40)
            self.Ax_inter, self.Ay_inter  = np.meshgrid(self.x_inter, self.y_inter)
            self.newshape = (self.Ax_inter.shape[0]) * (self.Ay_inter.shape[0])
            self.plt_flag = False
            
        data = np.array(tactile_data.data, dtype=float)     #
        # print("running call back func")
        sensor_1 = np.zeros((4,7),dtype=float)
        for i in range(4):
            for j in range(7):
                sensor_1[i][j] = data[i+4*j]
        # print(sensor_1)

        self.ax1.cla()

        # f1 = interpolate.interp2d(self.x, self.y, sensor_1, kind='linear')
        # sensor_1_inter = f1(self.x_inter, self.y_inter)
        
        sensor_1_inter = cv2.resize(sensor_1, (70,40), cv2.INTER_LINEAR)
        
        sensor_1_inter = cv2.GaussianBlur(sensor_1_inter, (5,5), 10)
        
        self.ax1.plot_surface(self.Ax_inter, self.Ay_inter,sensor_1_inter, cmap = 'hot', vmin=0 , vmax=0.5)
        self.ax1.set_zlim([-0.50,0.3])
        # plt.gca().set_box_aspect((7, 4, 3))
        self.ax1.set_box_aspect((7, 4, 3))
        
        self.ax1.axis('off')
        elev = 45    # 仰角
        azim = 180    # 方位角
        # azim = 90    # 方位角
        self.ax1.view_init(elev=elev, azim=azim)
        plt.pause(0.1)


if __name__ == "__main__":
    Plot_tactile()
