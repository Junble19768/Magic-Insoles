
#include <stdio.h>
#include <string.h>
#include <sys/types.h>

#include <sys/stat.h>
#include <stdlib.h>
#include <fcntl.h>
#include <unistd.h>  
//#include <vector>
#include <list>
//#include <deque.h>
#include <queue>
// #include <pthread.h>
//#include <linux/mutex.h>
#include"usb-daq-v20.h" 
#include "libusb.h"            
//#include <mutex>
#include <iostream>
 

//usb_dev_handle *dev_h = NULL;  // the device handle
int  opened=0;
int dev_num;	
 struct libusb_device **devs;
struct libusb_device *device[16];  //
struct libusb_device_handle *dev_handle[16];	//
struct libusb_device *DeviceCurrent=NULL;//
 
int DeviceCount;			 //
 
#define EP_IN1 0x81
#define EP_IN2 0x82
#define EP_IN3 0x83
#define EP_IN4 0x84
#define EP_IN5 0x85
#define EP_IN6 0x86
#define EP_IN7 0x87

#define EP_OUT1 0x01
#define EP_OUT2 0x02
#define EP_OUT3 0x03
#define EP_OUT4 0x04
#define EP_OUT5 0x05
#define EP_OUT6 0x06
#define EP_OUT7 0x07

#define pi 3.1415926
#define MY_VID        0x7812
#define MY_PID        0x55A9
#define TRANSFER_TIMEOUT 6000 /* in msecs */
#define MY_CONFIG 1
#define MY_INTF 0
#define PACKETTIMEOUT 100
#define BUF_SIZE 64
 
int timeout=1000;

int verbose = 0;
 
int Reset_Usb_DeviceV20(int dev)
{
 if(opened==1)
	{
		if(dev_handle[dev]!=NULL)
		{
			if(libusb_reset_device(dev_handle[dev])==0)
			{
				dev_handle[dev]=NULL;
				opened=0;
				return 0;
			}
			else
			{
				dev_handle[dev]=NULL;
				opened=0;
				return -2;
			}
		}
	}
	return -1;
}
int OpenUsbV20(void)
{
	if(opened==1)
	{
		CloseUsbV20();
		opened=0;
	}
	struct libusb_device *dev;
	struct libusb_device_handle *handle = NULL;
	size_t i = 0;
	int j=0;
	int r;
	r = libusb_init(NULL);
	if (r < 0)
		return r;
	if (libusb_get_device_list(NULL, &devs) < 0)
		return NULL;

	while ((dev = devs[i++]) != NULL) {
		struct libusb_device_descriptor desc;
		r = libusb_get_device_descriptor(dev, &desc);
		if (r < 0)
		{
			libusb_free_device_list(devs, 1);
			return -1;
		}
		printf("####VID = %x;PID = %x\n",desc.idVendor,desc.idProduct);
		if ((desc.idVendor == MY_VID ) && (desc.idProduct == MY_PID) ) {
			//found = dev;
			device[j]=dev;
			j++;
			printf("####V devnum = %x\n" ,j);
			if(j>=16)
			break;	
		}
	}
	dev_num=j;
	for(int i=0;i<dev_num;i++){
		printf("####open\n" );
		r = libusb_open(device[i], &handle);
		if (r < 0){
			handle = NULL;
			// handle= libusb_open_device_with_vid_pid(NULL,MY_VID,MY_PID)	;
		}
		if(libusb_claim_interface(handle,0))
		{
			printf("usb_claim_interface error!"); //  cout<<"usb_claim_interface error!  "<<strerror(-tmp)<<endl;
			libusb_free_device_list(devs, 1);
			return -1;
		}
		else
		{
			//USBÉè±ž¿ÉÓÃ£¬³É¹Š·µ»Ø
			printf("success: claim_interface #%d\n", MY_INTF);
			std::cout << "---> " << dev_handle[i] << std::endl;
			// printf("%s", dev_handle[i]);
			//DeviceCurrent=device[i];//±£Žæµ±Ç°Éè±ž
			opened=1;
			dev_handle[i] =handle;
			return 0;
		}
	}
	return -1;
}

int OpenUsbV20_V2(void)
{
	if(opened==1)
	{
		CloseUsbV20();
		opened=0;
	}
	struct libusb_device *dev;
	struct libusb_device_handle *handle = NULL;
	size_t i = 0;
	int j=0;
	int r;
	r = libusb_init(NULL);
	if (r < 0)
		return r;
	if (libusb_get_device_list(NULL, &devs) < 0)
		return NULL;

	while ((dev = devs[i++]) != NULL) {
		struct libusb_device_descriptor desc;
		r = libusb_get_device_descriptor(dev, &desc);
		if (r < 0)
		{
			libusb_free_device_list(devs, 1);
			return -1;
		}
		printf("####VID = %x;PID = %x\n",desc.idVendor,desc.idProduct);
		if ((desc.idVendor == MY_VID ) && (desc.idProduct == MY_PID) ) {
			//found = dev;
			device[j]=dev;
			j++;
			printf("####V devnum = %x\n" ,j);
			if(j>=16)
				break;	
		}
	}
	dev_num=j;
	for(int i=0;i<dev_num;i++){
		printf("####open\n" );
		r = libusb_open(device[i], &handle);
		if (r < 0){
			handle = NULL;
			// handle= libusb_open_device_with_vid_pid(NULL,MY_VID,MY_PID)	;
			return -1;

		}
		if(libusb_claim_interface(handle,0))
		{
			printf("usb_claim_interface error!"); //  cout<<"usb_claim_interface error!  "<<strerror(-tmp)<<endl;
			libusb_free_device_list(devs, 1);
			return -1;
		}
		else
		{
			//USBÉè±ž¿ÉÓÃ£¬³É¹Š·µ»Ø
			printf("success: claim_interface #%d\n", MY_INTF);
			//DeviceCurrent=device[i];//±£Žæµ±Ç°Éè±ž
			opened=1;
			dev_handle[i] =handle;
			std::cout << "---> " << dev_handle[i] << std::endl;

			// return 0;
		}
	}
	return 0;
	// return -1;
}

int GetDeviceCountV20(void)
{
	if(opened==1)
	return dev_num;
		else
	return 0;
}

int CloseUsbV20(void)
{
	if(opened==1)
	{
		opened=0;
		for(int i=0;i<dev_num;i++)
		{
				if(dev_handle[i]==NULL)
				{
					return-1;
				}
				libusb_release_interface(dev_handle[i], 0);
				if (dev_handle)
				{
					libusb_close(dev_handle[i]);
		
				}
		}
			libusb_free_device_list(devs, 1);
		libusb_exit(NULL);
		printf("Done.\n");
		return 0;
	}
	return -2;
}
int usb_bulk_write(int dev, unsigned char endpoint,  unsigned  char *data, int length,unsigned int timeout) 
{
	int transferred=0;
	// std::cout << "=====> usb_bulk_write" << dev_handle[dev] << std::endl;;
	libusb_bulk_transfer(dev_handle[dev], endpoint,(unsigned char *)data, length, &transferred, timeout);
	return transferred;
}
int usb_bulk_read(int dev, unsigned char endpoint, unsigned char *data, int length,unsigned int timeout) 
{
	int transferred=0;

	libusb_bulk_transfer( dev_handle[dev], endpoint,(unsigned char *)data, length, &transferred, timeout);
	return transferred;
}
/*
int WriteUsb(int dev,unsigned char dwPipeNum,unsigned char *pBuffer,int dwSize)
{
if((dev<0)||(dev>=dev_num)) return 1;
int ret;
//printf("####write start####\n");
  ret = usb_bulk_write(dev_handle[dev], (unsigned char)dwPipeNum,(unsigned char *)pBuffer, dwSize,TRANSFER_TIMEOUT);
  if(ret>0)
	{
//	printf("####write end####\n");
	   return 0;
	}
  else
	  return 1;
	
}
int ReadUsb(int dev,unsigned char dwPipeNum,unsigned char *pBuffer,int dwSize)
{
if((dev<0)||(dev>=dev_num)) return 1;
	int ret;
//printf("####read start####\n");
  ret = usb_bulk_xxread(dev_handle[dev], (unsigned char)dwPipeNum,(unsigned char *)pBuffer, dwSize,TRANSFER_TIMEOUT);
  if(ret>0)
   {
//	printf("####read end####\n");
	   return 0;
	}
  else
	  return 1;
}
 */
 
// *********** 单次获取AD采集结果，成功返回0 ***********
int  ADSingleV20(int dev,int chan,float* adResult)
{
	if(opened==0)
		return -1;
	unsigned char  buf[16],inbuf[16];
	//EnterCriticalSection( &critical_ad );
	buf[0]=0;
	buf[1]=0;
	if(2!=usb_bulk_write(dev,EP_OUT1,buf,2,PACKETTIMEOUT))//设置模式 单次采样
		return -1;
	buf[0]=2;
	buf[1]=(unsigned char )chan&0x0f;
	buf[2]=0;
	if(3!=usb_bulk_write(dev,EP_OUT1,buf,3,PACKETTIMEOUT)) //设置采样通道
		return -1;
	buf[0]=1;
	buf[1]=1;
	if(2!=usb_bulk_write(dev,EP_OUT1,buf,2,PACKETTIMEOUT))//启动采集
		return -1;
	//等待时间考虑AD转换时间
	if(2!=usb_bulk_read(dev,EP_IN2,inbuf,2,PACKETTIMEOUT*2)) //读取结果
		return -1;
	float v_adResult;
	v_adResult=(float)(((unsigned int)inbuf[1]<<8)+inbuf[0]);
	// v_adResult=v_adResult*2.5/4096;
	//  v_adResult=(v_adResult-1.25)/vv+1.25;
	//v_adResult=(v_adResult-0.3)/vv+(0.3-1.25)/(vv+1.25);
	//  v_adResult= (1.25- v_adResult)*8.33333333;
	v_adResult=(float)(v_adResult*3.3f/4096.0f);
	*adResult=v_adResult;
	//LeaveCriticalSection( &critical_ad );
	return 0;
 
}
// *********** 单通道获取AD采集结果，成功返回0 ***********
int  ADContinuV20(int dev,int chan,int Num_Sample,int Frequency,float  *databuf)
{
	if(opened==0)
		return -1;
	//EnterCriticalSection( &critical_ad );
	int num=0;
	unsigned char  buf[16],inbuf[1024];
	buf[0]=0;
	buf[1]=1;
	if(2!=usb_bulk_write(dev,EP_OUT1,buf,2,PACKETTIMEOUT))//设置模式 单次采样
		return -1;
	buf[0]=2;
	buf[1]=(unsigned char )chan&0x0f;
	buf[2]=0;
	if(3!=usb_bulk_write(dev,EP_OUT1,buf,3,PACKETTIMEOUT)) //设置采样通道
		return -1;

	buf[0]=3;
	buf[1]=Frequency&0xff;
	buf[2]=(Frequency>>8)&0xff;
	buf[3]=(Frequency>>16)&0xff;
	buf[4]=(Frequency>>24)&0xff;
	if(5!=usb_bulk_write(dev,EP_OUT1,buf,5,PACKETTIMEOUT)) //设置采样频率
		return -1;
	buf[0]=4;
	Num_Sample=Num_Sample-Num_Sample%32;
	if(Num_Sample<0)Num_Sample=0;
	buf[1]=Num_Sample&0xff;
	buf[2]=(Num_Sample>>8)&0xff;
	buf[3]=(Num_Sample>>16)&0xff;
	buf[4]=(Num_Sample>>24)&0xff;
	if(5!=usb_bulk_write(dev,EP_OUT1,buf,5,PACKETTIMEOUT)) //设置采样个数
		return -1;

	buf[0]=1;
	buf[1]=1;
	if(2!=usb_bulk_write(dev,EP_OUT1,buf,2,PACKETTIMEOUT))//启动采集
		return -1;
	int timeout=1000*1024/Frequency+5;
	int ret=usb_bulk_read(dev,EP_IN2,inbuf,2,timeout);
	if(ret!=2)
		return -1;
	//printf("本次采集 %d  ,%d  ,%d  ",ret,inbuf[0],inbuf[1]);

	if(!((inbuf[0]==0x55)&&(inbuf[1]==0xaa)))
	{
		if(2!=usb_bulk_read(dev,EP_IN2,inbuf,2,timeout)) //读取结果
			return -1;
		if(!((inbuf[0]==0x55)&&(inbuf[1]==0xaa)))
		{

		}
	}

	float v_adResult;
	for(int j=0;j<Num_Sample/512;j++)
	{
		//if(ReadUsb(0x82,inbuf,1024)) //读取结果
		ret=usb_bulk_read(dev,EP_IN2,inbuf,1024,timeout); //读取结果
		if(1024!=ret)
			return -1;
		for(int i=0;i<512;i++)
		{	 

			v_adResult=(float)(((unsigned int)inbuf[i*2+1]<<8)+inbuf[i*2]);
			v_adResult=(float)(v_adResult*3.3/4096);
			*databuf=v_adResult;
			databuf++;
		}		
	}
	//LeaveCriticalSection( &critical_ad );
	return 0;
 
}
// *********** 获取多通道AD采集结果，成功返回0 ***********
int  MADContinuV20(int dev,int chan_first,int chan_last,int Num_Sample,int Frequency,float  *mad_data)
{
	if(opened==0)
		return -1;
	//EnterCriticalSection( &critical_ad );
	if((chan_last<chan_first)||(chan_first<0)||(chan_last<0)||(chan_first>15)||(chan_last>15))
		return -1;
	int num=0,i,j;
	unsigned char  buf[16],inbuf[1024];
	buf[0]=0;
	buf[1]=2;
	if(2!=usb_bulk_write(dev,EP_OUT1,buf,2,PACKETTIMEOUT))//设置模式 单次采样
		return -1;
	buf[0]=2;
	buf[1]=(unsigned char )chan_first&0x0f;
	buf[2]=(unsigned char )chan_last&0x0f;
	if(3!=usb_bulk_write(dev,EP_OUT1,buf,3,PACKETTIMEOUT)) //设置采样通道
		return -1;

	buf[0]=3;
	buf[1]=Frequency&0xff;
	buf[2]=(Frequency>>8)&0xff;
	buf[3]=(Frequency>>16)&0xff;
	buf[4]=(Frequency>>24)&0xff;
	if(5!=usb_bulk_write(dev,EP_OUT1,buf,5,PACKETTIMEOUT)) //设置采样频率
		return -1;
	buf[0]=4;
	Num_Sample=Num_Sample-Num_Sample%32;
	if(Num_Sample<0)Num_Sample=0;
	buf[1]=Num_Sample&0xff;
	buf[2]=(Num_Sample>>8)&0xff;
	buf[3]=(Num_Sample>>16)&0xff;
	buf[4]=(Num_Sample>>24)&0xff;
	if(5!=usb_bulk_write(dev,EP_OUT1,buf,5,PACKETTIMEOUT)) //设置采样个数
		return -1;

	buf[0]=1;
	buf[1]=1;
	if(2!=usb_bulk_write(dev,EP_OUT1,buf,2,PACKETTIMEOUT))//启动采集
		return -1;

	int timeout=1000*1024/Frequency+5;		//计算延时
	int ret=usb_bulk_read(dev,EP_IN2,inbuf,2,timeout);
	//printf("本次采集 %d  ,%d  ,%d  ",ret,inbuf[0],inbuf[1]);
	if(!((inbuf[0]==0x55)&&(inbuf[1]==0xaa)))
	{
		if(2!=usb_bulk_read(dev,EP_IN2,inbuf,2,timeout)) //读取结果
			return -1;
		if(!((inbuf[0]==0x55)&&(inbuf[1]==0xaa)))
		{
			return -1;

		}
	}
	float v_adResult;
	for( j=0;j<Num_Sample/512;j++)
	{
		//if(ReadUsb(0x82,inbuf,1024)) //读取结果
		if(1024!=usb_bulk_read(dev,EP_IN2,inbuf,1024,timeout)) //读取结果
			return -1;
		for( i=0;i<512;i++)
		{	 
			v_adResult=(float)(((unsigned int)inbuf[i*2+1]<<8)+inbuf[i*2]);
			v_adResult=(float)(v_adResult*3.3/4096);
			*mad_data=v_adResult ;
			mad_data++;
		}
	}
	//LeaveCriticalSection( &critical_ad );
	return 0;
 
}
// *********** DA通道单值输出，成功返回0 ***********
int  DASingleOutV20(int dev,int chan,int value)
{
	if(opened==0)
		return -1;
	unsigned char  buf[16];
	if(chan==1)
	{
		buf[0]=7;
	}
	else
	{
		buf[0]=8;
	}
	buf[1]=0;//da mod
	buf[2]=0;//da num
	buf[3]=0;

	buf[4]=0;//da freq
	buf[5]=0;
	buf[6]=0;
	buf[7]=0;

	buf[8]= value&0xff;  //da value
	buf[9]=(value>>8)&0xff;

	if(10!=usb_bulk_write(dev,EP_OUT1,buf,10,PACKETTIMEOUT)) //设置采样频率
		return -1;

	return 0;
}
void delay(int ii)
{

	while(1)
	{
		ii--;
		if(ii<1)break;
	}
}
// *********** DA通道扫描数据发送，成功返回0 ***********
int  DADataSendV20(int dev,int chan,int Num,int *databuf)
{
	if(opened==0)
		return -1;
	unsigned char  buf2[64];
	int aa=0,bb=0;
	int i,j;
	if(Num>512)Num=512;
	aa=Num/30;
	bb=Num%30;
	buf2[0]=32;
	buf2[1]=0;
	/*   for(j=2;j<10;j++)
	{
	buf2[j]=j;
	}
	if(WriteUsb(0x2,buf2,10))  
	return -1;
	*/
	buf2[0]=32;
	buf2[1]=0;
	if(aa>0)
	{
		for(i=0;i<aa;i++)
		{
			if(chan==1)
			{
				buf2[2]=(i*30)&0xff;
				buf2[3]=((i*30)>>8)&0xff;
			}
			else
			{
				buf2[2]=(i*30+512)&0xff;
				buf2[3]=((i*30+512)>>8)&0xff;
			}
			for(j=0;j<30;j++)
			{
				buf2[(j<<1)+4]=(*(databuf+i*30+j))&0xff;
				buf2[(j<<1)+5]=((*(databuf+i*30+j))>>8)&0xff;
			}
			if(64!=usb_bulk_write(dev,EP_OUT1,buf2,64,PACKETTIMEOUT)) 
				return -1;
			// delay(1000000);
		}
	}
	if(bb>0)
	{
		if(chan==1)
		{
			buf2[2]=(aa*30)&0xff;
			buf2[3]=((aa*30)>>8)&0xff;
		}
		else
		{
			buf2[2]=(aa*30+512)&0xff;
			buf2[3]=((aa*30+512)>>8)&0xff;
		}
		for(j=0;j<bb;j++)
		{
			buf2[(j<<1)+4]=(*(databuf+aa*30+j))&0xff;
			buf2[(j<<1)+5]=((*(databuf+aa*30+j))>>8)&0xff;
		}
		//if(WriteUsb(0x1,buf2,(bb<<1)+4)) 
		int num=(bb<<1)+4;
		if(num!=usb_bulk_write(dev,EP_OUT1,buf2,num,PACKETTIMEOUT))
			return -1;
		// delay(1000000);
	}

	return 0;
}
// *********** DA通道扫描输出设置，成功返回0 ***********
int  DAScanOutV20(int dev,int chan,int Freq,int scan_Num)
{
	if(opened==0)
		return -1;


	unsigned char  buf[16];
	if(chan==1)
	{
		buf[0]=7;
	}
	else
	{
		buf[0]=8;
	}
	buf[1]=1;//da mod
	buf[2]=scan_Num&0xff;//da num
	buf[3]=(scan_Num>>8)&0xff;

	buf[4]=Freq&0xff;//da freq
	buf[5]=(Freq>>8)&0xff;
	buf[6]=(Freq>>16)&0xff;
	buf[7]=(Freq>>24)&0xff;

	buf[8]=0;  //da value
	buf[9]=0;

	if(10!=usb_bulk_write(dev,EP_OUT1,buf,10,PACKETTIMEOUT))  
		return -1;
	return 0;
}
// *********** PWM输出设置，成功返回0 ***********
int  PWMOutSetV20(int dev,int chan,int Freq,float DutyCycle)
{
	int mod=1;
	int DutyCycle_;
	DutyCycle_=DutyCycle*100;
	if(opened==0)
		return -1;
	unsigned char  buf[16];
	if(chan==1)
	{
		buf[0]=9;
	}
	else
	{
		buf[0]=10;
	}
	buf[1]=mod;//pwm mod
	buf[2]=DutyCycle_&0xff;//PWM_Duty-- 二个bit
	buf[3]=(DutyCycle_>>8)&0xff;

	buf[4]=Freq&0xff;//PWM_Freq--四个bit
	buf[5]=(Freq>>8)&0xff;
	buf[6]=(Freq>>16)&0xff;
	buf[7]=(Freq>>24)&0xff;

	if(8!=usb_bulk_write(dev,EP_OUT1,buf,8,PACKETTIMEOUT))  
		return -1;
	return 0;
}
// *********** PWM输入设置，成功返回0 ***********
int  PWMInSetV20(int dev,int mod)
{

	if(opened==0)
		return -1;
	unsigned char  buf[2];
	buf[0]=11;
	buf[1]=mod;
	if(2!=usb_bulk_write(dev,EP_OUT1,buf,2,PACKETTIMEOUT))// 
		return -1;
	return 0;
}
// *********** PWM输入结果获取，成功返回0 ***********
int  PWMInReadV20(int dev,float* Freq, int* DutyCycle)
{
	if(opened==0)
		return -1;
	unsigned char  inbuf[16];
	if(16!=usb_bulk_read(dev,EP_IN1,inbuf,16,PACKETTIMEOUT)) //读取结果
		return -1;
	if(16!=usb_bulk_read(dev,EP_IN1,inbuf,16,PACKETTIMEOUT)) //读取结果
		return -1;
	* DutyCycle=inbuf[1];
	* DutyCycle+=(unsigned int)inbuf[2]<<8;
	int freq1;
	freq1=inbuf[3];
	freq1+=(unsigned int)inbuf[4]<<8;
	freq1+=(unsigned int)inbuf[5]<<16;
	freq1+=(unsigned int)inbuf[6]<<24;
	* Freq=(float)freq1/10;
	return 0;
}
// *********** 计数器输入设置，成功返回0 ***********
int  CountSetV20(int dev,int mod)
{
	if(opened==0)
		return -1;
	unsigned char  buf[2];
	buf[0]=12;
	buf[1]=mod;
	if(2!=usb_bulk_write(dev,EP_OUT1,buf,2,PACKETTIMEOUT))// 
		return -1;
	return 0;
}
// *********** 计数器结果读取，成功返回0 ***********
int  CountReadV20(int dev,int* count)
{
	if(opened==0)
		return -1;
	unsigned char  inbuf[16];
	if(16!=usb_bulk_read(dev,EP_IN1,inbuf,16,PACKETTIMEOUT)) //读取结果
		return -1;
	if(16!=usb_bulk_read(dev,EP_IN1,inbuf,16,PACKETTIMEOUT)) //读取结果
		return -1;
	* count=inbuf[7];
	* count+=(unsigned int)inbuf[8]<<8;
	* count+=(unsigned int)inbuf[9]<<16;
	* count+=(unsigned int)inbuf[10]<<24;
	return 0;
}
// *********** 开关量输出设定，成功返回0 ***********
int  DoSetV20(int dev,unsigned char chan,unsigned char state)
{
	if(opened==0)
		return -1;
	unsigned char  buf[3];
	buf[0]=13;
	buf[1]=chan;
	buf[2]=state;
	if(3!=usb_bulk_write(dev,EP_OUT1,buf,3,PACKETTIMEOUT))// 
		return -1;
	return 0;
}
// *********** 开关量输入获取，成功返回0 ***********
int  DiReadV20(int dev,unsigned char *value)
{
	if(opened==0)
		return -1;
	unsigned char  inbuf[16];
	if(16!=usb_bulk_read(dev,EP_IN1,inbuf,16,PACKETTIMEOUT)) //读取结果
		return -1;
	if(16!=usb_bulk_read(dev,EP_IN1,inbuf,16,PACKETTIMEOUT)) //读取结果
		return -1;
	*value=inbuf[0];
	return 0;
}
// *********** 获取设备ID号，成功返回0 ***********
unsigned int  GetCardIdV20(int dev)
{
	if(opened==0)
		return -1;
	unsigned char  inbuf[16];
	if(16!=usb_bulk_read(dev,EP_IN1,inbuf,16,PACKETTIMEOUT)) //读取结果
		return 0;
	unsigned int id;
	id=inbuf[12];
	id+=(unsigned int)inbuf[13]<<8;
	id+=(unsigned int)inbuf[14]<<16;
	id+=(unsigned int)inbuf[15]<<24;
	return id;
}

/*
	unsigned int   SetTimer_COUNT(unsigned short mS)
{
  if(opened==0)
	return -1;
  unsigned char  buf[3];
  buf[0]=14;
  buf[1]=(unsigned  char)mS;
  buf[2]=(unsigned  char)(mS>>8);
 //if(WriteUsb(0x1,buf,3))// 
	 if(3!=usb_bulk_write(dev,EP_OUT1,buf,3,PACKETTIMEOUT))//
   return -1;
	return 0;
}
	unsigned int   Read_Diff(unsigned int* count,unsigned int* count1)
{

	if(opened==0)
	return -1;
	unsigned char  inbuf[16];
  if(16!=usb_bulk_read(dev,EP_IN1,inbuf,16,PACKETTIMEOUT)) //读取结果// if(ReadUsb(0x81,inbuf,16)) //读取结果
   return -1;
  if(16!=usb_bulk_read(dev,EP_IN1,inbuf,16,PACKETTIMEOUT)) //读取结果// if(ReadUsb(0x81,inbuf,16)) //读取结果
   return -1;
   
   *count=inbuf[12];
   *count+=(unsigned int)inbuf[13]<<8;
   *count1=(unsigned int)inbuf[14];
   *count1+=(unsigned int)inbuf[15]<<8;
   
	return 0;
}
	unsigned int   Read_COUNT01_PortIN(unsigned int* count0,unsigned int* count1,unsigned char  * PortIN)
{

	if(opened==0)
	return -1;
	unsigned char  inbuf[16];
 if(16!=usb_bulk_read(dev,EP_IN1,inbuf,16,PACKETTIMEOUT)) //读取结果// if(ReadUsb(0x81,inbuf,16)) //读取结果
   return -1;
  if(16!=usb_bulk_read(dev,EP_IN1,inbuf,16,PACKETTIMEOUT)) //读取结果// if(ReadUsb(0x81,inbuf,16)) //读取结果
   return -1;
   
   
  * count0=inbuf[7];
   * count0+=(unsigned int)inbuf[8]<<8;
   * count0+=(unsigned int)inbuf[9]<<16;
   * count0+=(unsigned int)inbuf[10]<<24;

* count1=inbuf[3];
   * count1+=(unsigned int)inbuf[4]<<8;
   * count1+=(unsigned int)inbuf[5]<<16;
   * count1+=(unsigned int)inbuf[6]<<24;

* PortIN= inbuf[0];
	return 0;
}


unsigned int  GetCardIdV12(int dev)
{
	if(opened==0)
		return -1;
	unsigned char  inbuf[BUF_SIZE];	
	if(BUF_SIZE!=usb_bulk_read(dev,EP_IN1,inbuf,BUF_SIZE,PACKETTIMEOUT*10))  
		return 0;
	unsigned int id;
	id=inbuf[12];
	id+=(unsigned int)inbuf[13]<<8;
	id+=(unsigned int)inbuf[14]<<16;
	id+=(unsigned int)inbuf[15]<<24;
	return id;
}
*/














