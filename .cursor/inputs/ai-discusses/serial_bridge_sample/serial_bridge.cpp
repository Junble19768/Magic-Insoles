/*
 * @Author: Zheng Junzhe zjz0@outlook.com
 * @Date: 2024-01-25 00:00:00
 * @FilePath: /Sentry_AutoSystem/src/drivers/src/serial_bridge.cpp
 * @Description: Serial Bridge for ROS2
 *
 * Copyright (c) 2023 by Zheng Junzhe, All Rights Reserved.
 */

#include "drivers/serial_bridge.hpp"

namespace drivers {
SerialBridge::SerialBridge(const rclcpp::NodeOptions &options)
    : Node("serial_bridge", options),
      serial_(std::make_shared<serial::Serial>()) {
  RCLCPP_INFO(this->get_logger(), "Serial Bridge start...");

  declareParams();

  // Init Serial
  serial_->setPort(port_address_);
  serial_->setBaudrate(baud_rate_);
  serial_->setBytesize(byte_size_);
  serial_->setStopbits(stop_bits_);
  serial_->setFlowcontrol(flow_control_);
  serial_->setParity(parity_);
  serial_->setTimeout(timeout_);

  RCLCPP_INFO(this->get_logger(), "Serial is initialized.");

  // Open Serial
  using std::chrono::operator""ms;
  int error_num = 0;
  if (!openSerial()) {
    RCLCPP_ERROR(this->get_logger(), "Failed to open the port: %s",
                 serial_->getPort().c_str());
    rclcpp::shutdown();
    return;
  }

  serial_->flush();

  auto send_callback_group =
      create_callback_group(rclcpp::CallbackGroupType::Reentrant);
  rclcpp::SubscriptionOptions send_options;
  send_options.callback_group = send_callback_group;
  sub_send_ = this->create_subscription<drivers_interfaces::msg::SerialData>(
      "/driver/serial/send", rclcpp::SensorDataQoS(),
      std::bind(&SerialBridge::sendDataCallback, this, std::placeholders::_1),
      send_options);

  if (serial_->isOpen()) {
    receive_thread_ = std::thread(&SerialBridge::receiveData, this);
  }
}

SerialBridge::~SerialBridge() {
  if (receive_thread_.joinable()) receive_thread_.join();

  if (serial_->isOpen()) {
    serial_->flush();
    serial_->close();
  }
}

bool SerialBridge::openSerial() {
  if (serial_->isOpen()) serial_->close();

  try {
    serial_->open();
    if (!serial_->isOpen()) {
      RCLCPP_ERROR(this->get_logger(), "Unable to open port %s",
                   serial_->getPort().c_str());
      return false;
    } else {
      RCLCPP_INFO(this->get_logger(), "Serial port %s is opened.",
                  serial_->getPort().c_str());
    }
  } catch (const serial::IOException &e) {
    RCLCPP_ERROR(this->get_logger(), "The Fail to open port %s",
                 serial_->getPort().c_str());
    return false;
  }
  return true;
}

void SerialBridge::sendDataCallback(
    const drivers_interfaces::msg::SerialData::ConstSharedPtr &send_msg) {
  //  auto send_func = std::bind((size_t (serial::Serial::*)(const
  //  std::vector<uint8_t> &data))&serial::Serial::write, &(*serial_),
  //  std::placeholders::_1);
  const auto send_func = [this](const std::vector<uint8_t> &data) {
    return this->serial_->write(data);
  };

  //  RCLCPP_INFO(this->get_logger(), "size: %ld", send_msg->data.size());
  std::vector<uint8_t> data{};
  data.reserve(send_msg->data.size());
  for (const uint8_t byte : send_msg->data) {
    data.emplace_back(byte);
  }
  sendCrc16Data(send_msg->cmd, data, send_func);
  //  try
  //  {
  //  }
  //  catch (const serial::SerialException & e)
  //  {
  //    RCLCPP_ERROR(this->get_logger(), "Send failed: %s", e.what());
  //  }
}

void SerialBridge::receiveData() {
  pub_receive_ = this->create_publisher<drivers_interfaces::msg::SerialData>(
      "/driver/serial/receive", rclcpp::SensorDataQoS());

  auto pub_func = [this](uint8_t cmd, const std::vector<uint8_t> &data) {
    drivers_interfaces::msg::SerialData data_msg;
    data_msg.header.frame_id = "serial";
    const auto transmit_cost = this->get_parameter("transmit_cost").as_double();
    transmit_cost_ = rclcpp::Duration::from_seconds(transmit_cost * 1e-3);
    data_msg.header.stamp = this->now() - transmit_cost_;
    data_msg.cmd = cmd;
    data_msg.data = data;
    //      RCLCPP_INFO(this->get_logger(), "Push.");
    this->pub_receive_->publish(data_msg);
  };

  ReceiveCrc16Data receiveCrc16Data;

  while (rclcpp::ok()) {
    try {
      receiveCrc16Data((uint8_t)serial_->read()[0], pub_func);
    } catch (const serial::SerialException &e) {
      RCLCPP_ERROR(this->get_logger(), "Receive Serial data failed: %s",
                   e.what());
      rclcpp::shutdown();
      throw;
    }
  }
}

void SerialBridge::declareParams() {
  const std::unordered_map<size_t, serial::bytesize_t> byte_size_map = {
      {5, serial::fivebits},
      {6, serial::sixbits},
      {7, serial::sevenbits},
      {8, serial::eightbits}};

  const std::unordered_map<std::string, serial::stopbits_t> stop_bits_map = {
      {"1", serial::stopbits_one},
      {"1.5", serial::stopbits_one_point_five},
      {"2", serial::stopbits_two}};

  const std::unordered_map<std::string, serial::flowcontrol_t>
      flow_control_map = {{"none", serial::flowcontrol_none},
                          {"hardware", serial::flowcontrol_hardware},
                          {"software", serial::flowcontrol_software}};

  const std::unordered_map<std::string, serial::parity_t> parity_map = {
      {"none", serial::parity_none},
      {"odd", serial::parity_odd},
      {"even", serial::parity_even},
      {"mark", serial::parity_mark},
      {"space", serial::parity_space}};

  try {
    port_address_ = this->declare_parameter<std::string>("port", "");

    baud_rate_ = this->declare_parameter<int>("baud_rate", 0);

    const auto byte_size = this->declare_parameter<int>("byte_size", 8);
    byte_size_ = byte_size_map.at(byte_size);

    const auto stop_bits =
        this->declare_parameter<std::string>("stop_bits", "1");
    stop_bits_ = stop_bits_map.at(stop_bits);

    const auto flow_control =
        this->declare_parameter<std::string>("flow_control", "none");
    flow_control_ = flow_control_map.at(flow_control);

    const auto parity = this->declare_parameter<std::string>("parity", "none");
    parity_ = parity_map.at(parity);

    const auto time_out = this->declare_parameter<int>("time_out", 1000);
    timeout_ = serial::Timeout::simpleTimeout(time_out);

    const auto transmit_cost =
        this->declare_parameter<double>("transmit_cost", 0.0);
    transmit_cost_ = rclcpp::Duration::from_seconds(transmit_cost);
  } catch (const std::exception &e) {
    RCLCPP_ERROR(this->get_logger(), "The Serial params was invalid: %s",
                 e.what());
  }
}

}  // namespace drivers

#include "rclcpp_components/register_node_macro.hpp"

// Register the component with class_loader.
// This acts as a sort of entry point, allowing the component to be discoverable
// when its library is being loaded into a running process.
RCLCPP_COMPONENTS_REGISTER_NODE(drivers::SerialBridge)