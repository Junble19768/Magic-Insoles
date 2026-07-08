#include <iostream>
#include <stdio.h>
#include <cstring>
#include <stdlib.h>
#include <math.h>
#include <unistd.h>
#include <arpa/inet.h>
#include <sys/socket.h>
#include <netinet/in.h>
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

	int chan_first = 0;
	int chan_last = 7;  // from AD0 - AD7
	int num_sample = 8;
	int frequency = 1000;  // sample frequency min = 100 | max = 100000


	unsigned char ON = 1;  //  3.3V
	unsigned char OFF = 0; // 0.0V
	
	printf("starting\n");
	
	// open device
	if(-1==OpenUsbV20())
	{
		printf("usb  device open fail \n");
		return -1;
	}
	else
	{
		// device_id = GetDeviceCountV20();
       	printf("usb device id = %d  \n", GetDeviceCountV20());
	}

	// int device_id = 0;
	for(int Dout_chan = 0; Dout_chan < 4; Dout_chan++){
		if (0 == DoSetV20(device_id, Dout_chan,0) and 0 == DoSetV20(device_id, Dout_chan+4,0))
			{
				printf("initial success\n"); 
				loop_signal = true;
			} 
		else{
			printf("initial failed\n");  
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
		serv_addr.sin_addr.s_addr = inet_addr("172.20.10.3");
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
	
	while(loop_signal){
		count++;
		cout << "---------------------------------------------------------------"  << count << endl;
		for(int Dout_chan = 0; Dout_chan < 4; Dout_chan++){
			if(0 == DoSetV20(device_id, Dout_chan,ON) and 0 == DoSetV20(device_id,Dout_chan+4, ON)){
				for(int row=0;row<8;row++)
				{
					if(ADSingleV20(0,row,&temp_data[row+Dout_chan*8])==0)
					{
						cout << setiosflags(ios::fixed) << setprecision(3) << temp_data[row+Dout_chan*8] << " | ";
						tactile_data[row+Dout_chan*8] = temp_data[row+Dout_chan*8];
						// for(int i=0;i<32;i++)
						// 	tactile_data_msg.data[i] = temp_data[i];
						// printf("row = %d , Dout_chan*4 = %d , temp_data[30] = %f, temp_data[31] = %f\n",row, Dout_chan*4,temp_data[30],temp_data[31]);
					}
					else
					{
						cout << "read ad " << row << "fail!" << endl;
						//ROS_INFO("read ad %d fail!\n",row);
					}
				}
				cout << endl;
				//printf("\n");
				DoSetV20(device_id, Dout_chan,OFF);
				DoSetV20(device_id, Dout_chan+4,OFF);
			}
			else{
				cout << "Dout channal" << Dout_chan << "OR Dout channel" << Dout_chan << "read data failed" << endl;
				//ROS_INFO("Dout channel %d OR Dout channel %d read data failed", Dout_chan, Dout_chan+4);
				// Dout_chan--;
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
	close(clnt_sock);
	close(serv_sock);
	
	CloseUsbV20();
	
	return 0;
}
