# Copyright (c) 2024 User. All rights reserved.

import rclpy
from rclpy.node import Node
from sensor_msgs.msg import Image
from cv_bridge import CvBridge
import cv2
import numpy as np


class CCMApplyNode(Node):
    """
    CCM 矩阵应用节点
    订阅原始图像话题，应用 CCM 矩阵进行颜色校正，并发布校正后的图像
    """

    def __init__(self):
        super().__init__('ccm_apply_node')

        # 默认 CCM 矩阵值 (从相机读取的原始 CCM)
        default_ccm = [
            0.89450421, -0.06810288,  0.03710562,
            0.01028388,  0.78203871, -0.02730229,
           -0.00501290, -0.02470507,  0.50913979
        ]

        # 声明参数
        self.declare_parameter('input_topic', '/vimbax_camera_90333/image_raw')
        self.declare_parameter('output_topic', '/ccm_corrected/image_raw')
        self.declare_parameter('ccm_values', default_ccm)
        self.declare_parameter('enable_debug', False)

        self.input_topic = self.get_parameter('input_topic').get_parameter_value().string_value
        self.output_topic = self.get_parameter('output_topic').get_parameter_value().string_value
        self.ccm_values = self.get_parameter('ccm_values').get_parameter_value().double_array_value
        self.enable_debug = self.get_parameter('enable_debug').get_parameter_value().bool_value

        # 将 CCM 数组转换为 3x3 矩阵
        self.ccm = np.array(self.ccm_values).reshape(3, 3).astype(np.float64)

        self.get_logger().info(f'CCM Apply Node started')
        self.get_logger().info(f'Input topic: {self.input_topic}')
        self.get_logger().info(f'Output topic: {self.output_topic}')
        self.get_logger().info(f'CCM Matrix:\n{self.ccm}')

        self.bridge = CvBridge()

        # 订阅图像话题
        self.image_sub = self.create_subscription(
            Image,
            self.input_topic,
            self.image_callback,
            10
        )

        # 发布校正后的图像
        self.image_pub = self.create_publisher(Image, self.output_topic, 10)

        # 帧计数
        self.frame_count = 0
        self.last_log_time = self.get_clock().now()

    def apply_ccm(self, image):
        """
        应用 CCM 矩阵对图像进行颜色校正
        使用 OpenCV 进行高效的矩阵运算
        """
        try:
            # 转换为 float32 进行计算
            img_float = image.astype(np.float32)

            # 应用 CCM: corrected = img @ CCM.T
            # img shape: (H, W, 3), CCM shape: (3, 3)
            corrected = cv2.transform(img_float, self.ccm.astype(np.float32).T)

            # 裁剪到有效范围 [0, 255]
            corrected = np.clip(corrected, 0, 255).astype(np.uint8)

            return corrected

        except Exception as e:
            self.get_logger().error(f'Error applying CCM: {e}')
            return image

    def image_callback(self, msg):
        """处理收到的图像"""
        try:
            # 转换 ROS 图像到 OpenCV 图像 (BGR 格式)
            cv_image = self.bridge.imgmsg_to_cv2(msg, "bgr8")

            # 应用 CCM 校正
            corrected_image = self.apply_ccm(cv_image)

            # 转换为 ROS 图像并发布
            output_msg = self.bridge.cv2_to_imgmsg(corrected_image, "bgr8")
            output_msg.header = msg.header
            self.image_pub.publish(output_msg)

            # 调试日志
            self.frame_count += 1
            current_time = self.get_clock().now()
            elapsed = (current_time - self.last_log_time).nanoseconds / 1e9

            if elapsed >= 5.0:  # 每 5 秒打印一次
                self.get_logger().info(f'Processed {self.frame_count} frames in {elapsed:.1f}s ({self.frame_count/elapsed:.1f} fps)')
                self.frame_count = 0
                self.last_log_time = current_time

        except Exception as e:
            self.get_logger().error(f'Error processing image: {e}')


def main(args=None):
    rclpy.init(args=args)
    node = CCMApplyNode()

    try:
        rclpy.spin(node)
    except KeyboardInterrupt:
        pass
    finally:
        node.destroy_node()
        rclpy.shutdown()


if __name__ == '__main__':
    main()
