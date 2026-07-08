#!/usr/bin/env python3

import rospy
from plantar_sensor.msg import plantar_data

import matplotlib.pyplot as plt
import numpy as np

class PlotCurve():
    def __init__(self,):
        rospy.init_node("plot_curve")
        self.xlim_width = 200
        self.y_min, self.y_max = 0,  2
        self.plot_flag = True
        
        self.plot_time = 0
        
        self.plot_x = []
        self.data_1, self.data_2, self.data_3, self.data_4, self.data_5, self.data_6, self.data_7, self.data_8 = \
        [],          [],          [],          [],          [],          [],          [],          []
        self.data_9, self.data_10, self.data_11, self.data_12, self.data_13, self.data_14, self.data_15, self.data_16 = \
        [],          [],          [],          [],          [],          [],          [],          []
        

        rospy.Subscriber("plantar_data",plantar_data,self.ploting_callback, queue_size=1)

        rospy.loginfo("RUNING MAIN FUNC ... ")

        rospy.spin()

    def ploting_callback(self, plantar_data):
        if self.plot_flag:
            self.fig = plt.figure(figsize=(8, 4))
            self.ax1 = self.fig.add_subplot(4,4,1)
            self.ax2 = self.fig.add_subplot(4,4,2)
            self.ax3 = self.fig.add_subplot(4,4,3)
            self.ax4 = self.fig.add_subplot(4,4,4)
            self.ax5 = self.fig.add_subplot(4,4,5)
            self.ax6 = self.fig.add_subplot(4,4,6)
            self.ax7 = self.fig.add_subplot(4,4,7)
            self.ax8 = self.fig.add_subplot(4,4,8)
            self.ax9 = self.fig.add_subplot(4,4,9)
            self.ax10 = self.fig.add_subplot(4,4,10)
            self.ax11 = self.fig.add_subplot(4,4,11)
            self.ax12 = self.fig.add_subplot(4,4,12)
            self.ax13 = self.fig.add_subplot(4,4,13)
            self.ax14 = self.fig.add_subplot(4,4,14)
            self.ax15 = self.fig.add_subplot(4,4,15)
            self.ax16 = self.fig.add_subplot(4,4,16)
            self.plot_flag = False

        data = np.array(plantar_data.data, dtype=float)

        
        self.plot_x.append(self.plot_time)
        self.data_1.append(data[0])
        self.data_2.append(data[1])
        self.data_3.append(data[2])
        self.data_4.append(data[3])
        self.data_5.append(data[4])
        self.data_6.append(data[5])
        self.data_7.append(data[6])
        self.data_8.append(data[7])
        self.data_9.append(data[8])
        self.data_10.append(data[9])
        self.data_11.append(data[10])
        self.data_12.append(data[11])
        self.data_13.append(data[12])
        self.data_14.append(data[13])
        self.data_15.append(data[14])
        self.data_16.append(data[15])

        if len(self.plot_x) > self.xlim_width:
            del(self.plot_x[0])
            del(self.data_1[0])
            del(self.data_2[0])
            del(self.data_3[0])
            del(self.data_4[0])
            del(self.data_5[0])
            del(self.data_6[0])
            del(self.data_7[0])
            del(self.data_8[0])
            del(self.data_9[0])
            del(self.data_10[0])
            del(self.data_11[0])
            del(self.data_12[0])
            del(self.data_13[0])
            del(self.data_14[0])
            del(self.data_15[0])
            del(self.data_16[0])

        self.plot_time = self.plot_time + 1

        self.ax1.cla()
        self.ax2.cla()
        self.ax3.cla()
        self.ax4.cla()
        self.ax5.cla()
        self.ax6.cla()
        self.ax7.cla()
        self.ax8.cla()
        self.ax9.cla()
        self.ax10.cla()
        self.ax11.cla()
        self.ax12.cla()
        self.ax13.cla()
        self.ax14.cla()
        self.ax15.cla()
        self.ax16.cla()
        
        if len(self.plot_x) < self.xlim_width:
            self.ax1.set_xlim(0, self.xlim_width)
            self.ax2.set_xlim(0, self.xlim_width)
            self.ax3.set_xlim(0, self.xlim_width)
            self.ax4.set_xlim(0, self.xlim_width)
            self.ax5.set_xlim(0, self.xlim_width)
            self.ax6.set_xlim(0, self.xlim_width)
            self.ax7.set_xlim(0, self.xlim_width)
            self.ax8.set_xlim(0, self.xlim_width)
            self.ax9.set_xlim(0, self.xlim_width)
            self.ax10.set_xlim(0, self.xlim_width)
            self.ax11.set_xlim(0, self.xlim_width)
            self.ax12.set_xlim(0, self.xlim_width)
            self.ax13.set_xlim(0, self.xlim_width)
            self.ax14.set_xlim(0, self.xlim_width)
            self.ax15.set_xlim(0, self.xlim_width)
            self.ax16.set_xlim(0, self.xlim_width)
        else:
            self.ax1.set_xlim(self.plot_x[-1]-len(self.plot_x), self.plot_x[-1])
            self.ax2.set_xlim(self.plot_x[-1]-len(self.plot_x), self.plot_x[-1])
            self.ax3.set_xlim(self.plot_x[-1]-len(self.plot_x), self.plot_x[-1])
            self.ax4.set_xlim(self.plot_x[-1]-len(self.plot_x), self.plot_x[-1])
            self.ax5.set_xlim(self.plot_x[-1]-len(self.plot_x), self.plot_x[-1])
            self.ax6.set_xlim(self.plot_x[-1]-len(self.plot_x), self.plot_x[-1])
            self.ax7.set_xlim(self.plot_x[-1]-len(self.plot_x), self.plot_x[-1])
            self.ax8.set_xlim(self.plot_x[-1]-len(self.plot_x), self.plot_x[-1])
            self.ax9.set_xlim(self.plot_x[-1]-len(self.plot_x), self.plot_x[-1])
            self.ax10.set_xlim(self.plot_x[-1]-len(self.plot_x), self.plot_x[-1])
            self.ax11.set_xlim(self.plot_x[-1]-len(self.plot_x), self.plot_x[-1])
            self.ax12.set_xlim(self.plot_x[-1]-len(self.plot_x), self.plot_x[-1])
            self.ax13.set_xlim(self.plot_x[-1]-len(self.plot_x), self.plot_x[-1])
            self.ax14.set_xlim(self.plot_x[-1]-len(self.plot_x), self.plot_x[-1])
            self.ax15.set_xlim(self.plot_x[-1]-len(self.plot_x), self.plot_x[-1])
            self.ax16.set_xlim(self.plot_x[-1]-len(self.plot_x), self.plot_x[-1])

        self.ax1.set_ylim(self.y_min, self.y_max)
        self.ax2.set_ylim(self.y_min, self.y_max)
        self.ax3.set_ylim(self.y_min, self.y_max)
        self.ax4.set_ylim(self.y_min, self.y_max)
        self.ax5.set_ylim(self.y_min, self.y_max)
        self.ax6.set_ylim(self.y_min, self.y_max)
        self.ax7.set_ylim(self.y_min, self.y_max)
        self.ax8.set_ylim(self.y_min, self.y_max)
        self.ax9.set_ylim(self.y_min, self.y_max)
        self.ax10.set_ylim(self.y_min, self.y_max)
        self.ax11.set_ylim(self.y_min, self.y_max)
        self.ax12.set_ylim(self.y_min, self.y_max)
        self.ax13.set_ylim(self.y_min, self.y_max)
        self.ax14.set_ylim(self.y_min, self.y_max)
        self.ax15.set_ylim(self.y_min, self.y_max)
        self.ax16.set_ylim(self.y_min, self.y_max)
        
        
        self.ax1.plot(self.plot_x, self.data_1)
        self.ax2.plot(self.plot_x, self.data_2)
        self.ax3.plot(self.plot_x, self.data_3)
        self.ax4.plot(self.plot_x, self.data_4)
        self.ax5.plot(self.plot_x, self.data_5)
        self.ax6.plot(self.plot_x, self.data_6)
        self.ax7.plot(self.plot_x, self.data_7)
        self.ax8.plot(self.plot_x, self.data_8)
        self.ax9.plot(self.plot_x, self.data_9)
        self.ax10.plot(self.plot_x, self.data_10)
        self.ax11.plot(self.plot_x, self.data_11)
        self.ax12.plot(self.plot_x, self.data_12)
        self.ax13.plot(self.plot_x, self.data_13)
        self.ax14.plot(self.plot_x, self.data_14)
        self.ax15.plot(self.plot_x, self.data_15)
        self.ax16.plot(self.plot_x, self.data_16)
        

        plt.pause(0.1)




PlotCurve()