#ifndef _WIN32_WINNT
#define _WIN32_WINNT 0x0601
#endif

#include <math.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>

#include <array>
#include <asio.hpp>
#include <chrono>
#include <mutex>
#include <thread>
#include <vector>

#include "usb-daq-v20.h"

/* unused, build only use g++
g++ server.cpp usb-daq-v20.cpp -Ilibusb/include
-Llibusb/lib -lusb-1.0 -o server.exe
*/

struct DataPack {
  double data[32];
  double stamp;  // seconds
  double _[7];
};

std::array<char, sizeof(DataPack)> serialize(DataPack data) {
  std::array<char, sizeof(DataPack)> res;
  memcpy(res.data(), &data, sizeof(DataPack));
  return res;
}

class Tactile {
 public:
  Tactile() {}
  bool init() {
    if (-1 == OpenUsbV20()) {
      printf("usb  device open fail.\n");
      return false;
    } else {
      printf("usb  device open ok.\n");
      printf("usb device id = %d.#\n", GetDeviceCountV20());
    }

    for (int Dout_chan = 0; Dout_chan < 8; Dout_chan++) {
      if (0 == DoSetV20(dev, Dout_chan, 0)) {
        printf("Dout_chan %d test set success.\n", Dout_chan);
      } else {
        printf("Dout_chan %d test set failed.\n", Dout_chan);
        return false;
      }
    }

    for (int AD_chan = 0; AD_chan < 12; AD_chan++) {
      float res;
      if (0 == ADSingleV20(dev, AD_chan, &res)) {
        printf("AD_chan %d test read success.\n", AD_chan);

      } else {
        printf("AD_chan %d test read failed.\n", AD_chan);
        return false;
      }
    }

    _init = true;
    return true;
  }
  ~Tactile() { CloseUsbV20(); }

  DataPack read() {
    if (!_init) throw std::runtime_error("uninited");

    memset(raw_data, 0, sizeof raw_data);
    DataPack data;
    int res;

    for (int row = out_chan_s; row <= out_chan_t; row++) {
      res = DoSetV20(dev, row, ON);
      if (res != 0) {
        printf("DoSetV20 ON res=%d\n", res);
      }
      for (int col = ad_chan_s; col <= ad_chan_t; col++) {
        res = ADSingleV20(dev, col, &raw_data[row][col]);
        if (res != 0) {
          printf("ADSingleV20 res=%d\n", res);
        }
      }
      res = DoSetV20(dev, row, OFF);
      if (res != 0) {
        printf("DoSetV20 OFF res=%d\n", res);
      }
    }
    for (int i = 0; i < 32; i++) {
      data.data[i] = raw_data[data_x[i]][data_y[i]];
    }

    auto now = std::chrono::high_resolution_clock::now;
    data.stamp = now().time_since_epoch().count() * 1e-9;

    return data;
  }

 private:
  bool _init = false;

  const int ad_chan_s = 0;
  const int ad_chan_t = 7;
  const int out_chan_s = 0;
  const int out_chan_t = 5;
  const int dev = 0;

  const unsigned char ON = 1;   // 3.3V
  const unsigned char OFF = 0;  // 0.0V

  const int data_x[32] = {
      0, 0, 0, 0, 1, 1, 1, 2, 2, 3, 3, 4, 5, 5, 5, 5,
      0, 0, 0, 0, 1, 1, 1, 2, 2, 3, 3, 4, 5, 5, 5, 5,
  };
  const int data_y[32] = {
      0, 1, 2, 3, 1, 2, 3, 1, 2, 1, 2, 3, 0, 1, 2, 3,
      4, 5, 6, 7, 5, 6, 7, 5, 6, 5, 6, 7, 4, 5, 6, 7,
  };

  float raw_data[6][8];
};

using asio::ip::tcp;

const int BUF_SIZE = 1024;
char _sendbuf[BUF_SIZE];

int main() {
  std::string addr = "127.0.0.1";
  int port = 6543;

  while (true) {
    Tactile tac;
    if (!tac.init()) {
      Reset_Usb_DeviceV20(0);
      printf("tac_init failed. sleep for 1 second.");
      std::this_thread::sleep_for(std::chrono::seconds(1));
      continue;
    }

    int send_cnt = 0;

    asio::io_context io;
    tcp::acceptor acceptor(io,
                           tcp::endpoint(asio::ip::make_address(addr), port));
    printf("listening...\n");
    tcp::socket socket(io);
    acceptor.accept(socket);
    printf("client connected.\n");

    auto t1 = std::chrono::high_resolution_clock::now();
    while (true) {
      auto tac_data = tac.read();
      auto raw = serialize(tac_data);

      // for (int i = 0; i <= 16; i++) {
      //   printf("%.2f ", tac_data.data[i]);
      // }
      // printf("%.2f\n", tac_data.stamp * 1e3);

      const size_t SendSize = sizeof(raw);
      memset(_sendbuf, 0, BUF_SIZE);
      memcpy(_sendbuf, raw.data(), SendSize);
      try {
        asio::write(socket, asio::buffer(_sendbuf, SendSize));
      } catch (std::exception& e) {
        printf("ERROR: %s\n", e.what());
        break;
      }

      send_cnt++;
      auto t2 = std::chrono::high_resolution_clock::now();
      double dur = (t2 - t1).count() * 1e-6;
      if (dur >= 1000.0) {
        t1 = t2;
        printf("sent %d msgs.\n", send_cnt);
      }

      // std::this_thread::sleep_for(std::chrono::milliseconds(33));
    }
  }

  return 0;
}