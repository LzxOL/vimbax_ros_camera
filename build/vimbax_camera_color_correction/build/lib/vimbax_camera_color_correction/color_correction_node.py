#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import os
import json
import traceback

import rclpy
from rclpy.node import Node

from sensor_msgs.msg import Image, CameraInfo
from std_msgs.msg import Float32MultiArray, Bool, String
from cv_bridge import CvBridge

import cv2
import numpy as np


class ColorCorrectionNode(Node):
    """
    基于 OpenCV mcc + ccm 的 ROS2 色彩校正节点

    功能:
    1. 订阅 RGB 图像 topic
    2. 自动检测 ColorChecker
    3. 使用 OpenCV ColorCorrectionModel 计算校正模型
    4. 对后续图像进行颜色校正并发布

    说明:
    - 输入 topic 约定为 RGB
    - 节点内部转换为 BGR 供 OpenCV 使用
    - 输出时再转换回 RGB
    - 当前真正用于 infer() 的是 self.ccm_model，而不只是 self.ccm 矩阵
    - 仅加载 ccm_file 中的 3x3 矩阵，不足以完整恢复 OpenCV 的 ColorCorrectionModel
      所以本节点以“运行时自动检测并建模”为主
    """

    def __init__(self):
        super().__init__('color_correction_node')

        # -----------------------------
        # Parameters
        # -----------------------------
        self.declare_parameter('input_topic', '/vimbax_camera_220946/image_raw')
        self.declare_parameter('output_topic', '/color_corrected/image_raw')
        self.declare_parameter('camera_info_topic', '/vimbax_camera_220946/camera_info')
        self.declare_parameter('output_camera_info_topic', '/color_corrected/camera_info')

        self.declare_parameter('input_encoding', 'rgb8')   # 输入是 rgb8
        self.declare_parameter('output_encoding', 'rgb8')  # 输出也按 rgb8 发布

        self.declare_parameter('ccm_file', '')
        self.declare_parameter('auto_detect_colorchecker', True)
        self.declare_parameter('max_calibration_attempts', 100)
        self.declare_parameter('chart_type', 'MCC24')   # MCC24, DigitalSG, Vinyl
        self.declare_parameter('max_checkers', 1)

        self.input_topic = self.get_parameter('input_topic').get_parameter_value().string_value
        self.output_topic = self.get_parameter('output_topic').get_parameter_value().string_value
        self.camera_info_topic = self.get_parameter('camera_info_topic').get_parameter_value().string_value
        self.output_camera_info_topic = self.get_parameter('output_camera_info_topic').get_parameter_value().string_value

        self.input_encoding = self.get_parameter('input_encoding').get_parameter_value().string_value
        self.output_encoding = self.get_parameter('output_encoding').get_parameter_value().string_value

        self.ccm_file = self.get_parameter('ccm_file').get_parameter_value().string_value
        self.auto_detect = self.get_parameter('auto_detect_colorchecker').get_parameter_value().bool_value
        self.max_attempts = self.get_parameter('max_calibration_attempts').get_parameter_value().integer_value
        self.chart_type_name = self.get_parameter('chart_type').get_parameter_value().string_value
        self.max_checkers = self.get_parameter('max_checkers').get_parameter_value().integer_value

        # OpenCV 色卡检测类型
        self.chart_type = self._get_mcc_chart_type(self.chart_type_name)
        # OpenCV ccm 参考色卡类型
        self.ccm_chart_type = self._get_ccm_chart_type(self.chart_type_name)

        # -----------------------------
        # Runtime states
        # -----------------------------
        self.bridge = CvBridge()

        # 只保存 3x3 CCM 用于记录/显示
        self.ccm = None
        # 真正用于 infer 的 OpenCV 模型
        self.ccm_model = None

        self.ccm_enabled = False
        self.calibration_done = False
        self.calibration_attempts = 0
        self.colorchecker_detected = False

        self.latest_image_bgr = None
        self.latest_image_header = None
        self.latest_camera_info = None

        # -----------------------------
        # Publishers
        # -----------------------------
        self.image_pub = self.create_publisher(Image, self.output_topic, 10)
        self.camera_info_pub = self.create_publisher(CameraInfo, self.output_camera_info_topic, 10)

        self.ccm_pub = self.create_publisher(Float32MultiArray, '~/ccm_matrix', 10)
        self.calibration_status_pub = self.create_publisher(Bool, '~/calibration_status', 10)
        self.detection_status_pub = self.create_publisher(String, '~/detection_status', 10)

        # -----------------------------
        # Subscribers
        # -----------------------------
        self.image_sub = self.create_subscription(
            Image,
            self.input_topic,
            self.image_callback,
            10
        )

        self.camera_info_sub = self.create_subscription(
            CameraInfo,
            self.camera_info_topic,
            self.camera_info_callback,
            10
        )

        # 定时尝试自动标定
        self.calibration_timer = self.create_timer(1.0, self.try_calibration)

        # 状态消息
        self.calibration_status = Bool()
        self.calibration_status.data = False

        self.detection_status = String()
        self.detection_status.data = 'Idle'

        # 如果提供了 ccm_file，则读取已有 CCM 作为记录用途
        # 注意：仅加载矩阵不能完整恢复 OpenCV 的 ccm_model
        if self.ccm_file and os.path.exists(self.ccm_file):
            self.load_ccm(self.ccm_file)

        # 启动日志
        self.get_logger().info('Color correction node started (OpenCV mcc/ccm)')
        self.get_logger().info(f'Input topic: {self.input_topic}')
        self.get_logger().info(f'Output topic: {self.output_topic}')
        self.get_logger().info(f'CameraInfo in: {self.camera_info_topic}')
        self.get_logger().info(f'CameraInfo out: {self.output_camera_info_topic}')
        self.get_logger().info(f'Input encoding: {self.input_encoding}')
        self.get_logger().info(f'Output encoding: {self.output_encoding}')
        self.get_logger().info(f'Auto detect ColorChecker: {self.auto_detect}')
        self.get_logger().info(f'Chart type: {self.chart_type_name}')
        self.get_logger().info(f'Max calibration attempts: {self.max_attempts}')

        if self.ccm is not None:
            self.get_logger().info(f'Loaded CCM matrix (record only):\n{self.ccm}')

        self.publish_status()

    # ------------------------------------------------------------------
    # Type mapping
    # ------------------------------------------------------------------
    def _get_mcc_chart_type(self, name: str):
        """获取 cv2.mcc 使用的色卡类型"""
        if name == 'MCC24':
            return cv2.mcc.MCC24
        elif name == 'DigitalSG':
            return cv2.mcc.DigitalSG
        elif name == 'Vinyl':
            return cv2.mcc.Vinyl
        else:
            self.get_logger().warn(f'Unknown chart_type "{name}", fallback to MCC24')
            return cv2.mcc.MCC24

    def _get_ccm_chart_type(self, name: str):
        """获取 cv2.ccm.ColorCorrectionModel 使用的参考色卡类型"""
        if name == 'MCC24':
            return cv2.ccm.COLORCHECKER_Macbeth
        elif name == 'DigitalSG':
            if hasattr(cv2.ccm, 'COLORCHECKER_DigitalSG'):
                return cv2.ccm.COLORCHECKER_DigitalSG
            self.get_logger().warn('OpenCV does not provide COLORCHECKER_DigitalSG, fallback to Macbeth')
            return cv2.ccm.COLORCHECKER_Macbeth
        elif name == 'Vinyl':
            if hasattr(cv2.ccm, 'COLORCHECKER_Vinyl'):
                return cv2.ccm.COLORCHECKER_Vinyl
            self.get_logger().warn('OpenCV does not provide COLORCHECKER_Vinyl, fallback to Macbeth')
            return cv2.ccm.COLORCHECKER_Macbeth
        else:
            self.get_logger().warn(f'Unknown ccm chart_type "{name}", fallback to Macbeth')
            return cv2.ccm.COLORCHECKER_Macbeth

    def _create_detector(self):
        """兼容不同 OpenCV 版本的 detector 创建方式"""
        if hasattr(cv2.mcc, 'CCheckerDetector_create'):
            return cv2.mcc.CCheckerDetector_create()
        elif hasattr(cv2.mcc, 'CCheckerDetector'):
            return cv2.mcc.CCheckerDetector.create()
        else:
            raise RuntimeError('OpenCV mcc detector API not found. Please check opencv-contrib-python installation.')

    # ------------------------------------------------------------------
    # Status / IO
    # ------------------------------------------------------------------
    def publish_status(self):
        self.calibration_status_pub.publish(self.calibration_status)
        self.detection_status_pub.publish(self.detection_status)

    def publish_ccm(self):
        """发布当前 3x3 CCM 矩阵"""
        if self.ccm is None:
            return

        msg = Float32MultiArray()
        msg.data = self.ccm.flatten().astype(np.float32).tolist()
        self.ccm_pub.publish(msg)

    def save_ccm(self, filename: str):
        """保存 3x3 CCM 矩阵到 JSON 文件"""
        if self.ccm is None:
            self.get_logger().warn('No CCM to save')
            return

        try:
            data = {
                'ccm': self.ccm.tolist(),
                'chart_type': self.chart_type_name
            }
            with open(filename, 'w', encoding='utf-8') as f:
                json.dump(data, f, indent=2, ensure_ascii=False)
            self.get_logger().info(f'Saved CCM to: {filename}')
        except Exception as e:
            self.get_logger().error(f'Failed to save CCM file: {e}')

    def load_ccm(self, filename: str):
        """
        从文件加载 3x3 CCM 矩阵
        注意：这里只是读取矩阵用于显示/记录，不能完整恢复 OpenCV ColorCorrectionModel
        """
        try:
            with open(filename, 'r', encoding='utf-8') as f:
                data = json.load(f)

            self.ccm = np.array(data['ccm'], dtype=np.float64)

            # 这里只代表“有一个历史矩阵”
            # 不能说明 infer() 已可用，因为 ccm_model 还没建立
            self.get_logger().info(f'Loaded CCM matrix from: {filename}')
            self.get_logger().info(f'Loaded CCM:\n{self.ccm}')
            self.publish_ccm()

        except Exception as e:
            self.get_logger().error(f'Failed to load CCM file: {e}')

    # ------------------------------------------------------------------
    # Detection / calibration
    # ------------------------------------------------------------------
    def detect_colorchecker_opencv(self, image_bgr):
        """
        使用 OpenCV mcc 模块检测 ColorChecker
        返回:
            (success, checker)
        """
        try:
            detector = self._create_detector()

            ok = detector.process(image_bgr, self.chart_type, self.max_checkers)
            if not ok:
                return False, None

            checkers = detector.getListColorChecker()
            if checkers is None or len(checkers) == 0:
                return False, None

            return True, checkers[0]

        except Exception as e:
            self.get_logger().error(f'Error detecting ColorChecker: {e}')
            traceback.print_exc()
            return False, None

    def calibrate_ccm(self, image_bgr, checker):
        """
        使用 OpenCV ccm 模块计算颜色校正模型
        """
        try:
            charts_rgb = checker.getChartsRGB()

            self.get_logger().info(f'ChartsRGB shape: {charts_rgb.shape}')

            # 和你基础程序一致：取第二列作为 patch RGB
            src = charts_rgb[:, 1].copy()

            src = src.astype(np.float64)
            if src.max() > 1.0:
                src = src / 255.0

            # 变成 (N,1,3)，这是 OpenCV ccm 常见要求格式
            src = src.reshape((-1, 1, 3))
            src = np.ascontiguousarray(src)

            self.get_logger().info(f'src shape: {src.shape}, dtype: {src.dtype}')
            self.get_logger().info(f'src min/max: {src.min():.6f} / {src.max():.6f}')

            self.ccm_model = cv2.ccm.ColorCorrectionModel(src, self.ccm_chart_type)
            self.ccm_model.run()

            self.ccm = self.ccm_model.getCCM()
            loss = self.ccm_model.getLoss()

            self.get_logger().info(f'CCM matrix:\n{self.ccm}')
            self.get_logger().info(f'CCM loss: {loss}')

            self.ccm_enabled = True
            self.calibration_done = True
            self.colorchecker_detected = True

            self.calibration_status.data = True
            self.detection_status.data = 'ColorChecker detected, CCM calibration completed'

            if self.ccm_file:
                self.save_ccm(self.ccm_file)

            self.publish_ccm()
            self.publish_status()

            return True

        except Exception as e:
            self.get_logger().error(f'Error computing CCM: {e}')
            traceback.print_exc()
            return False

    def try_calibration(self):
        """
        定时尝试校准
        """
        if not self.auto_detect:
            return

        if self.calibration_done:
            return

        if self.latest_image_bgr is None:
            return

        if self.calibration_attempts >= self.max_attempts:
            self.detection_status.data = f'Max calibration attempts reached: {self.max_attempts}'
            self.publish_status()
            self.get_logger().warn(self.detection_status.data)
            self.calibration_done = True
            return

        success, checker = self.detect_colorchecker_opencv(self.latest_image_bgr)

        if success:
            self.get_logger().info('ColorChecker detected! Start computing CCM...')
            self.detection_status.data = 'ColorChecker detected, computing CCM...'
            self.publish_status()

            ok = self.calibrate_ccm(self.latest_image_bgr, checker)
            if ok:
                self.get_logger().warn('=' * 60)
                self.get_logger().warn('CCM CALIBRATION COMPLETED')
                self.get_logger().warn(f'CCM:\n{self.ccm}')
                self.get_logger().warn('=' * 60)
            else:
                self.calibration_attempts += 1
                self.detection_status.data = f'CCM computation failed ({self.calibration_attempts}/{self.max_attempts})'
                self.publish_status()
        else:
            self.colorchecker_detected = False
            self.calibration_attempts += 1
            self.detection_status.data = (
                f'Searching for ColorChecker... ({self.calibration_attempts}/{self.max_attempts})'
            )
            self.publish_status()

            if self.calibration_attempts % 10 == 0:
                self.get_logger().info(self.detection_status.data)

    # ------------------------------------------------------------------
    # Apply model
    # ------------------------------------------------------------------
    def apply_ccm(self, image_bgr):
        """
        应用 OpenCV ColorCorrectionModel 对图像进行颜色校正

        输入:
            image_bgr: uint8, BGR
        输出:
            corrected_bgr: uint8, BGR
        """
        if not self.ccm_enabled or self.ccm_model is None:
            return image_bgr

        try:
            # ColorCorrectionModel 更适合用 RGB 流程
            image_rgb = cv2.cvtColor(image_bgr, cv2.COLOR_BGR2RGB)
            img_float = image_rgb.astype(np.float64) / 255.0
            img_float = np.ascontiguousarray(img_float)

            corrected_rgb = self.ccm_model.infer(img_float)

            corrected_rgb = np.clip(corrected_rgb * 255.0, 0, 255).astype(np.uint8)
            corrected_bgr = cv2.cvtColor(corrected_rgb, cv2.COLOR_RGB2BGR)

            return corrected_bgr

        except Exception as e:
            self.get_logger().error(f'Error applying CCM: {e}')
            traceback.print_exc()
            return image_bgr

    # ------------------------------------------------------------------
    # ROS callbacks
    # ------------------------------------------------------------------
    def image_callback(self, msg: Image):
        """
        处理输入图像
        约定输入为 RGB topic
        内部转成 BGR 给 OpenCV 使用
        输出再转回 RGB
        """
        try:
            # 先按参数声明的编码读取
            if self.input_encoding == 'rgb8':
                cv_image_rgb = self.bridge.imgmsg_to_cv2(msg, 'rgb8')
                cv_image_bgr = cv2.cvtColor(cv_image_rgb, cv2.COLOR_RGB2BGR)
            elif self.input_encoding == 'bgr8':
                cv_image_bgr = self.bridge.imgmsg_to_cv2(msg, 'bgr8')
            else:
                # 尽量兼容 passthrough，但仍建议你明确设置 rgb8 或 bgr8
                cv_image = self.bridge.imgmsg_to_cv2(msg, 'passthrough')
                if msg.encoding.lower() == 'rgb8':
                    cv_image_bgr = cv2.cvtColor(cv_image, cv2.COLOR_RGB2BGR)
                elif msg.encoding.lower() == 'bgr8':
                    cv_image_bgr = cv_image
                else:
                    self.get_logger().error(f'Unsupported image encoding: {msg.encoding}')
                    return

            self.latest_image_bgr = cv_image_bgr.copy()
            self.latest_image_header = msg.header

            # 如果已经完成标定，则做颜色校正
            if self.ccm_enabled and self.ccm_model is not None:
                corrected_bgr = self.apply_ccm(cv_image_bgr)
            else:
                corrected_bgr = cv_image_bgr

            # 根据输出编码发布
            if self.output_encoding == 'rgb8':
                corrected_rgb = cv2.cvtColor(corrected_bgr, cv2.COLOR_BGR2RGB)
                output_msg = self.bridge.cv2_to_imgmsg(corrected_rgb, encoding='rgb8')
            elif self.output_encoding == 'bgr8':
                output_msg = self.bridge.cv2_to_imgmsg(corrected_bgr, encoding='bgr8')
            else:
                self.get_logger().error(f'Unsupported output encoding: {self.output_encoding}')
                return

            output_msg.header = msg.header
            self.image_pub.publish(output_msg)

        except Exception as e:
            self.get_logger().error(f'Error processing image: {e}')
            traceback.print_exc()

    def camera_info_callback(self, msg: CameraInfo):
        """
        转发 CameraInfo
        """
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