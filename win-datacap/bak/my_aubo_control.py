#! /usr/bin/env python

import subprocess
from robotcontrol import *
import libpyauboi5
import numpy as np
import serial
import struct
import time
import os
from typing import Tuple, Optional, Callable
import json
import sys
from glob import glob

# 动态将工作空间中编译好的 ROS2 python 包路径添加到 sys.path 中
# 解决在 Jupyter 等未自动 source setup.zsh 的环境中 ModuleNotFoundError 的问题
install_dir = os.path.expanduser("~/workspace2025/install")
site_packages_dirs = glob(
    os.path.join(install_dir, "*", "lib", "python*", "site-packages")
)
for path in site_packages_dirs:
    if path not in sys.path:
        sys.path.insert(0, path)

import rclpy
from rclpy.node import Node
from nglove_interfaces.srv import TriggerCalibration
from nglove_interfaces.msg import FourChipsData
import gc
import threading

# 定义每个部分的中文名称和标识符
CALIBRATION_PARTS = {
    "index_finger": "食指",
    "middle_finger": "中指",
    "ring_finger": "无名指",
    "pinky_finger": "小指",
    "thumb_finger": "大拇指",
    "palm_main": "主手掌",
    "palm_secondary": "副手掌",
}

SENSOR_MAPPING = {
    "index_distal": {"start": 29, "rows": 2, "cols": 2, "part": "index_finger"},
    "index_middle": {"start": 33, "rows": 2, "cols": 2, "part": "index_finger"},
    "index_proximal": {"start": 37, "rows": 2, "cols": 2, "part": "index_finger"},
    "middle_distal": {"start": 41, "rows": 2, "cols": 2, "part": "middle_finger"},
    "middle_middle": {"start": 45, "rows": 2, "cols": 2, "part": "middle_finger"},
    "middle_proximal": {"start": 49, "rows": 2, "cols": 2, "part": "middle_finger"},
    "ring_distal": {"start": 53, "rows": 2, "cols": 2, "part": "ring_finger"},
    "ring_middle": {"start": 57, "rows": 2, "cols": 2, "part": "ring_finger"},
    "ring_proximal": {"start": 61, "rows": 2, "cols": 2, "part": "ring_finger"},
    "pinky_distal": {"start": 65, "rows": 2, "cols": 2, "part": "pinky_finger"},
    "pinky_middle": {"start": 69, "rows": 2, "cols": 2, "part": "pinky_finger"},
    "pinky_proximal": {"start": 73, "rows": 2, "cols": 2, "part": "pinky_finger"},
    "thumb_distal": {"start": 77, "rows": 2, "cols": 6, "part": "thumb_finger"},
    "thumb_middle": {"start": 89, "rows": 2, "cols": 6, "part": "thumb_finger"},
    "thumb_proximal": {"start": 101, "rows": 2, "cols": 6, "part": "thumb_finger"},
    "palm_main": {"start": 4, "rows": 5, "cols": 5, "part": "palm_main"},
    "palm_secondary": {"start": 0, "rows": 2, "cols": 2, "part": "palm_secondary"},
}

# Per-part region plan: (region_name, waypoint_attr, x_spacing, y_spacing)
PART_REGION_PLAN = {
    "index_finger": [
        ("index_distal", "_first_point_of_first_region_on_waypoint", 0.0035, 0.0035),
        ("index_middle", "_index_finger_sencond_point_on_waypoint", 0.0035, 0.0035),
        ("index_proximal", "_index_finger_third_point_on_waypoint", 0.0035, 0.0035),
    ],
    "middle_finger": [
        ("middle_distal", "_middle_finger_first_point_on_waypoint", 0.0035, 0.0035),
        ("middle_middle", "_middle_finger_second_point_on_waypoint", 0.0035, 0.0035),
        ("middle_proximal", "_middle_finger_third_point_on_waypoint", 0.0035, 0.0035),
    ],
    "ring_finger": [
        ("ring_distal", "_ring_finger_first_point_on_waypoint", 0.0035, 0.0035),
        ("ring_middle", "_ring_finger_second_point_on_waypoint", 0.0035, 0.0035),
        ("ring_proximal", "_ring_finger_third_point_on_waypoint", 0.0035, 0.0035),
    ],
    "pinky_finger": [
        ("pinky_distal", "_pinky_finger_first_point_on_waypoint", 0.0035, 0.0035),
        ("pinky_middle", "_pinky_finger_second_point_on_waypoint", 0.0035, 0.0035),
        ("pinky_proximal", "_pinky_finger_third_point_on_waypoint", 0.0035, 0.0035),
    ],
    "thumb_finger": [
        ("thumb_distal", "_thumb_finger_first_point_on_waypoint", 0.0035, 0.0035),
        ("thumb_middle", "_thumb_finger_second_point_on_waypoint", 0.0035, 0.0035),
        ("thumb_proximal", "_thumb_finger_third_point_on_waypoint", 0.0035, 0.0035),
    ],
    "palm_main": [
        ("palm_main", "_palm_main_first_point_on_waypoint", 0.0039, 0.0039),
    ],
    "palm_secondary": [
        ("palm_secondary", "_palm_secondary_first_point_on_waypoint", 0.0035, 0.0035),
    ],
}

FINGER_REGION_LABELS = ("远节 distal", "中节 middle", "近节 proximal")

CALIBRATION_WAYPOINTS_JSON = os.path.join(
    os.path.dirname(os.path.abspath(__file__)), "calibration_waypoints.json"
)

MENU_PART_BY_CHOICE = {
    "1": "index_finger",
    "2": "middle_finger",
    "3": "ring_finger",
    "4": "pinky_finger",
    "5": "thumb_finger",
    "6": "palm_main",
    "7": "palm_secondary",
}


class MyAuboi10(Auboi5Robot):
    _l20_initial_waypoint = {
        "joint": [
            -1.0601848363876343,
            -0.7283787131309509,
            1.0115262269973755,
            0.18252842128276825,
            -1.4968122243881226,
            1.7903791666030884,
        ],
        "ori": [
            0.9124222959550947,
            0.025662570450757805,
            -0.02746123148216334,
            -0.4075203885542128,
        ],
        "pos": [0.3675520316237865, -1.0822706738148484, 0.6400702374707403],
    }
    _hil_serl_initial_waypoint = {
        "joint": [
            -1.3445706367492676,
            -0.9264265298843384,
            0.4955613911151886,
            -0.11877074837684631,
            1.5727146863937378,
            -1.3323304653167725,
        ],
        "ori": [
            0.013283199935367475,
            0.711330380687989,
            0.7026966782640119,
            -0.00707279764177724,
        ],
        "pos": [0.07684526739960558, -1.230520285309826, 0.5500004768876829],
    }
    _initial_waypoint = {  # 这个是完全竖直
        "joint": [
            -1.2505847215652466,
            -0.6142553091049194,
            0.4769490361213684,
            -2.0503764152526855,
            0.3202041685581207,
            -0.7853981852531433,
        ],
        "ori": [
            0.6532777290836816,
            -0.27059980761388086,
            -0.6532821870059223,
            0.2706036528640324,
        ],
        "pos": [2.462214636789195e-06, -0.9229812614789412, 0.8665109536996233],
    }
    _prepare_waypoint = {  # 这个是标定的预备姿势
        "joint": [
            -0.9986500144004822,
            -1.1699285507202148,
            0.519121527671814,
            1.689618468284607,
            -0.5721023082733154,
            2.3556222915649414,
        ],
        "ori": [
            0.6531877546338221,
            -0.2705944692294826,
            -0.6534007166989129,
            0.2705400041328223,
        ],
        "pos": [0.38212865247216404, -1.1111212530731245, 0.46729577014358113],
    }
    _left_max_waypoint = {
        "joint": [
            -0.8857590556144714,
            -1.2877309322357178,
            0.18294523656368256,
            1.4709525108337402,
            -0.6848317980766296,
            2.356227397918701,
        ],
        "ori": [
            0.6531631585750483,
            -0.2706352393958624,
            -0.6533329673836653,
            0.2707221623862099,
        ],
        "pos": [0.5211982947276006, -1.0711505942443407, 0.506412658423399],
    }
    _first_point_of_first_region_on_waypoint = {
        "joint": [
            -1.0155044794082642,
            -1.1444686651229858,
            0.5664162039756775,
            1.7140145301818848,
            -0.5551340579986572,
            2.3542320728302,
        ],
        "ori": [
            0.6526265146372073,
            -0.2709967677864525,
            -0.6537472797311027,
            0.2706545371612492,
        ],
        "pos": [0.35881582921991884, -1.1117150763673176, 0.44925004489905856],
    }
    _index_finger_sencond_point_on_waypoint = {
        "joint": [
            -0.9935917854309082,
            -1.0359758138656616,
            0.7795777320861816,
            1.8185789585113525,
            -0.577046811580658,
            2.3543570041656494,
        ],
        "ori": [
            0.6526261012708768,
            -0.2709972122063824,
            -0.6537474807778139,
            0.2706546033102085,
        ],
        "pos": [0.3588163498415954, -1.0642877704593867, 0.44979799574707613],
    }
    # TODO: 示教后填入食指第3区域起始点
    _index_finger_third_point_on_waypoint = {
        "joint": [
            -0.9699440002441406,
            -0.9494580626487732,
            0.9473153352737427,
            1.8997011184692383,
            -0.6006982922554016,
            2.354485273361206,
        ],
        "ori": [
            0.6526241396758751,
            -0.2710016246904649,
            -0.6537472901488274,
            0.2706553756172548,
        ],
        "pos": [0.3588140317879503, -1.0167471889234359, 0.4498772732649972],
    }
    _middle_finger_first_point_on_waypoint = {
        "joint": [
            -1.089613437652588,
            -1.0607056617736816,
            0.730905294418335,
            1.7922022342681885,
            -0.4811352491378784,
            2.3554904460906982,
        ],
        "ori": [
            0.6532099761753583,
            -0.27056071296381073,
            -0.653401651476733,
            0.2705178542591606,
        ],
        "pos": [0.2600398126536693, -1.1130266622628597, 0.4500518937726916],
    }
    # TODO: 示教后填入中指第2区域起始点
    _middle_finger_second_point_on_waypoint = {
        "joint": [
            -1.0695492029190063,
            -0.9665070176124573,
            0.9147200584411621,
            1.8818048238754272,
            -0.5012030005455017,
            2.3555195331573486,
        ],
        "ori": [
            0.653207585434244,
            -0.2705661958610811,
            -0.6534008968872753,
            0.270519965871897,
        ],
        "pos": [0.26003289295062976, -1.0650619584984593, 0.4498506293426135],
    }
    # TODO: 示教后填入中指第3区域起始点
    _middle_finger_third_point_on_waypoint = {
        "joint": [
            -1.0480766296386719,
            -0.8874536752700806,
            1.0668457746505737,
            1.954838752746582,
            -0.522675633430481,
            2.3555452823638916,
        ],
        "ori": [
            0.6532121760354817,
            -0.2705606286852234,
            -0.6533999971466521,
            0.2705166224341912,
        ],
        "pos": [0.2600500892165521, -1.0176978277022792, 0.44949320831109996],
    }
    _ring_finger_first_point_on_waypoint = {
        "joint": [
            -1.1816589832305908,
            -1.0077283382415771,
            0.8369088768959045,
            1.8392189741134644,
            -0.3880663514137268,
            2.3495442867279053,
        ],
        "ori": [
            0.6553758687323105,
            -0.2661573644434317,
            -0.6543203597483225,
            0.267409040338433,
        ],
        "pos": [0.14686682677477617, -1.1181014995011256, 0.4488549269804204],
    }
    # TODO: 示教后填入无名指第2区域起始点
    _ring_finger_second_point_on_waypoint = {
        "joint": [
            -1.1651087999343872,
            -0.9220799207687378,
            1.0044658184051514,
            1.921360731124878,
            -0.40461283922195435,
            2.349320650100708,
        ],
        "ori": [
            0.6553690391400309,
            -0.266165762527404,
            -0.6543204251766159,
            0.26741725933748356,
        ],
        "pos": [0.14686747894126534, -1.0709635797301558, 0.4476347178649019],
    }
    # TODO: 示教后填入无名指第3区域起始点
    _ring_finger_third_point_on_waypoint = {
        "joint": [
            -1.1469887495040894,
            -0.8437491655349731,
            1.1503334045410156,
            1.9890981912612915,
            -0.4227328896522522,
            2.349093198776245,
        ],
        "ori": [
            0.6553711821654111,
            -0.26616314012407366,
            -0.654320071261509,
            0.2674154834162338,
        ],
        "pos": [0.1466615392447095, -1.0230464805757378, 0.44926936578714527],
    }
    _pinky_finger_first_point_on_waypoint = {
        "joint": [
            -1.2639107704162598,
            -0.966855525970459,
            0.9131432175636292,
            1.8896433115005493,
            -0.28898191452026367,
            2.350520133972168,
        ],
        "ori": [
            0.6494423951322187,
            -0.2662702921038535,
            -0.6561054395932409,
            0.27721897316745114,
        ],
        "pos": [0.04750275558409059, -1.1145165929745873, 0.4501305410149532],
    }
    # TODO: 示教后填入小指第2区域起始点
    _pinky_finger_second_point_on_waypoint = {
        "joint": [
            -1.2507022619247437,
            -0.882945716381073,
            1.0733336210250854,
            1.9655202627182007,
            -0.30219048261642456,
            2.3509418964385986,
        ],
        "ori": [
            0.6494420132771785,
            -0.2662705010511715,
            -0.6561060177258974,
            0.27721829875444315,
        ],
        "pos": [0.04701755171515934, -1.0667842357162565, 0.45041112535482064],
    }
    # TODO: 示教后填入小指第3区域起始点
    _pinky_finger_third_point_on_waypoint = {
        "joint": [
            -1.2359200716018677,
            -0.8100326657295227,
            1.214323878288269,
            2.0331807136535645,
            -0.31697264313697815,
            2.3513784408569336,
        ],
        "ori": [
            0.6494421719879913,
            -0.2662703661098765,
            -0.6561061525359372,
            0.2772177374911684,
        ],
        "pos": [0.047017624760462645, -1.0193845517494373, 0.44840743262964133],
    }

    _palm_main_first_point_on_waypoint = {
        "joint": [
            -1.3753747940063477,
            -0.9515085220336914,
            0.9479644298553467,
            1.9149783849716187,
            -0.1775362193584442,
            2.344416379928589,
        ],
        "ori": [
            0.6494591362333199,
            -0.2662438288106035,
            -0.6561122904723906,
            0.27718895409884853,
        ],
        "pos": [-0.07909514356057029, -1.1135687577099675, 0.44714905042274367],
    }
    _palm_secondary_first_point_on_waypoint = {
        "joint": [
            -1.3898341655731201,
            -0.7850717306137085,
            1.263164758682251,
            2.0614206790924072,
            -0.16157296299934387,
            2.343367338180542,
        ],
        "ori": [
            0.6499096170634823,
            -0.2645885207026766,
            -0.6565465406985155,
            0.2766894364763129,
        ],
        "pos": [-0.11393643587227517, -1.0112438306117872, 0.44720511853215117],
    }
    _thumb_finger_first_point_on_waypoint = {
        "joint": [
            -1.5315337181091309,
            -0.9919338226318359,
            0.8681203126907349,
            1.9664517641067505,
            -0.019972411915659904,
            2.2500052452087402,
        ],
        "ori": [
            0.6499093342130192,
            -0.26458913263067996,
            -0.6565462858613307,
            0.27669012038420654,
        ],
        "pos": [-0.25170338980491175, -1.115134584829461, 0.447589478967865],
    }
    # TODO: 示教后填入大拇指第2区域起始点
    _thumb_finger_second_point_on_waypoint = {
        "joint": [
            -1.5300188064575195,
            -0.8953619599342346,
            1.054953932762146,
            2.049213409423828,
            -0.021483639255166054,
            2.257502555847168,
        ],
        "ori": [
            0.6499104773601747,
            -0.2645891136753103,
            -0.6565463637340094,
            0.2766872686077797,
        ],
        "pos": [-0.2522045946512589, -1.0617459175316721, 0.4470579037671372],
    }
    # TODO: 示教后填入大拇指第3区域起始点
    _thumb_finger_third_point_on_waypoint = {
        "joint": [
            -1.5283315181732178,
            -0.8099923133850098,
            1.2148197889328003,
            2.1165108680725098,
            -0.023156261071562767,
            2.2646992206573486,
        ],
        "ori": [
            0.6499103123348289,
            -0.2645854492078666,
            -0.6565475293625073,
            0.2766883945457496,
        ],
        "pos": [-0.2526957089252747, -1.0083587665416571, 0.447813048438051],
    }
    # Force sensor serial (port resolved per-instance in __init__)
    FORCE_SENSOR_BAUDRATE = 9600
    FORCE_SENSOR_COMMAND = bytes([0x01, 0x03, 0x00, 0x00, 0x00, 0x0D, 0x84, 0x0F])

    @staticmethod
    def _resolve_force_sensor_port() -> str:
        env_port = os.environ.get("FORCE_SENSOR_PORT", "").strip()
        if env_port:
            return env_port
        result = subprocess.check_output("ls /dev/ttyUSB*", shell=True)
        return str(result.strip().split()[0].decode().strip())

    def __init__(self, ip="192.168.1.100", port=8899):
        super().__init__()
        self.ip = ip
        self.port = port
        self.ros_initialized = False
        self.trigger_calibration_service = None
        self.node = None
        self.force_log_file = None
        self.log_filename = "force_log.txt"
        self.force_serial = None
        self.calibration_files = {}  # 存储不同部分的标定文件句柄
        self.force_sensor_port = self._resolve_force_sensor_port()
        self.force_serial = serial.Serial(
            self.force_sensor_port, self.FORCE_SENSOR_BAUDRATE, timeout=0.1
        )
        logger.info(f"串口 {self.force_sensor_port} 连接成功并常开。")
        self.force_log_file = open(self.log_filename, "w")
        self.force_log_file.write("Timestamp(s),Force(N),TargetForce(N)\n")
        self.calibration_pose_confirm = True
        logger.info(f"力值日志文件已打开: {self.log_filename}")

    def get_current_waypoint(self):
        self.check_event()
        if self.rshd >= 0 and self.connected:
            return libpyauboi5.get_current_waypoint(self.rshd)
        else:
            logger.warn("RSHD uninitialized or not login!!!")
            return None

    def _initialize_ros(self):
        if self.ros_initialized:
            return
        if not rclpy.ok():
            rclpy.init()
        self.node = Node("robot_calibration_client_node")
        service_name = "trigger_calibration_read"
        self.node.get_logger().info(f"正在等待ROS服务 '{service_name}'...")
        self.trigger_calibration_service = self.node.create_client(
            TriggerCalibration, service_name
        )
        if not self.trigger_calibration_service.wait_for_service(timeout_sec=10.0):
            raise RuntimeError(f"服务 '{service_name}' 不可用。")
        self.ros_initialized = True
        self.node.get_logger().info("成功连接到标定服务！")

    def _destroy_sdk_context_if_any(self):
        """End session if logged in, then destroy SDK context (libpyauboi5.destory_context). Resets rshd."""
        if self.rshd < 0:
            return
        if self.connected:
            try:
                self.move_stop()
            except Exception:
                pass
            try:
                self.robot_shutdown()
            except Exception:
                pass
            try:
                self.disconnect()
            except Exception:
                pass
        try:
            libpyauboi5.destory_context(self.rshd)
        except Exception:
            pass
        self.rshd = -1
        self.connected = False

    def set_and_startup(self):
        try:
            logger_init()
            logger.info("{0} test beginning...".format(Auboi5Robot.get_local_time()))
            # Drop any stale context from a previous session on this object before reconnecting.
            self._destroy_sdk_context_if_any()
            ini = Auboi5Robot.initialize()
            if ini != RobotErrorType.RobotError_SUCC:
                logger.error("Auboi5Robot.initialize() failed: {0}".format(ini))
                return False
            self.rshd = self.create_context()
            result = self.connect(self.ip, self.port)
            if result != RobotErrorType.RobotError_SUCC:
                logger.warning(
                    "connect failed once; uninitializing SDK and retrying login once (close other clients e.g. notebook)."
                )
                self._destroy_sdk_context_if_any()
                try:
                    Auboi5Robot.uninitialize()
                except Exception:
                    pass
                ini = Auboi5Robot.initialize()
                if ini != RobotErrorType.RobotError_SUCC:
                    logger.error(
                        "Auboi5Robot.initialize() failed after reset: {0}".format(ini)
                    )
                    return False
                self.rshd = self.create_context()
                result = self.connect(self.ip, self.port)
            if result != RobotErrorType.RobotError_SUCC:
                self._destroy_sdk_context_if_any()
                return False
            self.robot_startup()
            self.set_collision_class(6)
            self.set_tool_dynamics_param(
                {
                    "position": (0.0, 0.0, 0.1),
                    "payload": 1,
                    "inertia": (0.0, 0.0, 0.0, 0.0, 0.0, 0.0),
                }
            )
            self.init_profile()
            self.set_joint_maxacc((0.5, 0.5, 0.5, 0.5, 0.5, 0.5))
            self.set_joint_maxvelc((0.1, 0.1, 0.1, 0.1, 0.1, 0.1))
            # self._initialize_ros()
            return True
        except RobotError as e:
            logger.error("{0} robot Event:{1}".format(self.get_local_time(), e))
            self._destroy_sdk_context_if_any()
            return False

    def move_cartesian_step(self, pos, ori, issync=False):
        """
        IK + move_joint to target pose. Same math as move_to_target_in_cartesian but no per-call
        logging spam, and optional issync=False so the API returns before the segment finishes
        (better for keyboard teleop; use issync=True for safe point-to-point moves).
        """
        self.check_event()
        if self.rshd < 0 or not self.connected:
            return RobotErrorType.RobotError_NotLogin
        pos = tuple(pos)
        ori = tuple(ori)
        joint_radian = libpyauboi5.get_current_waypoint(self.rshd)
        ik_result = libpyauboi5.inverse_kin(self.rshd, joint_radian["joint"], pos, ori)
        return libpyauboi5.move_joint(self.rshd, ik_result["joint"], issync)

    def _ori_to_quaternion(self, orientation) -> tuple:
        if len(orientation) == 3:
            rpy_xyz = [i / 180.0 * pi for i in orientation]
            return tuple(libpyauboi5.rpy_to_quaternion(self.rshd, rpy_xyz))
        if len(orientation) == 4:
            return tuple(orientation)
        raise ValueError("orientation must be Euler(3) or quaternion(4)")

    def move_to_pose_via_canbus(
        self,
        pos,
        orientation,
        v_max: float = 0.05,
        pos_tol: float = 0.0003,
        settle_time: float = 0.3,
        timeout: float = 120.0,
        can_hz: float = 100.0,
        ik_max_joint_step: float = 0.015,
    ) -> int:
        """
        Stream Cartesian target at can_hz via tcp2canbus (IK + joint step guard).
        """
        self.check_event()
        if self.rshd < 0 or not self.connected:
            return RobotErrorType.RobotError_NotLogin

        cmd_ori = self._ori_to_quaternion(orientation)
        target_pos = np.array(pos, dtype=float)
        wp = self.get_current_waypoint()
        if not wp:
            logger.error("move_to_pose_via_canbus: cannot read current waypoint")
            return RobotErrorType.RobotError_Move

        current_pos = np.array(wp["pos"], dtype=float)
        cmd_joint = np.array(wp["joint"], dtype=float)
        can_dt = 1.0 / can_hz
        max_step = v_max * can_dt

        self.enter_tcp2canbus_mode()
        start_t = time.time()
        settle_start = None
        ik_fail_streak = 0
        try:
            while True:
                loop_t0 = time.time()
                if loop_t0 - start_t > timeout:
                    logger.error("move_to_pose_via_canbus: timeout")
                    return RobotErrorType.RobotError_Move

                delta = target_pos - current_pos
                dist = float(np.linalg.norm(delta))

                if dist <= pos_tol:
                    if settle_start is None:
                        settle_start = loop_t0
                    elif loop_t0 - settle_start >= settle_time:
                        return RobotErrorType.RobotError_SUCC
                else:
                    settle_start = None
                    step = delta if dist <= max_step else delta * (max_step / dist)
                    current_pos = current_pos + step

                    new_joint = self._try_apply_ik_guarded(
                        cmd_joint, current_pos, cmd_ori, ik_max_joint_step
                    )
                    if new_joint is None:
                        current_pos = current_pos - step
                        ik_fail_streak += 1
                        if ik_fail_streak > 50:
                            logger.error(
                                "move_to_pose_via_canbus: repeated IK rejection"
                            )
                            return RobotErrorType.RobotError_Move
                    else:
                        cmd_joint = new_joint
                        ik_fail_streak = 0

                self.set_waypoint_to_canbus(cmd_joint.tolist())
                elapsed = time.time() - loop_t0
                time.sleep(max(0.0, can_dt - elapsed))
        finally:
            if self.connected:
                self.leave_tcp2canbus_mode()

    def move_to_target_in_cartesian(self, pos, orientation):
        """Point-to-point via SDK move_joint (planned); CAN reserved for force control / teleop."""
        result = self.move_cartesian_step(pos, orientation, issync=True)
        if result != RobotErrorType.RobotError_SUCC:
            self.raise_error(RobotErrorType.RobotError_Move, result, "move error")
        return result

    def _waypoint_attr_for_region(self, region_name: str) -> Optional[str]:
        for plan in PART_REGION_PLAN.values():
            for region, wp_attr, _, _ in plan:
                if region == region_name:
                    return wp_attr
        return None

    def _capture_current_waypoint_dict(self) -> dict:
        wp = self.get_current_waypoint()
        if not wp:
            self.raise_error(
                RobotErrorType.RobotError_Move, -1, "cannot read current waypoint"
            )
        return {
            "joint": list(wp["joint"]),
            "ori": list(wp["ori"]),
            "pos": list(wp["pos"]),
        }

    def _persist_calibration_waypoints(self) -> None:
        payload = {}
        for plan in PART_REGION_PLAN.values():
            for region_name, wp_attr, _, _ in plan:
                payload[region_name] = getattr(self.__class__, wp_attr)
        with open(CALIBRATION_WAYPOINTS_JSON, "w", encoding="utf-8") as f:
            json.dump(payload, f, indent=2, ensure_ascii=False)
        logger.info(f"💾 路点已写入 {CALIBRATION_WAYPOINTS_JSON}")

    def _update_region_waypoint_from_teleop(
        self,
        start_waypoint: dict,
        region_name: str,
        row: int,
        col: int,
        x_spacing: float,
        y_spacing: float,
        point_label: str,
    ) -> None:
        """After teleop at grid (row,col), back-solve region origin and persist."""
        current = self._capture_current_waypoint_dict()
        cur_pos = current["pos"]
        new_origin_pos = [
            cur_pos[0] + col * x_spacing,
            cur_pos[1] - row * y_spacing,
            cur_pos[2],
        ]
        start_waypoint["pos"] = new_origin_pos
        start_waypoint["ori"] = current["ori"]
        start_waypoint["joint"] = current["joint"]

        wp_attr = self._waypoint_attr_for_region(region_name)
        if wp_attr is not None:
            class_wp = getattr(self.__class__, wp_attr)
            class_wp["pos"] = list(new_origin_pos)
            class_wp["ori"] = list(current["ori"])
            class_wp["joint"] = list(current["joint"])

        self._persist_calibration_waypoints()
        logger.info(
            f"✏️ [{point_label}] 遥操后更新 region '{region_name}' 路点原点: "
            f"x={new_origin_pos[0]:.6f}, y={new_origin_pos[1]:.6f}, z={new_origin_pos[2]:.6f}"
        )

    def _print_current_pose(self, context: str) -> None:
        wp = self.get_current_waypoint()
        if not wp:
            logger.warning("无法读取当前位姿")
            return
        pos = wp["pos"]
        logger.info(
            f"📍 [{context}] 当前 TCP: "
            f"x={pos[0]:.6f}, y={pos[1]:.6f}, z={pos[2]:.6f}"
        )

    def _run_keyboard_teleop_session(self) -> None:
        """Block until ESC; W/S A/D R/F + U/O I/K J/L via CAN bus."""
        from pynput import keyboard

        loop_hz = 100.0
        dt = 1.0 / loop_hz
        alpha = 0.08
        max_lin_vel = 0.02
        max_ang_vel = 0.1
        ik_max_joint_step = 0.025
        active_keys: set = set()
        v_filtered = np.zeros(6)
        running = {"on": True}

        key_map = {
            "w": (0, 1),
            "s": (0, -1),
            "a": (1, 1),
            "d": (1, -1),
            "r": (2, 1),
            "f": (2, -1),
            "o": (3, 1),
            "u": (3, -1),
            "i": (4, 1),
            "k": (4, -1),
            "j": (5, 1),
            "l": (5, -1),
        }

        def on_press(key):
            char = getattr(key, "char", None)
            if char is None:
                return
            char = char.lower()
            if char in ("=", "+"):
                nonlocal max_lin_vel, max_ang_vel
                max_lin_vel = min(0.1, max_lin_vel + 0.005)
                max_ang_vel = min(0.5, max_ang_vel + 0.02)
                print(f"\r[+] 平移限速={max_lin_vel:.3f}m/s", end="", flush=True)
            elif char in ("-", "_"):
                max_lin_vel = max(0.002, max_lin_vel - 0.005)
                max_ang_vel = max(0.01, max_ang_vel - 0.02)
                print(f"\r[-] 平移限速={max_lin_vel:.3f}m/s", end="", flush=True)
            elif char in key_map:
                active_keys.add(char)

        def on_release(key):
            if key == keyboard.Key.esc:
                running["on"] = False
                return False
            char = getattr(key, "char", None)
            if char is not None and char.lower() in active_keys:
                active_keys.remove(char.lower())

        current_wp = self.get_current_waypoint()
        if not current_wp:
            logger.error("遥操启动失败：无法读取当前位姿")
            return

        cmd_pos = np.array(current_wp["pos"], dtype=float)
        cmd_rpy = np.array(self.quaternion_to_rpy(current_wp["ori"]), dtype=float)
        cmd_joint = np.array(current_wp["joint"], dtype=float)
        cmd_ori = tuple(current_wp["ori"])

        def control_loop():
            nonlocal cmd_joint, cmd_pos, cmd_rpy, cmd_ori
            self.enter_tcp2canbus_mode()
            try:
                while running["on"]:
                    t0 = time.time()
                    v_target = np.zeros(6)
                    for k in active_keys:
                        axis, sign = key_map[k]
                        vel_mag = max_lin_vel if axis < 3 else max_ang_vel
                        v_target[axis] += sign * vel_mag
                    v_filtered[:] = alpha * v_target + (1.0 - alpha) * v_filtered
                    if active_keys or float(np.linalg.norm(v_filtered)) > 1e-5:
                        cmd_pos += v_filtered[:3] * dt
                        cmd_rpy += v_filtered[3:] * dt
                        cmd_ori = tuple(self.rpy_to_quaternion(cmd_rpy.tolist()))
                        new_joint = self._try_apply_ik_guarded(
                            cmd_joint, cmd_pos, cmd_ori, ik_max_joint_step
                        )
                        if new_joint is None:
                            fk = self.forward_kin(cmd_joint.tolist())
                            if fk and "pos" in fk and "ori" in fk:
                                cmd_pos[:] = np.array(fk["pos"], dtype=float)
                                cmd_rpy[:] = np.array(
                                    self.quaternion_to_rpy(fk["ori"]), dtype=float
                                )
                            v_filtered[:] = 0.0
                        else:
                            cmd_joint = new_joint
                    self.set_waypoint_to_canbus(cmd_joint.tolist())
                    elapsed = time.time() - t0
                    time.sleep(max(0.0, dt - elapsed))
            finally:
                if self.connected:
                    self.leave_tcp2canbus_mode()

        print("\n" + "=" * 50)
        print("🎮 标定微调遥操 (CAN)")
        print(" 平移 W/S(X) A/D(Y) R/F(Z) | 旋转 U/O I/K J/L | +/- 调速")
        print(" ESC 结束遥操，回到标定确认")
        print("=" * 50 + "\n")

        ctrl_thread = threading.Thread(target=control_loop, daemon=True)
        ctrl_thread.start()
        with keyboard.Listener(on_press=on_press, on_release=on_release) as listener:
            listener.join()
        time.sleep(0.2)
        self._print_current_pose("遥操结束")

    def _confirm_calibration_pose(
        self, context: str, on_teleop_exit: Optional[Callable[[], None]] = None
    ) -> None:
        """After auto-move: user continues or enters keyboard teleop for fine alignment."""
        if not self.calibration_pose_confirm:
            return
        while True:
            self._print_current_pose(context)
            print(
                f"\n[{context}] 自动对点完成。\n"
                "  回车 — 从此位开始力控标定\n"
                "  t   — 键盘遥操微调 (ESC 结束并写回路点)\n"
                "  q   — 中止整个标定流程\n"
            )
            choice = input("请选择: ").strip().lower()
            if choice in ("", "y", "c"):
                return
            if choice == "t":
                self._run_keyboard_teleop_session()
                if on_teleop_exit is not None:
                    on_teleop_exit()
                continue
            if choice == "q":
                self.raise_error(
                    RobotErrorType.RobotError_Move, -1, "user aborted calibration"
                )
                return
            print("无效输入，请重试。")

    def _move_then_confirm(
        self,
        pos,
        ori,
        context: str,
        on_teleop_exit: Optional[Callable[[], None]] = None,
    ) -> int:
        result = self.move_to_target_in_cartesian(pos, ori)
        if result != RobotErrorType.RobotError_SUCC:
            return result
        self._confirm_calibration_pose(context, on_teleop_exit=on_teleop_exit)
        return RobotErrorType.RobotError_SUCC

    def close(self, shutdown_ros: bool = True):
        """Release SDK and optionally shut down rclpy (disable when ROS is owned by caller, e.g. ee_keyboard)."""
        if self.connected:
            self.move_stop()
            # self.robot_shutdown()
            self.disconnect()
        self.uninitialize()
        if self.node:
            self.node.destroy_node()
        if shutdown_ros and rclpy.ok():
            rclpy.shutdown()
        if self.force_log_file:
            self.force_log_file.close()
        if self.force_serial and self.force_serial.is_open:
            self.force_serial.close()
        # 关闭所有标定文件
        for part_name, file_handle in self.calibration_files.items():
            if file_handle and not file_handle.closed:
                file_handle.close()
                logger.info(f"已关闭 {part_name} 的标定文件")

    def get_calibration_file(self, part_name: str):
        """
        获取或创建特定部分的标定文件

        Args:
            part_name (str): 部分名称

        Returns:
            file handle: 文件句柄
        """
        if (
            part_name not in self.calibration_files
            or self.calibration_files[part_name].closed
        ):
            part_display_name = CALIBRATION_PARTS.get(part_name, part_name)
            filename = f"calibration_{part_name}.csv"

            try:
                # 如果文件已存在，优先检查并在需要时做迁移/规范化（加入 RegionName 列），再以追加模式打开
                if os.path.exists(filename):
                    # 如果文件非空，检查头部是否包含 RegionName；若没有则先做迁移
                    if os.path.getsize(filename) > 0:
                        try:
                            with open(filename, "r", encoding="utf-8") as _fh:
                                first_line = _fh.readline()
                        except Exception:
                            first_line = ""

                        if "RegionName" not in first_line:
                            # 迁移：将旧格式更新为包含 RegionName 的格式（同时不删除任何行）
                            self.clear_region_in_calibration_file(part_name, None)

                    # 打开为追加模式
                    self.calibration_files[part_name] = open(
                        filename, "a", encoding="utf-8"
                    )
                else:
                    # 新建文件并写表头（包含 RegionName）
                    self.calibration_files[part_name] = open(
                        filename, "w", encoding="utf-8"
                    )
                    # 统一 header 为仅包含 RegionName（不再写 PartName）
                    self.calibration_files[part_name].write(
                        "Timestamp,Force(N),SensorIndex,SensorReading,RegionName\n"
                    )
                    self.calibration_files[part_name].flush()

                if self.node:
                    self.node.get_logger().info(
                        f"✨ 已创建/打开 {part_display_name} 的标定文件: {filename}"
                    )
                else:
                    logger.info(
                        f"✨ 已创建/打开 {part_display_name} 的标定文件: {filename}"
                    )

            except Exception as e:
                error_msg = f"无法创建 {part_display_name} 的标定文件 {filename}: {e}"
                if self.node:
                    self.node.get_logger().error(error_msg)
                else:
                    logger.error(error_msg)
                return None

        return self.calibration_files[part_name]

    def _infer_region_by_sensor_index(self, sensor_index: int) -> str:
        """
        Infer region key (e.g., 'index_distal') for a given sensor index using SENSOR_MAPPING.
        Returns empty string if not found.
        """
        try:
            si = int(sensor_index)
        except Exception:
            return ""
        for region_key, info in SENSOR_MAPPING.items():
            start = int(info.get("start", 0))
            rows = int(info.get("rows", 0))
            cols = int(info.get("cols", 0))
            count = rows * cols
            if si >= start and si < start + count:
                return region_key
        return ""

    def clear_region_in_calibration_file(self, part_name: str, region_name: str = None):
        """
        Normalize the calibration CSV for `part_name` to include a RegionName column (if missing).
        If `region_name` is provided (str), also remove all rows belonging to that region.

        Args:
            part_name: part identifier (matches filename `calibration_{part_name}.csv`)
            region_name: if None, only normalize; if provided, remove rows for this region.
        """
        filename = f"calibration_{part_name}.csv"
        try:
            # Close existing open handle if any
            fh = self.calibration_files.get(part_name)
            if fh and not fh.closed:
                fh.close()

            if not os.path.exists(filename):
                # ensure future writes will create the file with proper header via get_calibration_file
                return

            with open(filename, "r", encoding="utf-8") as f:
                lines = f.readlines()
            if not lines:
                return

            header_line = lines[0].strip()
            cols = [c.strip().lower() for c in header_line.split(",")]
            has_region_col = "regionname" in cols
            has_part_col = "partname" in cols

            new_lines = []
            for line in lines[1:]:
                parts = line.strip().split(",")
                ts = parts[0] if len(parts) > 0 else ""
                force = parts[1] if len(parts) > 1 else ""
                sensor_idx = parts[2] if len(parts) > 2 else ""
                sensor_read = parts[3] if len(parts) > 3 else ""

                # Determine region column if present, otherwise infer by sensor index
                region_col = ""
                try:
                    if has_region_col:
                        region_idx = cols.index("regionname")
                        if len(parts) > region_idx:
                            region_col = parts[region_idx]
                        else:
                            region_col = self._infer_region_by_sensor_index(sensor_idx)
                    else:
                        region_col = self._infer_region_by_sensor_index(sensor_idx)
                except Exception:
                    region_col = self._infer_region_by_sensor_index(sensor_idx)

                # If the caller requested removal of a region_name, skip lines matching it
                if region_name is not None and region_col == region_name:
                    continue

                # rebuild normalized line with 5 columns (no PartName)
                new_line = f"{ts},{force},{sensor_idx},{sensor_read},{region_col}\n"
                new_lines.append(new_line)

            # write normalized header and content (统一为不包含 PartName 的格式)
            header = "Timestamp,Force(N),SensorIndex,SensorReading,RegionName\n"
            with open(filename, "w", encoding="utf-8") as f:
                f.write(header)
                for line in new_lines:
                    f.write(line)

            # reopen in append mode for future writes
            self.calibration_files[part_name] = open(filename, "a", encoding="utf-8")
            if region_name is None:
                msg = (
                    f"♻️ 已规范化 {filename}（已添加 RegionName 列，如可推断则已填充）。"
                )
            else:
                msg = f"🧹 已移除 {filename} 中的区域 '{region_name}' 的旧记录并规范化文件。"

            if self.node:
                self.node.get_logger().info(msg)
            else:
                logger.info(msg)

        except Exception as e:
            err = f"无法清理/规范化 {filename}: {e}"
            if self.node:
                self.node.get_logger().error(err)
            else:
                logger.error(err)

    def move_z_in_step(self, distance: float = 0.0001, direction: str = "up"):
        self.check_event()
        if self.rshd >= 0 and self.connected:
            current_waypoint = self.get_current_waypoint()
            current_pos = np.array(current_waypoint["pos"])
            if direction == "up":
                current_pos += [0, 0, distance]
            else:
                current_pos -= [0, 0, distance]
            result = self.move_to_target_in_cartesian(
                current_pos.tolist(), current_waypoint["ori"]
            )
            if result != RobotErrorType.RobotError_SUCC:
                self.raise_error(RobotErrorType.RobotError_Move, result, "move error")
            else:
                return RobotErrorType.RobotError_SUCC
        else:
            return RobotErrorType.RobotError_NotLogin

    def move_x_in_step(self, distance: float = 0.0001, direction: str = "left"):
        self.check_event()
        time.sleep(0.1)
        if self.rshd >= 0 and self.connected:
            current_waypoint = self.get_current_waypoint()
            current_pos = np.array(current_waypoint["pos"])
            if direction == "left":
                current_pos += [distance, 0, 0]
            else:
                current_pos -= [distance, 0, 0]
            result = self.move_to_target_in_cartesian(
                current_pos.tolist(), current_waypoint["ori"]
            )
            if result != RobotErrorType.RobotError_SUCC:
                self.raise_error(RobotErrorType.RobotError_Move, result, "move error")
            else:
                return RobotErrorType.RobotError_SUCC
        else:
            return RobotErrorType.RobotError_NotLogin

    def move_y_in_step(self, distance: float = 0.0001, direction: str = "front"):
        self.check_event()
        time.sleep(0.1)
        if self.rshd >= 0 and self.connected:
            current_waypoint = self.get_current_waypoint()
            current_pos = np.array(current_waypoint["pos"])
            if direction == "front":
                current_pos -= [0, distance, 0]
            else:
                current_pos += [0, distance, 0]
            result = self.move_to_target_in_cartesian(
                current_pos.tolist(), current_waypoint["ori"]
            )
            if result != RobotErrorType.RobotError_SUCC:
                self.raise_error(RobotErrorType.RobotError_Move, result, "move error")
            else:
                return RobotErrorType.RobotError_SUCC
        else:
            return RobotErrorType.RobotError_NotLogin

    def _try_apply_ik_guarded(
        self,
        cmd_joint: np.ndarray,
        cmd_pos: np.ndarray,
        cmd_ori: tuple,
        max_joint_step: float,
    ) -> Optional[np.ndarray]:
        """IK with per-cycle joint jump limit; returns None on reject."""
        ik_res = self.inverse_kin(cmd_joint.tolist(), cmd_pos.tolist(), cmd_ori)
        if not ik_res or "joint" not in ik_res:
            return None
        new_joint = np.array(ik_res["joint"], dtype=float)
        if float(np.linalg.norm(new_joint - cmd_joint)) > max_joint_step:
            return None
        return new_joint

    def apply_force_and_read_onepoint(
        self,
        target_force_N: float,
        target_point_absolute_index: int,
        part_name: str = "unknown",
        region_name: str = None,
        point_label: str = None,
    ) -> Tuple[Optional[float], Optional[float]]:
        """
        极简两阶段力控标定 (位置/导纳控制版)：
        解决速度控制在通信延迟下导致的“持续下压过冲”问题。
        主线程根据力误差计算目标位置 (target_z)，CAN 线程平滑追踪该位置。
        """
        import time
        import gc
        import numpy as np
        import rclpy
        import threading
        from collections import deque
        from nglove_interfaces.msg import FourChipsData
        from nglove_interfaces.srv import TriggerCalibration

        # --- 参数配置 ---
        FORCE_TOL = 0.15  # N: 稳定误差范围
        FORCE_STABLE_TIME = 0.50  # s: 维持在误差范围内的时间
        TOTAL_TIMEOUT = 40.0  # s: 整体超时时间
        CONTACT_THRESHOLD = 0.10  # N: 接触力阈值 (稍微调高防噪)

        CAN_HZ = 100.0
        IK_MAX_JOINT_STEP = 0.008  # rad per 100Hz CAN tick

        # 位置控制参数 (导纳控制)
        # 注意：Z轴向下为负，所以下压是减小Z
        APPROACH_STEP = (
            0.00002  # m: 未接触时，每次下压 0.02mm (0.2mm/s) -> 极慢接近，防撞击！
        )
        KP_P = 0.000001  # m/N: 1N误差对应 1um 步长
        KI_P = 0.0000002  # m/(N*s)
        I_CLAMP_P = 0.0002  # m: 积分限幅 (0.2mm)

        MAX_DOWN_STEP = 0.00002  # m: 接触后单次最大下压步长 0.02mm (20um)
        MAX_UP_STEP = 0.0005  # m: 接触后单次最大抬起步长 0.5mm (500um)

        # CAN 线程平滑追踪的速度限制
        V_MAX_DOWN = 0.0002  # m/s: 物理最大下压速度 0.2mm/s -> 配合 APPROACH_STEP
        V_MAX_UP = 0.005  # m/s: 物理最大抬起速度 5mm/s

        # 数据缓存
        sensor_buf = deque(maxlen=50)
        force_buf = deque(maxlen=50)

        def _sensor_cb(msg: FourChipsData):
            try:
                if len(msg.data_113) > target_point_absolute_index:
                    v = float(msg.data_113[target_point_absolute_index])
                    sensor_buf.append(v)
            except Exception:
                pass

        part_display_name = CALIBRATION_PARTS.get(part_name, part_name)
        region_display = region_name if region_name is not None else ""

        sub = None
        can_stop = None
        can_thread = None

        try:
            gc.disable()
            if not self.node:
                self._initialize_ros()

            sub = self.node.create_subscription(
                FourChipsData, "/four_chips_data", _sensor_cb, 10
            )

            self.node.get_logger().info(
                f"🎯 开始标定(位置控制版)：目标力={target_force_N:.2f}N, index={target_point_absolute_index}, 部位={part_display_name}, 区域={region_display}"
            )

            # --- 启动 CAN 透传线程 ---
            current_wp = self.get_current_waypoint()
            if not current_wp:
                self.node.get_logger().error("无法获取初始位姿。")
                return None, None

            cmd_pos = np.array(current_wp["pos"], dtype=float)
            cmd_ori = tuple(current_wp["ori"])
            cmd_joint = np.array(current_wp["joint"], dtype=float)

            can_lock = threading.Lock()
            can_stop = threading.Event()

            # 共享变量：目标 Z 坐标 (base frame, 向下减小)
            shared_state = {"target_z": cmd_pos[2], "cmd_joint": cmd_joint}
            can_dt = 1.0 / CAN_HZ

            def _canbus_stream_loop():
                pos = cmd_pos.copy()
                current_z = pos[2]
                while not can_stop.is_set():
                    t0 = time.time()
                    with can_lock:
                        target_z = shared_state["target_z"]

                        # 计算需要移动的距离
                        dz = target_z - current_z

                        # 速度限幅
                        max_dz_down = -V_MAX_DOWN * can_dt  # 向下是负的
                        max_dz_up = V_MAX_UP * can_dt  # 向上是正的

                        # 限制 dz
                        if dz < max_dz_down:
                            dz = max_dz_down
                        elif dz > max_dz_up:
                            dz = max_dz_up

                        current_z += dz
                        pos[2] = current_z

                        new_joint = self._try_apply_ik_guarded(
                            shared_state["cmd_joint"], pos, cmd_ori, IK_MAX_JOINT_STEP
                        )
                        if new_joint is not None:
                            shared_state["cmd_joint"] = new_joint
                        else:
                            # IK失败，回退
                            current_z -= dz
                            pos[2] = current_z

                        self.set_waypoint_to_canbus(shared_state["cmd_joint"].tolist())
                    elapsed = time.time() - t0
                    time.sleep(max(0.0, can_dt - elapsed))

            self.enter_tcp2canbus_mode()
            can_thread = threading.Thread(target=_canbus_stream_loop, daemon=True)
            can_thread.start()

            # --- 控制主循环 ---
            start_time = time.time()
            last_time = start_time
            stable_enter_time = None
            err_I = 0.0

            while True:
                now = time.time()
                dt = max(1e-3, now - last_time)
                last_time = now

                if now - start_time > TOTAL_TIMEOUT:
                    self.node.get_logger().warning(f"⚠️ 总超时({TOTAL_TIMEOUT}s)！")
                    break

                rclpy.spin_once(self.node, timeout_sec=0.0)

                current_force = self.get_force(
                    target_force_N=target_force_N, log_to_console=False, max_retries=1
                )

                if current_force is None:
                    time.sleep(0.02)
                    continue

                force_buf.append(current_force)

                # 核心逻辑：位置控制 (Admittance)
                if current_force < CONTACT_THRESHOLD:
                    # 阶段1：未接触，固定步长下压
                    delta_z = -APPROACH_STEP  # 向下
                    err_I = 0.0
                    stable_enter_time = None
                else:
                    # 阶段2：已接触，位置 PI 闭环
                    error = target_force_N - current_force
                    err_I += error * dt
                    err_I = float(np.clip(err_I, -I_CLAMP_P, I_CLAMP_P))

                    # 计算目标位置的增量 (error > 0 需要下压，即 Z 减小)
                    # 所以 delta_z = - (KP_P * error + KI_P * err_I)
                    raw_delta_z = -(KP_P * error + KI_P * err_I)

                    # 限制单步增量
                    if raw_delta_z < 0:
                        # 下压
                        delta_z = float(max(raw_delta_z, -MAX_DOWN_STEP))
                    else:
                        # 抬起
                        delta_z = float(min(raw_delta_z, MAX_UP_STEP))

                    # 判稳逻辑
                    if abs(error) <= FORCE_TOL:
                        if stable_enter_time is None:
                            stable_enter_time = now
                        elif (now - stable_enter_time) >= FORCE_STABLE_TIME:
                            self.node.get_logger().info(
                                f"✅ 力稳定满足 ({FORCE_STABLE_TIME}s)！"
                            )
                            break
                    else:
                        stable_enter_time = None

                self.node.get_logger().info(
                    f"[FSM] force={current_force:.2f}N, err={target_force_N - current_force:.2f}N, dz={delta_z*1000:.4f}mm, target_z={shared_state['target_z']:.4f}, point {point_label} "
                )

                with can_lock:
                    shared_state["target_z"] += delta_z

            # --- 结束处理 ---
            # 取最近的统计值
            confirmed_force = float(np.mean(force_buf)) if force_buf else None
            final_sensor_reading = float(np.median(sensor_buf)) if sensor_buf else None

            if confirmed_force is None:
                self.node.get_logger().error("❌ 无法获取有效力值。")
                return None, None

            # 调用 ROS 服务
            try:
                req = TriggerCalibration.Request()
                req.target_sensor_index = target_point_absolute_index
                req.applied_force = confirmed_force
                future = self.trigger_calibration_service.call_async(req)
                rclpy.spin_until_future_complete(self.node, future, timeout_sec=5.0)

                if future.done() and future.result() and future.result().success:
                    final_sensor_reading = float(future.result().sensor_reading)
                    self.node.get_logger().info(
                        f"✅ 服务成功：sensor={final_sensor_reading:.4f}"
                    )
                else:
                    self.node.get_logger().warning(
                        "⚠️ 服务失败或超时，使用本地缓存传感器值。"
                    )
            except Exception as e:
                self.node.get_logger().error(f"❌ 服务异常：{e}")

            # 写文件
            cal_file = self.get_calibration_file(part_name)
            if cal_file:
                sensor_to_write = (
                    final_sensor_reading
                    if final_sensor_reading is not None
                    else float("nan")
                )
                cal_file.write(
                    f"{time.time()},{confirmed_force:.4f},{target_point_absolute_index},{sensor_to_write:.4f},{region_display}\n"
                )
                cal_file.flush()
                self.node.get_logger().info(
                    f"💾 记录完成：force={confirmed_force:.4f}N, sensor={sensor_to_write:.4f}"
                )

            return confirmed_force, final_sensor_reading

        finally:
            if can_stop is not None:
                can_stop.set()
            if can_thread is not None:
                can_thread.join(timeout=1.0)
            if self.connected:
                self.leave_tcp2canbus_mode()
            if sub is not None and self.node is not None:
                self.node.destroy_subscription(sub)
            gc.enable()

    def get_force(
        self,
        target_force_N: Optional[float] = None,
        log_to_console: bool = True,
        max_retries: int = 1,
    ) -> Optional[float]:
        """
        [加固版] 发送指令并解析返回的力值，增加了重试机制和打印开关。

        Args:
            target_force_N (Optional[float]): 目标力，用于日志记录。
            log_to_console (bool): 是否在控制台打印实时力值。
            max_retries (int): 失败时最大重试次数。

        :return: 浮点型力值，或失败时返回 None。
        """
        if not self.force_serial or not self.force_serial.is_open:
            logger.error("测力计串口未连接。")
            return None

        for attempt in range(max_retries):
            try:
                self.force_serial.reset_input_buffer()

                # 1. 发送指令
                self.force_serial.write(self.FORCE_SENSOR_COMMAND)
                self.force_serial.flush()  # 确保指令立刻被推入物理串口

                # 2. 魔法在这里：读取正好 9 个字节（Modbus 返回长度）
                # 这样代码只会被阻塞 ~20ms（硬件物理延迟），而不用傻等 50ms
                response = self.force_serial.read(9)

                if (
                    response
                    and len(response) == 9  # 确保收齐了 9 个字节
                    and response[0] == 0x01
                    and response[1] == 0x03
                ):
                    result = -struct.unpack(">f", response[3:7])[0]

                    if self.force_log_file:
                        log_line = (
                            f"{time.time()},{result:.6f},{target_force_N or 0.0:.6f}\n"
                        )
                        self.force_log_file.write(log_line)
                        self.force_log_file.flush()

                    if log_to_console:
                        print(f"✅ 当前力反馈: {result:.6f} N", end="\r")

                    return result

            except Exception as e:
                logger.error(f"get_force 错误 (尝试 {attempt + 1}/{max_retries}): {e}")

        if log_to_console:
            print(" " * 40, end="\r")
        else:
            return RobotErrorType.RobotError_NotLogin

    def _travel_to_region_start(
        self, start_waypoint: dict, region_transfer_lift: float = 0.005
    ) -> int:
        """
        Inter-region transfer: lift first, move at safe height, then descend to waypoint Z.
        """
        self.check_event()
        if not (self.rshd >= 0 and self.connected):
            return RobotErrorType.RobotError_NotLogin

        start_pos = start_waypoint["pos"]
        start_ori = start_waypoint["ori"]
        safe_pos = (
            start_pos[0],
            start_pos[1],
            start_pos[2] + region_transfer_lift,
        )

        result = self.move_z_in_step(region_transfer_lift, "up")
        if result != RobotErrorType.RobotError_SUCC:
            return result

        result = self.move_to_target_in_cartesian(safe_pos, start_ori)
        if result != RobotErrorType.RobotError_SUCC:
            return result

        result = self.move_to_target_in_cartesian(start_pos, start_ori)
        return result

    def _move_to_start_waypoint(self, waypoint: dict) -> Optional[dict]:
        """Move to the taught first-region start pose before calibration."""
        result = self.move_to_target_in_cartesian(waypoint["pos"], waypoint["ori"])
        if result != RobotErrorType.RobotError_SUCC:
            self.raise_error(
                RobotErrorType.RobotError_Move,
                result,
                "move to calibration start failed",
            )
            return None
        return waypoint

    def calibration_a_region(
        self,
        start_waypoint: dict,
        region_name: str,
        x_spacing: float = 0.00350,
        y_spacing: float = 0.00350,
    ):
        """
        以给定的起始点为基准，全自动标定一个传感器区域。
        """
        self.check_event()
        if not (self.rshd >= 0 and self.connected):
            return
        forces_to_apply = [0, 0.5, 1, 1.5, 2, 2.5, 3, 3.5, 4, 4.5, 5]
        # Intra-region: stay at waypoint Z, translate XY only.
        # Inter-region: use _travel_to_region_start() before entering this function.
        try:
            region_info = SENSOR_MAPPING[region_name]
            part_name = region_info["part"]  # 获取部分名称
            part_display_name = CALIBRATION_PARTS.get(part_name, part_name)
            # 在开始本区域标定前，清除该 region 的旧记录（只覆盖该 region）
            try:
                self.clear_region_in_calibration_file(part_name, region_name)
                if self.node:
                    self.node.get_logger().info(
                        f"🧹 已清除 {part_display_name} 文件中区域 '{region_name}' 的旧记录，开始新一轮标定。"
                    )
                else:
                    logger.info(
                        f"🧹 已清除 {part_display_name} 文件中区域 '{region_name}' 的旧记录，开始新一轮标定。"
                    )
            except Exception as e:
                if self.node:
                    self.node.get_logger().error(f"无法清除旧记录: {e}")
                else:
                    logger.error(f"无法清除旧记录: {e}")

            start_pos = start_waypoint["pos"]
            start_ori = start_waypoint["ori"]
            # 移除标定区域前的硬下压，让机械臂直接停留在上方
            # above_start_pos = (start_pos[0], start_pos[1], start_pos[2] + lift_height)
            # self.move_to_target_in_cartesian(above_start_pos, start_ori) # 注释掉，不强行抬起

            logger.info(f"\n{'='*50}")
            logger.info(f"🎯 开始标定部分: {part_display_name} - 区域: {region_name}")
            logger.info(f"{'='*50}")
            for row in range(SENSOR_MAPPING[region_name]["rows"]):
                for col in range(SENSOR_MAPPING[region_name]["cols"]):
                    on_pos = (
                        start_pos[0] - col * x_spacing,
                        start_pos[1] + row * y_spacing,
                        start_pos[2],
                    )
                    absolute_index = (
                        region_info["start"] + row * region_info["cols"] + col
                    )
                    logger.info(
                        f"\n{'='*20} 🎯 标定点: {region_name}({row},{col}), 索引: {absolute_index} {'='*20}"
                    )

                    point_label = f"{region_name}({row},{col}) idx={absolute_index}"

                    def _on_teleop_exit(
                        _row=row,
                        _col=col,
                        _label=point_label,
                    ):
                        nonlocal start_pos, start_ori
                        self._update_region_waypoint_from_teleop(
                            start_waypoint,
                            region_name,
                            _row,
                            _col,
                            x_spacing,
                            y_spacing,
                            _label,
                        )
                        start_pos = tuple(start_waypoint["pos"])
                        start_ori = tuple(start_waypoint["ori"])

                    if row == 0 and col == 0:
                        self._confirm_calibration_pose(
                            f"标定点 {point_label} — 区域首点",
                            on_teleop_exit=_on_teleop_exit,
                        )
                    else:
                        above_pos_no_lift = (on_pos[0], on_pos[1], start_pos[2])
                        result = self._move_then_confirm(
                            above_pos_no_lift,
                            start_ori,
                            f"标定点 {point_label}",
                            on_teleop_exit=_on_teleop_exit,
                        )
                        if result != RobotErrorType.RobotError_SUCC:
                            self.raise_error(
                                RobotErrorType.RobotError_Move,
                                result,
                                "move to calibration point failed",
                            )
                            return

                    for force in forces_to_apply:
                        logger.info(f"--- 尝试施加 {force:.2f}N 的力 ---")
                        # 🚨 关键修复：移除硬下压，让力控算法自己去轻柔接触！
                        # self.move_to_target_in_cartesian(on_pos, start_ori)

                        force_read, sensor_read = self.apply_force_and_read_onepoint(
                            force,
                            absolute_index,
                            part_name,
                            region_name,
                            point_label=point_label,
                        )

                        if force_read is not None:
                            sensor_text = (
                                f"{sensor_read:.4f}"
                                if sensor_read is not None
                                else "nan"
                            )
                            logger.info(
                                f"🌟 成功记录数据点: (力: {force_read:.4f}N, 读数: {sensor_text})"
                            )
                        else:
                            logger.error("未能记录此力值的数据点。")
                        time.sleep(0.2)
                        # 🚨 关键修复：移除每次测力后的抬起，实现“阶梯式连续加载”
                        # self.move_to_target_in_cartesian(above_pos, start_ori)
                        # time.sleep(0.2)

                    # 测完该点的所有力后，统一抬起，准备去下一个点
                    # 抬起到给定的初始路点高度，而不是额外再加 lift_height
                    above_pos_no_lift = (on_pos[0], on_pos[1], start_pos[2])
                    self.move_to_target_in_cartesian(above_pos_no_lift, start_ori)
                    time.sleep(0.2)

            logger.info(
                f"\n✅ 部分 '{part_display_name}' - 区域 '{region_name}' 标定完成！"
            )
        except Exception as e:
            logger.error(f"标定过程出错: {e}")
            self.raise_error(RobotErrorType.RobotError_Move, -1, "calibration error")

    def calibration_part_regions(
        self,
        part_name: str,
        region_slots: list,
        first_waypoint: dict = None,
    ) -> int:
        """
        Calibrate selected regions of one part. Each region writes to
        calibration_{part_name}.csv with RegionName; only cleared region is overwritten.
        """
        self.check_event()
        if not (self.rshd >= 0 and self.connected):
            return RobotErrorType.RobotError_NotLogin

        plan = PART_REGION_PLAN[part_name]
        slots = sorted(set(int(s) for s in region_slots))
        for slot in slots:
            if slot < 0 or slot >= len(plan):
                logger.error(
                    f"无效 region 序号 {slot}，{part_name} 仅有 {len(plan)} 个区域"
                )
                return RobotErrorType.RobotError_Move

        result = RobotErrorType.RobotError_SUCC
        for seq_i, slot in enumerate(slots):
            region_name, wp_attr, x_sp, y_sp = plan[slot]
            waypoint = getattr(self, wp_attr)
            if slot == 0 and first_waypoint is not None:
                waypoint = first_waypoint

            if seq_i == 0:
                if slot == 0:
                    moved = self._move_to_start_waypoint(waypoint)
                    if moved is None:
                        return RobotErrorType.RobotError_Move
                else:
                    result = self._travel_to_region_start(waypoint)
            else:
                result = self._travel_to_region_start(waypoint)

            if result != RobotErrorType.RobotError_SUCC:
                self.raise_error(RobotErrorType.RobotError_Move, result, "move error")
                return result

            self.calibration_a_region(waypoint, region_name, x_sp, y_sp)

        return RobotErrorType.RobotError_SUCC

    # --- 标定函数：使用绝对waypoint定位，避免累积误差 ---
    def calibration_index_finger(
        self,
        first_point_of_first_region_on_waypoint: dict,
        region_slots: list = None,
    ):
        """标定食指 - 使用绝对waypoint定位"""
        slots = region_slots if region_slots is not None else [0, 1, 2]
        return self.calibration_part_regions(
            "index_finger", slots, first_point_of_first_region_on_waypoint
        )

    def calibration_middle_finger(
        self,
        first_point_of_first_region_on_waypoint: dict,
        region_slots: list = None,
    ):
        """标定中指 - 使用绝对waypoint定位"""
        slots = region_slots if region_slots is not None else [0, 1, 2]
        return self.calibration_part_regions(
            "middle_finger", slots, first_point_of_first_region_on_waypoint
        )

    def calibration_ring_finger(
        self,
        first_point_of_first_region_on_waypoint: dict,
        region_slots: list = None,
    ):
        """标定无名指 - 使用绝对waypoint定位"""
        slots = region_slots if region_slots is not None else [0, 1, 2]
        return self.calibration_part_regions(
            "ring_finger", slots, first_point_of_first_region_on_waypoint
        )

    def calibration_pinky_finger(
        self,
        first_point_of_first_region_on_waypoint: dict,
        region_slots: list = None,
    ):
        """标定小指 - 使用绝对waypoint定位"""
        slots = region_slots if region_slots is not None else [0, 1, 2]
        return self.calibration_part_regions(
            "pinky_finger", slots, first_point_of_first_region_on_waypoint
        )

    def calibration_thumb_finger(
        self,
        first_point_of_first_region_on_waypoint: dict,
        region_slots: list = None,
    ):
        """标定大拇指 - 使用绝对waypoint定位"""
        slots = region_slots if region_slots is not None else [0, 1, 2]
        return self.calibration_part_regions(
            "thumb_finger", slots, first_point_of_first_region_on_waypoint
        )

    def calibration_single_part(
        self,
        part_name: str,
        first_waypoint: dict = None,
        region_slots: list = None,
    ):
        """
        单独标定某个部分

        Args:
            part_name (str): 要标定的部分名称 (index_finger, middle_finger, 等)
            first_waypoint (dict): 第一个区域的起始点，如为None则使用默认值
            region_slots (list): 要标定的区域序号 0=远节,1=中节,2=近节；None=全部
        """
        if part_name not in CALIBRATION_PARTS:
            logger.error(f"无效的部分名称: {part_name}")
            logger.info(f"支持的部分: {list(CALIBRATION_PARTS.keys())}")
            return

        part_display_name = CALIBRATION_PARTS[part_name]
        plan = PART_REGION_PLAN[part_name]
        slots = region_slots if region_slots is not None else list(range(len(plan)))

        region_names = [plan[s][0] for s in slots]
        logger.info(f"\n🎆 开始单独标定: {part_display_name}")
        logger.info(f"   区域: {region_names}")
        logger.info(f"{'='*60}")

        default_first = {
            "index_finger": self._first_point_of_first_region_on_waypoint,
            "middle_finger": self._middle_finger_first_point_on_waypoint,
            "ring_finger": self._ring_finger_first_point_on_waypoint,
            "pinky_finger": self._pinky_finger_first_point_on_waypoint,
            "thumb_finger": self._thumb_finger_first_point_on_waypoint,
            "palm_main": self._palm_main_first_point_on_waypoint,
            "palm_secondary": self._palm_secondary_first_point_on_waypoint,
        }
        first_wp = first_waypoint or default_first[part_name]
        self.calibration_part_regions(part_name, slots, first_wp)

        logger.info(f"\n✨ {part_display_name} 标定完成！")
        logger.info(f"{'='*60}")

    def calibration_all_sensors(self, first_point_of_first_region_on_waypoint: dict):
        """校准所有传感器区域"""
        self.calibration_index_finger(first_point_of_first_region_on_waypoint)
        self._travel_to_region_start(self._middle_finger_first_point_on_waypoint)
        self.calibration_middle_finger(self._middle_finger_first_point_on_waypoint)
        self._travel_to_region_start(self._ring_finger_first_point_on_waypoint)
        self.calibration_ring_finger(self._ring_finger_first_point_on_waypoint)
        self._travel_to_region_start(self._pinky_finger_first_point_on_waypoint)
        self.calibration_pinky_finger(self._pinky_finger_first_point_on_waypoint)
        self._travel_to_region_start(self._palm_main_first_point_on_waypoint)
        self.calibration_a_region(
            self._palm_main_first_point_on_waypoint, "palm_main", 0.0039, 0.0039
        )
        self._travel_to_region_start(self._palm_secondary_first_point_on_waypoint)
        self.calibration_a_region(
            self._palm_secondary_first_point_on_waypoint,
            "palm_secondary",
            0.0035,
            0.0035,
        )
        self._travel_to_region_start(self._thumb_finger_first_point_on_waypoint)
        self.calibration_thumb_finger(self._thumb_finger_first_point_on_waypoint)


def prompt_region_slots(part_name: str) -> Optional[list]:
    """Second-level menu: all regions or a single region for one finger/part."""
    plan = PART_REGION_PLAN[part_name]
    part_label = CALIBRATION_PARTS[part_name]

    if len(plan) == 1:
        region_name = plan[0][0]
        print(f"\n{part_label} 仅一个区域 ({region_name})，回车开始标定。")
        input("按回车继续...")
        return [0]

    print(
        f"\n{part_label} — 选择标定范围（各区域独立写入 calibration_{part_name}.csv）："
    )
    print("  a / 0 / 回车 — 三个区域从头连续标定")
    for i, (region_name, _, _, _) in enumerate(plan):
        print(f"  {i + 1} — 仅标定 {FINGER_REGION_LABELS[i]} ({region_name})")
    print("  也可输入组合，如 1,3")

    choice = input("请选择: ").strip().lower()
    if choice in ("", "a", "0"):
        return [0, 1, 2]
    if choice in ("1", "2", "3"):
        return [int(choice) - 1]
    slots = [int(x.strip()) - 1 for x in choice.split(",") if x.strip()]
    if not slots or any(s < 0 or s >= len(plan) for s in slots):
        logger.error("无效选择，已取消。")
        return None
    return sorted(set(slots))


if __name__ == "__main__":
    robot = MyAuboi10()
    try:
        if robot.set_and_startup():
            # 示例：单独标定食指
            print("\n🤖 标定模式选择：")
            print("1. 单独标定食指")
            print("2. 单独标定中指")
            print("3. 单独标定无名指")
            print("4. 单独标定小指")
            print("5. 单独标定大拇指")
            print("6. 单独标定主手掌")
            print("7. 单独标定副手掌")
            print("8. 标定所有部分")

            choice = input("请选择标定模式 (1-8): ").strip()

            if choice in MENU_PART_BY_CHOICE:
                part_name = MENU_PART_BY_CHOICE[choice]
                region_slots = prompt_region_slots(part_name)
                if region_slots is not None:
                    robot.calibration_single_part(part_name, region_slots=region_slots)
            elif choice == "8":
                # 全部标定
                robot.move_to_target_in_cartesian(
                    robot._first_point_of_first_region_on_waypoint["pos"],
                    robot._first_point_of_first_region_on_waypoint["ori"],
                )
                start_point_for_calibration = robot.get_current_waypoint()
                logger.info(f"从路点: {start_point_for_calibration} 开始全部标定")
                robot.calibration_all_sensors(start_point_for_calibration)
            else:
                logger.info("取消标定")

            logger.info("标定程序已完成。")
        else:
            logger.error("启动或连接机械臂失败。")
    except Exception as e:
        logger.error(f"主程序运行中发生异常: {e}")
    finally:
        robot.close()
