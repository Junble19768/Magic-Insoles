/*
 * @Author: Zheng Junzhe zjz0@outlook.com
 * @Date: 2024-01-25 00:00:00
 * @FilePath: /Sentry_AutoSystem/src/drivers/include/drivers/serial_bridge.hpp
 * @Description: Serial Bridge for ROS2
 *
 * Copyright (c) 2023 by Zheng Junzhe, All Rights Reserved.
 */

#ifndef DRIVER_INCLUDE_DRIVER_SERIAL_BRIDGE_HPP_
#define DRIVER_INCLUDE_DRIVER_SERIAL_BRIDGE_HPP_

// C++
#include <memory>
#include <string>
#include <thread>
#include <unordered_map>

// Serial
#include "serial/serial.h"

// ROS2
#include <rclcpp/rclcpp.hpp>

#include "drivers_interfaces/msg/serial_data.hpp"
#include "std_msgs/msg/u_int8_multi_array.hpp"

// Verify
#include "verify/crc16.hpp"

namespace drivers {
class SerialBridge : public rclcpp::Node {
 public:
  explicit SerialBridge(const rclcpp::NodeOptions& options);
  ~SerialBridge() override;

 private:
  void declareParams();
  bool openSerial();

  void sendDataCallback(
      const drivers_interfaces::msg::SerialData::ConstSharedPtr& send_msg);
  void receiveData();

  std::shared_ptr<serial::Serial> serial_;

  std::string port_address_;
  size_t baud_rate_;
  serial::bytesize_t byte_size_;
  serial::stopbits_t stop_bits_;
  serial::flowcontrol_t flow_control_;
  serial::parity_t parity_;
  serial::Timeout timeout_;
  rclcpp::Duration transmit_cost_ = rclcpp::Duration::from_seconds(0.0);

  rclcpp::Subscription<drivers_interfaces::msg::SerialData>::SharedPtr
      sub_send_;
  rclcpp::Publisher<drivers_interfaces::msg::SerialData>::SharedPtr
      pub_receive_;

  std::thread receive_thread_;
};
}  // namespace drivers

#endif  // DRIVER_INCLUDE_DRIVER_SERIAL_BRIDGE_HPP_