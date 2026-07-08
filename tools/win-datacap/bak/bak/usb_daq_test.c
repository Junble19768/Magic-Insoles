#include <math.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>

#include "usb-daq-v20.h"

/*
g++ usb_daq_test.c usb-daq-v20.cpp -Ilibusb/include -Llibusb/lib -lusb-1.0 -o
usb_daq_test.exe

*/

int main() {
  if (-1 == OpenUsbV20()) {
    printf("####usb  device open fail ####\n");
    return -1;
  } else {
    printf("####usb  device open ok  ####\n");
  }
  int i;
  for (i = 0; i < 8; i = i + 2) {
    DoSetV20(0, i, 1);
    printf("### write Dout-%d set 1  ####\n", i);
  }
  for (i = 1; i < 8; i = i + 2) {
    DoSetV20(0, i, 0);
    printf("### write Dout-%d set 0  ####\n", i);
  }
  unsigned char DI = 0;
  DiReadV20(0, &DI);
  printf("####Din = %x\n", DI);

  DASingleOutV20(0, 1, (int)(1.5 * 4095 / 3.3));
  printf("####DusbEMO  device DA1 output 1.5V  ####\n");

  DASingleOutV20(0, 2, (int)(2.8 * 4095 / 3.3));
  printf("####DusbEMO  device DA1 output 2.8V  ####\n");

  PWMOutSetV20(0, 0, 10, 30.5);
  printf("####DusbEMO  device PWM0 output FREq=10hz,duty=30.5%  ####\n");

  PWMOutSetV20(0, 1, 100, 40.5);
  printf("####DusbEMO  device PWM0 output FREq=100hz,duty=40.5%  ####\n");

  float adResult1;

  for (i = 0; i < 12; i++) {
    // ADSingleV12(int dev,int ad_mod, int chan, int gain, float* adResult);
    if (ADSingleV20(0, i, &adResult1) == 0) {
      printf("AD_single read ad %d =%f\n", i, adResult1);
    } else {
      printf("read ad %d fail!\n", i);
    }
  }
  float data[1024];

  // int  ADContinuV20(int dev,int chan,int Num_Sample,int Frequency,float
  // *databuf);
  if (ADContinuV20(0, 0, 1024, 10000, data) == 0) {
    for (i = 0; i < 50; i++) {
      printf("AD_continu ad[%d]=%f\n", i, data[i]);
    }
  } else {
    printf("AD_continu read ad fail!\n");
  }
  CloseUsbV20();

  return 0;
}
