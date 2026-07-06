//
// Created by ZJZ0 on 2024/1/25.
//

#ifndef BUILD_CRC16_HPP
#define BUILD_CRC16_HPP

#include <functional>
#include <vector>

#include "serial/v8stdint.h"

namespace drivers {
enum KeyFrame : uint8_t { SOF_1 = 0xA5, SOF_2 = 0x5A, EOF_1 = 0xFF };

using SendFunc = std::function<size_t(const std::vector<uint8_t>& data)>;
using AnalysisFunc =
    std::function<void(uint8_t cmd, const std::vector<uint8_t>& data)>;

uint16_t CRC16_Check(const std::vector<uint8_t>& data) {
  uint16_t CRC16 = 0xFFFF;

  for (const uint8_t byte : data) {
    CRC16 ^= byte;
    uint8_t state;
    for (uint8_t j = 0; j < 8; ++j) {
      state = CRC16 & 0x01;
      CRC16 >>= 1;

      if (state) CRC16 ^= 0xA001;
    }
  }
  return CRC16;
}

void sendCrc16Data(uint8_t cmd, const std::vector<uint8_t>& data,
                   const SendFunc& send_func) {
  const uint8_t data_length = data.size();
  std::vector<uint8_t> packet;
  packet.reserve(data.size());

  packet.push_back(SOF_1);
  packet.push_back(SOF_2);
  packet.push_back(data_length);
  packet.push_back(cmd);
  for (const auto& byte : data) {
    packet.push_back(byte);
  }
  const uint16_t crc16 = CRC16_Check(packet);
  packet.push_back(crc16 >> 8);
  packet.push_back(crc16 & EOF_1);
  packet.push_back(EOF_1);

  send_func(packet);
}

class ReceiveCrc16Data {
 private:
  enum class Status {
    SOF_1,
    SOF_2,
    DATA_LENGTH,
    CMD,
    DATA,
    CRC16_HIGH_8,
    CRC16_LOW_8,
    EOF_1
  };
  Status status = Status::SOF_1;
  std::vector<uint8_t> buffer_;

  uint8_t length{};
  uint8_t cmd{};
  std::vector<uint8_t>::iterator data_itr{};
  uint16_t crc16{};

 public:
  ReceiveCrc16Data() { buffer_.reserve(300); }
  void operator()(uint8_t byte_data, const AnalysisFunc& analysis_func) {
    if (buffer_.size() > 200) {
      buffer_.clear();
      status = Status::SOF_1;
    }
    //进行数据解析 状态机
    switch (status) {
      case Status::SOF_1:  //接收帧头1状态
        if (SOF_1 == byte_data) {
          buffer_.clear();
          buffer_.emplace_back(byte_data);
          status = Status::SOF_2;
        }
        break;
      case Status::SOF_2:  //接收帧头2状态
        if (SOF_2 == byte_data) {
          buffer_.emplace_back(byte_data);
          status = Status::DATA_LENGTH;
        } else if (SOF_1 == byte_data) {
          status = Status::SOF_2;
        } else {
          status = Status::SOF_1;
        }
        break;
      case Status::DATA_LENGTH:  //接收数据长度字节状态
        buffer_.emplace_back(byte_data);
        length = byte_data;
        status = Status::CMD;
        break;
      case Status::CMD:  //接收命令字节状态
        buffer_.emplace_back(byte_data);
        cmd = byte_data;
        data_itr = buffer_.end();  //记录数据指针首地址

        if (0 == length)
          status = Status::CRC16_HIGH_8;  //数据字节长度为0则跳过数据接收状态
        status = Status::DATA;
        break;
      case Status::DATA:  //接收len字节数据状态
        buffer_.emplace_back(byte_data);

        if (data_itr + length ==
            buffer_.end())  //利用指针地址偏移判断是否接收完len位数据
          status = Status::CRC16_HIGH_8;

        break;
      case Status::CRC16_HIGH_8:  //接收crc16校验高8位字节
        crc16 = byte_data;
        status = Status::CRC16_LOW_8;
        break;
      case Status::CRC16_LOW_8:  //接收crc16校验低8位字节
        crc16 <<= 8;
        crc16 += byte_data;
        if (crc16 == CRC16_Check(buffer_))  //校验正确进入下一状态
        {
          status = Status::EOF_1;
        } else if (byte_data == SOF_1) {
          status = Status::SOF_2;
        } else {
          status = Status::SOF_1;
        }
        break;
      case Status::EOF_1:        //接收帧尾
        if (byte_data == EOF_1)  //帧尾接收正确
        {
          std::vector<uint8_t> data(data_itr, data_itr + length);
          analysis_func(cmd, data);  //数据解析
          status = Status::SOF_1;
          data_itr = buffer_.begin();
          buffer_.clear();
        } else if (byte_data == SOF_1) {
          status = Status::SOF_2;
        } else {
          status = Status::SOF_1;
        }
        break;
      default:
        status = Status::SOF_1;
        break;  //多余状态，正常情况下不可能出现
    }
  }

 private:
};
}  // namespace drivers

#endif  // BUILD_CRC16_HPP