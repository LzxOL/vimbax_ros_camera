# Copyright (c) 2024 User. All rights reserved.

import rclpy
from rclpy.node import Node
from sensor_msgs.msg import Image, CameraInfo
from std_msgs.msg import Float32MultiArray, Bool, String
from cv_bridge import CvBridge
import cv2
import numpy as np
import os


class ColorCorrectionNode(Node):
    """
    颜色校正节点
    使用 OpenCV 的 mcc 和 ccm 模块进行 ColorChecker 检测和色彩校正
    """

    def __init__(self):
        super().__init__('color_correction_node')

        # 声明参数
        self.declare_parameter('input_topic', '/vimbax_camera_16833/image_raw')
        self.declare_parameter('output_topic', '/color_corrected/image_raw')
        self.declare_parameter('camera_info_topic', '/vimbax_camera_16833/camera_info')
        self.declare_parameter('ccm_file', '')
        self.declare_parameter('auto_detect_colorchecker', True)
        self.declare_parameter('max_calibration_attempts', 100)
        self.declare_parameter('chart_type', 'MCC24')  # MCC24, DigitalSG, Vinyl

        self.input_topic = self.get_parameter('input_topic').get_parameter_value().string_value
        self.output_topic = self.get_parameter('output_topic').get_parameter_value().string_value
        self.camera_info_topic = self.get_parameter('camera_info_topic').get_parameter_value().string_value
        self.ccm_file = self.get_parameter('ccm_file').get_parameter_value().string_value
        self.auto_detect = self.get_parameter('auto_detect_colorchecker').get_parameter_value().bool_value
        self.max_attempts = self.get_parameter('max_calibration_attempts').get_parameter_value().integer_value
        self.chart_type_name = self.get_parameter('chart_type').get_parameter_value().string_value

        # 根据参数选择色卡类型
        self.chart_type = self._get_chart_type(self.chart_type_name)

        self.bridge = CvBridge()
        self.ccm = None
        self.ccm_enabled = False
        self.calibration_attempts = 0
        self.calibration_done = False
        self.colorchecker_detected = False

        # 创建 ColorCorrectionModel (用于离线计算)
        self.ccm_model = None

        # 发布者
        self.ccm_pub = self.create_publisher(Float32MultiArray, '~/ccm_matrix', 10)
        self.calibration_status_pub = self.create_publisher(Bool, '~/calibration_status', 10)
        self.detection_status_pub = self.create_publisher(String, '~/detection_status', 10)

        # 加载已有的 CCM 文件
        if self.ccm_file and os.path.exists(self.ccm_file):
            self.load_ccm(self.ccm_file)
            self.get_logger().info(f'Loaded CCM from: {self.ccm_file}')

        # 存储最新图像用于校准
        self.latest_image = None
        self.latest_image_header = None

        # 创建定时器来尝试自动校准（每秒一次）
        self.calibration_timer = self.create_timer(1.0, self.try_calibration)

        # 订阅图像话题
        self.image_sub = self.create_subscription(
            Image,
            self.input_topic,
            self.image_callback,
            10
        )

        # 订阅相机信息话题
        self.camera_info_sub = self.create_subscription(
            CameraInfo,
            self.camera_info_topic,
            self.camera_info_callback,
            10
        )

        # 发布校正后的图像
        self.image_pub = self.create_publisher(Image, self.output_topic, 10)

        # 发布相机信息
        self.camera_info_pub = self.create_publisher(CameraInfo, self.output_topic + '/camera_info', 10)

        self.latest_camera_info = None

        # 校准状态
        self.calibration_status = Bool()
        self.calibration_status.data = self.ccm_enabled

        # 检测状态
        self.detection_status = String()

        self.get_logger().info('Color correction node started (using OpenCV mcc/ccm)')
        self.get_logger().info(f'Subscribing to: {self.input_topic}')
        self.get_logger().info(f'Publishing to: {self.output_topic}')
        self.get_logger().info(f'Auto detect ColorChecker: {self.auto_detect}')
        self.get_logger().info(f'Chart type: {self.chart_type_name}')

        if self.ccm is not None:
            self.get_logger().info(f'Loaded CCM Matrix:\n{self.ccm}')

    def _get_chart_type(self, name):
        """获取色卡类型"""
        if name == 'MCC24':
            return cv2.mcc.MCC24
        elif name == 'DigitalSG':
            return cv2.mcc.DigitalSG
        elif name == 'Vinyl':
            return cv2.mcc.Vinyl
        else:
            self.get_logger().warn(f'Unknown chart type: {name}, using MCC24')
            return cv2.mcc.MCC24

    def publish_ccm(self):
        """发布当前的 CCM 矩阵"""
        if self.ccm is not None:
            msg = Float32MultiArray()
            msg.data = self.ccm.flatten().tolist()
            self.ccm_pub.publish(msg)

    def load_ccm(self, filename):
        """从文件加载 CCM 矩阵"""
        try:
            import json
            with open(filename, 'r') as f:
                data = json.load(f)
                self.ccm = np.array(data['ccm'], dtype=np.float64)
                self.ccm_enabled = True
                self.get_logger().info(f'Loaded CCM Matrix:\n{self.ccm}')
        except Exception as e:
            self.get_logger().error(f'Failed to load CCM file: {e}')

    def save_ccm(self, filename):
        """保存 CCM 矩阵到文件"""
        try:
            import json
            data = {'ccm': self.ccm.tolist()}
            with open(filename, 'w') as f:
                json.dump(data, f, indent=2)
            self.get_logger().info(f'Saved CCM to: {filename}')
        except Exception as e:
            self.get_logger().error(f'Failed to save CCM file: {e}')

    def detect_colorchecker_opencv(self, image):
        """
        使用 OpenCV mcc 模块检测 ColorChecker
        返回: (success, checker) - checker 是检测到的色卡对象
        """
        try:
            detector = cv2.mcc.CCheckerDetector_create()
            chart_type = self.chart_type

            # 检测色卡，nc=1 表示最多检测一个色卡
            if not detector.process(image, chart_type, 1):
                return False, None

            checkers = detector.getListColorChecker()
            if len(checkers) > 0:
                return True, checkers[0]

            return False, None
        except Exception as e:
            self.get_logger().error(f'Error detecting ColorChecker: {e}')
            return False, None

    def calibrate_ccm(self, image, checker):
        """
        使用 OpenCV ccm 模块计算 CCM
        """
        try:
            # 获取色卡的 RGB 数据
            chartsRGB = checker.getChartsRGB()  # shape: (24, 3) 或类似结构

            self.get_logger().info(f'ChartsRGB shape: {chartsRGB.shape}')

            # 提取源颜色 (测量的颜色)
            src = chartsRGB[:, 1].copy()  # (N, 3)

            # 确保是连续数组并转换为正确格式
            src = src.astype(np.float64)
            if src.max() > 1.0:
                src = src / 255.0  # 归一化到 [0, 1]

            src = src.reshape((-1, 1, 3))  # (N, 1, 3) for CV_64FC3
            src = np.ascontiguousarray(src)

            # 创建颜色校正模型
            self.ccm_model = cv2.ccm.ColorCorrectionModel(src, cv2.ccm.COLORCHECKER_Macbeth)
            self.ccm_model.run()

            # 获取 CCM 矩阵
            self.ccm = self.ccm_model.getCCM()
            loss = self.ccm_model.getLoss()

            self.get_logger().info(f'CCM Matrix:\n{self.ccm}')
            self.get_logger().info(f'CCM Loss: {loss}')

            self.ccm_enabled = True

            # 如果指定了文件路径，保存 CCM
            if self.ccm_file:
                self.save_ccm(self.ccm_file)

            # 更新校准状态
            self.calibration_status.data = True
            self.calibration_status_pub.publish(self.calibration_status)

            return True

        except Exception as e:
            self.get_logger().error(f'Error computing CCM: {e}')
            import traceback
            traceback.print_exc()
            return False

    def apply_ccm(self, image):
        """
        应用 CCM 矩阵对图像进行颜色校正
        """
        if self.ccm is None or not self.ccm_enabled or self.ccm_model is None:
            return image

        try:
            # 转换图像格式
            img_float = image.astype(np.float64)
            if img_float.max() > 1.0:
                img_float = img_float / 255.0

            # 确保是连续的
            img_float = np.ascontiguousarray(img_float)

            # 使用模型的 infer 方法进行校正
            calibrated = self.ccm_model.infer(img_float)

            # 恢复原始格式
            if calibrated.max() <= 1.0:
                calibrated = calibrated * 255.0

            calibrated = np.clip(calibrated, 0, 255).astype(np.uint8)

            return calibrated

        except Exception as e:
            self.get_logger().error(f'Error applying CCM: {e}')
            return image

    def try_calibration(self):
        """定时尝试校准"""
        if not self.auto_detect or self.calibration_done or self.latest_image is None:
            return

        if self.calibration_attempts >= self.max_attempts:
            self.get_logger().warn(f'Max calibration attempts ({self.max_attempts}) reached')
            self.calibration_done = True
            return

        # 使用 OpenCV mcc 模块检测色卡
        success, checker = self.detect_colorchecker_opencv(self.latest_image)

        if success:
            self.get_logger().info('ColorChecker detected! Computing CCM...')
            self.colorchecker_detected = True
            self.detection_status.data = 'ColorChecker detected, computing CCM...'
            self.detection_status_pub.publish(self.detection_status)

            if self.calibrate_ccm(self.latest_image, checker):
                self.calibration_done = True
                self.get_logger().warn('=' * 60)
                self.get_logger().warn('CCM CALIBRATION COMPLETED!')
                self.get_logger().warn(f'CCM Matrix:\n{self.ccm}')
                self.get_logger().warn('=' * 60)
            else:
                self.get_logger().warn('Failed to compute CCM')
                self.calibration_attempts += 1
        else:
            self.colorchecker_detected = False
            self.detection_status.data = f'Searching for ColorChecker... ({self.calibration_attempts}/{self.max_attempts})'
            self.detection_status_pub.publish(self.detection_status)
            self.calibration_attempts += 1

            if self.calibration_attempts % 10 == 0:
                self.get_logger().info(f'Looking for ColorChecker... ({self.calibration_attempts}/{self.max_attempts})')

    def image_callback(self, msg):
        """处理收到的图像"""
        try:
            # 转换 ROS 图像到 OpenCV 图像 (BGR 格式用于 OpenCV)
            cv_image = self.bridge.imgmsg_to_cv2(msg, "bgr8")

            # 存储最新图像用于校准
            self.latest_image = cv_image.copy()
            self.latest_image_header = msg.header

            # 应用 CCM 校正
            if self.ccm_enabled:
                corrected_image = self.apply_ccm(cv_image)
            else:
                corrected_image = cv_image

            # 转换为 ROS 图像并发布
            output_msg = self.bridge.cv2_to_imgmsg(corrected_image, "bgr8")
            output_msg.header = msg.header
            self.image_pub.publish(output_msg)

            # 发布 CCM 矩阵
            self.publish_ccm()

        except Exception as e:
            self.get_logger().error(f'Error processing image: {e}')

    def camera_info_callback(self, msg):
        """处理相机信息并转发"""
        self.latest_camera_info = msg
        self.camera_info_pub.publish(msg)


def main(args=None):
    rclpy.init(args=args)
    node = ColorCorrectionNode()

    try:
        rclpy.spin(node)
    except KeyboardInterrupt:
        pass
    finally:
        node.destroy_node()
        rclpy.shutdown()


if __name__ == '__main__':
    main()
