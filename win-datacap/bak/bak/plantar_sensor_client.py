#!/usr/bin/env python3

import socket
import struct
import numpy as np
import os, sys

import rospy
from plantar_sensor.msg import two_plantar_data

class Plot_tactile:
    def __init__(self):
        host = "192.168.1.101"
        port = 6543
        
        rospy.init_node("tactile_plantar")
        self.plantar_pub = rospy.Publisher('/two_plantar_data', two_plantar_data, queue_size=1)

        mySocket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        while mySocket.connect((host, port)) == socket.error:
            print("Connection ERROR! Now re-try to get connected ...")
        print("running main func")

        self.plantar_data_msg = two_plantar_data()

        # before 2023.10.08
        # try:
        #     while True:
        #         msg = mySocket.recv(1024)
        #         tactile_data = []
        #         for i in range(256):
        #             msg_single = msg[i*4: (i*4)+4]
        #             try:
        #                 data_single = struct.unpack('f', msg_single)
        #             except:
        #                 data_single = [0]
        #             tactile_data.append(float(data_single[0]))
        #         self.publish(tactile_data)
                
        # except KeyboardInterrupt:
        #     print(" Client shut down !")
        #     mySocket.close()

        try:
            while True:
                msg = mySocket.recv(1024)
                tactile_data = []
                for i in range(256):
                    msg_single = msg[i*4: (i*4)+4]
                    try:
                        data_single = struct.unpack('f', msg_single)
                        tactile_data.append(float(data_single[0]))
                    except struct.error:
                        # 如果解析失败，可以将一个默认值（例如0.0）添加到 tactile_data
                        tactile_data.append(0.0)
                self.publish(tactile_data)
        except KeyboardInterrupt:
            print(" Client shut down !")
            mySocket.close()

        
        
    def publish(self, tactile_data):
        # data = np.array(tactile_data, dtype=float)  # 32x1 np
        # tactile_data = tactile_data[0:31] 
        self.plantar_data_msg.data =  tactile_data[0:32]
        # print(type(tactile_data[0]))
        # os._exit(0)
        self.plantar_pub.publish(self.plantar_data_msg)
        
            
if __name__ == "__main__":
    Plot_tactile()
