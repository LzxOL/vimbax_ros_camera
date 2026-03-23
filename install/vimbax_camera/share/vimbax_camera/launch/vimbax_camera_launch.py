# Copyright (c) 2024 Allied Vision Technologies GmbH. All rights reserved.

from launch import LaunchDescription
from launch_ros.actions import Node


def generate_launch_description():
    return LaunchDescription([
        Node(
            package='vimbax_camera',
            namespace='vimbax_camera',
            executable='vimbax_camera_node',
            name='vimbax_camera_node',
            parameters=[{
                # 相机ID（可选，不指定则自动选择第一个相机）
                # "camera_id": "DEV_1AB22C049FF1",
                
                # 自动开始/停止流
                "autostream": 1,
                
                # 相机参数配置文件（启动时自动加载）
                "settings_file": "/home/root1/lzx_ws/project/vimbax_ros_camera/config/camera_settings.xml",
            }],
            output='screen',
        )
    ])
