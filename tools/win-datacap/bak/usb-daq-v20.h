
 

#ifdef __cplusplus
extern "C" {
#endif

 
 
// *********** 设备打开函数，成功返回0 ***********
	int  OpenUsbV20(void);
	int  OpenUsbV20_V2(void);    // 修复连接多个采集卡报错bug -- WuBing

// *********** 设备关闭函数，成功返回0 ***********
	int  CloseUsbV20(void);



// *********** 获取设备数量函数，成功返回0 ***********
	int  GetDeviceCountV20(void);

 // *********** USB设备重新挂载函数，成功返回0，然后需要重新打开设备 ***********
	int    Reset_Usb_DeviceV20(int dev);
 

// *********** 单次获取AD采集结果，成功返回0 ***********
	int  ADSingleV20(int dev,int chan,float* adResult);

// *********** 单通道获取AD采集结果，成功返回0 ***********
	int  ADContinuV20(int dev,int chan,int Num_Sample,int Frequency,float  *databuf);

// *********** 获取多通道AD采集结果，成功返回0 ***********
	int  MADContinuV20(int dev,int chan_first,int chan_last,int Num_Sample,int Frequency,float  *mad_data);






// *********** DA通道单值输出，成功返回0 ***********
	int  DASingleOutV20(int dev,int chan,int value);

// *********** DA通道扫描数据发送，成功返回0 ***********
	int  DADataSendV20(int dev,int chan,int Num,int *databuf);

// *********** DA通道扫描输出设置，成功返回0 ***********
	int  DAScanOutV20(int dev,int chan,int Freq,int scan_Num);

// *********** PWM输出设置，成功返回0 ***********
	int  PWMOutSetV20(int dev,int chan,int Freq,float DutyCycle);

// *********** PWM输入设置，成功返回0 ***********
	int  PWMInSetV20(int dev,int mod);

// *********** PWM输入结果获取，成功返回0 ***********
	int  PWMInReadV20(int dev,float* Freq, int* DutyCycle);

// *********** 计数器输入设置，成功返回0 ***********
	int  CountSetV20(int dev,int mod);

// *********** 计数器结果读取，成功返回0 ***********
	int  CountReadV20(int dev,int* count);

// *********** 开关量输出设定，成功返回0 ***********
	int  DoSetV20(int dev,unsigned char chan,unsigned char state);

// *********** 开关量输入获取，成功返回0 ***********
	int  DiReadV20(int dev,unsigned char *value);

// *********** 获取设备ID号，成功返回0 ***********
	unsigned int  GetCardIdV20(int dev);


#ifdef __cplusplus
}
#endif
