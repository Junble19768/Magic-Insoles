#include <iostream>
#include <stdio.h>
#include <cstring>
#include <stdlib.h>
#include <math.h>
//#include <unistd.h>
//#include <arpa/inet.h>
//#include <sys/socket.h>
//#include <netinet/in.h>
#include "usb-daq-v20.h"
#include <iomanip>


using namespace std;
typedef char BYTE;
#define MAXLEN 32
#define BUF_SIZE 1024


//int  opened=0;
bool loop_signal = true;



int main(int argc, char **argv){
	
	int count = 0;
	float temp_data[MAXLEN];
	float tactile_data[MAXLEN];

	int device_id = 0;
	int device_id_0 = 0;
	int device_id_1 = 1;

	int chan_first = 0;
	int chan_last = 7;  // from AD0 - AD7
	int num_sample = 8;
	int frequency = 1000;  // sample frequency min = 100 | max = 100000


	unsigned char ON = 1;  //  3.3V
	unsigned char OFF = 0; // 0.0V
	
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
		if (0 == DoSetV20(device_id_0, Dout_chan,OFF) && 0 == DoSetV20(device_id_1, Dout_chan,OFF))
        {
            loop_signal = true;
        } 
		else{
			printf("device initial failed\n");  
			loop_signal = false;
		}   
	} // inital Dout channels

	//initial socket
	int serv_sock = socket(AF_INET, SOCK_STREAM, IPPROTO_TCP);
	int clnt_sock = -1;


	//run socket
	if(loop_signal){
		
		struct sockaddr_in serv_addr;
		memset(&serv_addr, 0, sizeof(serv_addr));
		serv_addr.sin_family = AF_INET;
		serv_addr.sin_addr.s_addr = inet_addr("172.20.10.4");
		serv_addr.sin_port = htons(6543);
		bind(serv_sock, (struct sockaddr*)&serv_addr, sizeof(serv_addr));
	
		listen(serv_sock, 10);
		cout << "listening..." << endl;
		
		struct sockaddr_in clnt_addr;
		socklen_t clnt_addr_size = sizeof(clnt_addr);
		do{
			clnt_sock = accept(serv_sock, (struct sockaddr*)&clnt_addr, &clnt_addr_size);
			if(clnt_sock < 0){
				cout << "Connected Error, re-try to get connected with client..." << endl;
			}
		}while(clnt_sock < 0);
	}
	
	// while(loop_signal && TermSignal::ok()){
	// for (int cnt=0; cnt<100; cnt++){
	while (loop_signal){
		count++;
		for(int Dout_chan = 0; Dout_chan < 6; Dout_chan++){
			if (2 == Dout_chan){
				if(0 == DoSetV20(device_id_0, Dout_chan,ON) && 0 == DoSetV20(device_id_1, Dout_chan,ON)){
					ADSingleV20(device_id_0,1,&tactile_data[0]);
					ADSingleV20(device_id_0,2,&tactile_data[1]);

                    ADSingleV20(device_id_1,1,&tactile_data[16]);
					ADSingleV20(device_id_1,2,&tactile_data[17]);

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
					ADSingleV20(device_id_0,1,&tactile_data[2]);
					ADSingleV20(device_id_0,2,&tactile_data[3]);

                    ADSingleV20(device_id_1,1,&tactile_data[18]);
					ADSingleV20(device_id_1,2,&tactile_data[19]);
				}
				DoSetV20(device_id_0, Dout_chan,OFF);
				DoSetV20(device_id_1, Dout_chan,OFF);
			}

			else if (1 == Dout_chan){
				if(0 == DoSetV20(device_id_0, Dout_chan,ON) && 0 == DoSetV20(device_id_1, Dout_chan,ON)){
					ADSingleV20(device_id_0,1,&tactile_data[4]);
					ADSingleV20(device_id_0,2,&tactile_data[5]);
					ADSingleV20(device_id_0,3,&tactile_data[6]);

                    ADSingleV20(device_id_1,1,&tactile_data[20]);
					ADSingleV20(device_id_1,2,&tactile_data[21]);
					ADSingleV20(device_id_1,3,&tactile_data[22]);
                    

				}
				DoSetV20(device_id_0, Dout_chan,OFF);
				DoSetV20(device_id_1, Dout_chan,OFF);
			}

			else if (4 == Dout_chan){
                if(0 == DoSetV20(device_id_0, Dout_chan,ON) && 0 == DoSetV20(device_id_1, Dout_chan,ON)){
					ADSingleV20(device_id_0,3,&tactile_data[7]);

					ADSingleV20(device_id_1,3,&tactile_data[23]);


				}
				DoSetV20(device_id_0, Dout_chan,OFF);
				DoSetV20(device_id_1, Dout_chan,OFF);
			}

			else if (0 == Dout_chan){
                if(0 == DoSetV20(device_id_0, Dout_chan,ON) && 0 == DoSetV20(device_id_1, Dout_chan,ON)){
					ADSingleV20(device_id_0,0,&tactile_data[8]);
					ADSingleV20(device_id_0,1,&tactile_data[9]);
					ADSingleV20(device_id_0,2,&tactile_data[10]);
					ADSingleV20(device_id_0,3,&tactile_data[11]);

                    ADSingleV20(device_id_1,0,&tactile_data[24]);
					ADSingleV20(device_id_1,1,&tactile_data[25]);
					ADSingleV20(device_id_1,2,&tactile_data[26]);
					ADSingleV20(device_id_1,3,&tactile_data[27]);
				}
				DoSetV20(device_id_0, Dout_chan,OFF);
				DoSetV20(device_id_1, Dout_chan,OFF);
			}

			else if (5 == Dout_chan){
                if(0 == DoSetV20(device_id_0, Dout_chan,ON) && 0 == DoSetV20(device_id_1, Dout_chan,ON)){
					ADSingleV20(device_id_0,0,&tactile_data[12]);
					ADSingleV20(device_id_0,1,&tactile_data[13]);
					ADSingleV20(device_id_0,2,&tactile_data[14]);
					ADSingleV20(device_id_0,3,&tactile_data[15]);

                    ADSingleV20(device_id_1,0,&tactile_data[28]);
					ADSingleV20(device_id_1,1,&tactile_data[29]);
					ADSingleV20(device_id_1,2,&tactile_data[30]);
					ADSingleV20(device_id_1,3,&tactile_data[31]);
				}
				DoSetV20(device_id_0, Dout_chan,OFF);
				DoSetV20(device_id_1, Dout_chan,OFF);
			}

			else{
				// ROS_INFO("Dout channel %d \n", Dout_chan);
				cout << "Dout channal" << Dout_chan << " read data failed" << endl;
			}     
		}
		char sendbuf[BUF_SIZE] ={ 0 };
		memset(sendbuf, 0, BUF_SIZE);
		memcpy(&sendbuf, &tactile_data, BUF_SIZE);
		int sendLen = send(clnt_sock, sendbuf, BUF_SIZE, 0);
		if(sendLen < 0){
			cout << "Read Error ... " << endl;
			continue;
		}
		memset(&temp_data, 0, sizeof(temp_data));
		memset(&tactile_data, 0, sizeof(tactile_data));

	}

	DoSetV20(device_id_0, 7,OFF);
	DoSetV20(device_id_1, 7,OFF);
	close(clnt_sock);
	close(serv_sock);
	
	CloseUsbV20();
	
	cout << "--> exit ! <--" << endl;

	return 0;
}
