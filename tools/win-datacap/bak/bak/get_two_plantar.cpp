#include <stdio.h>
#include <string.h>
#include <stdlib.h>
#include <math.h>
#include <sstream>
#include <iostream>


#include "ros/ros.h"
#include "plantar_sensor/two_plantar_data.h"

#include "usb-daq-v20.h"
 
typedef char BYTE;

bool loop_signal = true;

int main(int argc, char **argv)
{
	float temp_data[16];
	int device_id_0 = 0;
	int device_id_1 = 1;

	const unsigned char ON = 1;  //  3.3V
	const unsigned char OFF = 0; // 0.0V

	// ROS节点初始化
	ros::init(argc, argv, "plantar_sensor");
	ros::NodeHandle n;
	ros::Publisher tactile_data_pub = n.advertise<plantar_sensor::two_plantar_data>("two_plantar_data", 1);
	ros::Rate loop_rate(200);       // message rate Hz

	printf("starting\n");

	// 连接设备
    if(-1==OpenUsbV20_V2()){
		printf("usb  device open fail \n");
		return -1;
    }
    else {printf("usb device id = %d  \n", GetDeviceCountV20());}
	if (0 ==DoSetV20(device_id_0, 7,ON)){
		printf("device_id_0 initial success\n"); 
	}
    if (0 ==DoSetV20(device_id_1, 7,ON)){
		printf("device_id_1 initial success\n"); 
	}

	// 将输出全部置位0
	for(int Dout_chan = 0; Dout_chan < 6; Dout_chan++){
		if (0 == DoSetV20(device_id_0, Dout_chan,OFF) && 0 == DoSetV20(device_id_0, Dout_chan,OFF))
        {
            loop_signal = true;
        } 
		else{
			printf("device initial failed\n");  
			loop_signal = false;
		}   
	} // inital Dout channels

    // DoSetV20(device_id_0, 4,ON);
    // DoSetV20(device_id_1, 4,ON);

    // while (1){
    //     ADSingleV20(device_id_0,3,&temp_data[0]);
    //     ADSingleV20(device_id_1,3,&temp_data[16]);
    //     std::cout << temp_data[0] << " | " << temp_data[16]  << std::endl;
    // }


    float temp_i ;
	plantar_sensor::two_plantar_data plantar_data_msg;
	while (ros::ok() and loop_signal){
		// printf("------------------------------------\n");
		for(int Dout_chan = 0; Dout_chan < 6; Dout_chan++){
			if (2 == Dout_chan){
				if(0 == DoSetV20(device_id_0, Dout_chan,ON) && 0 == DoSetV20(device_id_1, Dout_chan,ON)){
					ADSingleV20(device_id_0,1,&plantar_data_msg.data[0]);
					ADSingleV20(device_id_0,2,&plantar_data_msg.data[1]);

                    ADSingleV20(device_id_1,1,&plantar_data_msg.data[16]);
					ADSingleV20(device_id_1,2,&plantar_data_msg.data[17]);

                    // ADSingleV20(device_id_0,1,&temp_i);
                    // std::cout << temp_i << " |*| " ;
					// ADSingleV20(device_id_1,1,&temp_i);
                    // std::cout << temp_i << std::endl;
				}
				DoSetV20(device_id_0, Dout_chan,OFF);
				DoSetV20(device_id_1, Dout_chan,OFF);
			}
			else if (3 == Dout_chan){
				if(0 == DoSetV20(device_id_0, Dout_chan,ON) && 0 == DoSetV20(device_id_1, Dout_chan,ON)){
					ADSingleV20(device_id_0,1,&plantar_data_msg.data[2]);
					ADSingleV20(device_id_0,2,&plantar_data_msg.data[3]);

                    ADSingleV20(device_id_1,1,&plantar_data_msg.data[18]);
					ADSingleV20(device_id_1,2,&plantar_data_msg.data[19]);
				}
				DoSetV20(device_id_0, Dout_chan,OFF);
				DoSetV20(device_id_1, Dout_chan,OFF);
			}

			else if (1 == Dout_chan){
				if(0 == DoSetV20(device_id_0, Dout_chan,ON) && 0 == DoSetV20(device_id_1, Dout_chan,ON)){
					ADSingleV20(device_id_0,1,&plantar_data_msg.data[4]);
					ADSingleV20(device_id_0,2,&plantar_data_msg.data[5]);
					ADSingleV20(device_id_0,3,&plantar_data_msg.data[6]);

                    ADSingleV20(device_id_1,1,&plantar_data_msg.data[20]);
					ADSingleV20(device_id_1,2,&plantar_data_msg.data[21]);
					ADSingleV20(device_id_1,3,&plantar_data_msg.data[22]);
                    

				}
				DoSetV20(device_id_0, Dout_chan,OFF);
				DoSetV20(device_id_1, Dout_chan,OFF);
			}

			else if (4 == Dout_chan){
                if(0 == DoSetV20(device_id_0, Dout_chan,ON) && 0 == DoSetV20(device_id_1, Dout_chan,ON)){
					ADSingleV20(device_id_0,3,&plantar_data_msg.data[7]);

					ADSingleV20(device_id_1,3,&plantar_data_msg.data[23]);


				}
				DoSetV20(device_id_0, Dout_chan,OFF);
				DoSetV20(device_id_1, Dout_chan,OFF);
			}

			else if (0 == Dout_chan){
                if(0 == DoSetV20(device_id_0, Dout_chan,ON) && 0 == DoSetV20(device_id_1, Dout_chan,ON)){
					ADSingleV20(device_id_0,0,&plantar_data_msg.data[8]);
					ADSingleV20(device_id_0,1,&plantar_data_msg.data[9]);
					ADSingleV20(device_id_0,2,&plantar_data_msg.data[10]);
					ADSingleV20(device_id_0,3,&plantar_data_msg.data[11]);

                    ADSingleV20(device_id_1,0,&plantar_data_msg.data[24]);
					ADSingleV20(device_id_1,1,&plantar_data_msg.data[25]);
					ADSingleV20(device_id_1,2,&plantar_data_msg.data[26]);
					ADSingleV20(device_id_1,3,&plantar_data_msg.data[27]);
				}
				DoSetV20(device_id_0, Dout_chan,OFF);
				DoSetV20(device_id_1, Dout_chan,OFF);
			}

			else if (5 == Dout_chan){
                if(0 == DoSetV20(device_id_0, Dout_chan,ON) && 0 == DoSetV20(device_id_1, Dout_chan,ON)){
					ADSingleV20(device_id_0,0,&plantar_data_msg.data[12]);
					ADSingleV20(device_id_0,1,&plantar_data_msg.data[13]);
					ADSingleV20(device_id_0,2,&plantar_data_msg.data[14]);
					ADSingleV20(device_id_0,3,&plantar_data_msg.data[15]);

                    ADSingleV20(device_id_1,0,&plantar_data_msg.data[28]);
					ADSingleV20(device_id_1,1,&plantar_data_msg.data[29]);
					ADSingleV20(device_id_1,2,&plantar_data_msg.data[30]);
					ADSingleV20(device_id_1,3,&plantar_data_msg.data[31]);
				}
				DoSetV20(device_id_0, Dout_chan,OFF);
				DoSetV20(device_id_1, Dout_chan,OFF);
			}

			else{
				ROS_INFO("Dout channel %d \n", Dout_chan);
			}     
	}
		tactile_data_pub.publish(plantar_data_msg);
	}

	DoSetV20(device_id_0, 7,OFF);
	DoSetV20(device_id_1, 7,OFF);
	CloseUsbV20();
    
 	return 0;
}
