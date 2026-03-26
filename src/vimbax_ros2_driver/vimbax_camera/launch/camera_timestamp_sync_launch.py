#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
相机时间戳同步 Launch 文件

订阅左右相机图像，自动检测时间戳偏移量，
将右相机图像重发为校正后的图像。

用法:
    ros2 launch vimbax_camera camera_timestamp_sync_launch.py
    ros2 launch vimbax_camera camera_timestamp_sync_launch.py \\
        left_topic:=/vimbax_camera_left/image_raw \\
        right_topic:=/vimbax_camera_right/image_raw \\
        output_topic:=/vimbax_camera_right/image_sync \\
        detect_frames:=30 \\
        converge_thresh:=5.0

参数:
    left_topic:       左相机图像话题 (默认 /vimbax_camera_left/image_raw)
    right_topic:      右相机图像话题 (默认 /vimbax_camera_right/image_raw)
    output_topic:     校正后图像输出话题 (默认 /vimbax_camera_right/image_sync)
    detect_frames:    自动检测所用帧数 (默认 30)
    converge_thresh:  收敛判定阈值，毫秒 (默认 5.0)
    offset_ms:        手动指定偏移量，非 0 时禁用自动检测 (默认 0.0)
"""

from launch import LaunchDescription
from launch.actions import DeclareLaunchArgument
from launch.substitutions import LaunchConfiguration
from launch_ros.actions import Node
import os


def _get_sync_script_path():
    """获取 camera_timestamp_sync.py 的路径"""
    # launch 文件在 install/vimbax_camera/share/vimbax_camera/launch/
    # 脚本安装到 lib/vimbax_camera/
    this_dir = os.path.dirname(os.path.abspath(__file__))
    # 从 .../share/vimbax_camera/launch/ 往上一级取 lib/
    lib_dir = os.path.join(this_dir, '..', '..', 'lib', 'vimbax_camera')
    script = os.path.join(lib_dir, 'vimbax_camera_timestamp_sync')
    return os.path.normpath(script)


def launch_setup(context, *args, **kwargs):
    left_topic     = LaunchConfiguration('left_topic').perform(context)
    right_topic    = LaunchConfiguration('right_topic').perform(context)
    output_topic   = LaunchConfiguration('output_topic').perform(context)
    detect_frames  = LaunchConfiguration('detect_frames').perform(context)
    converge_thresh = LaunchConfiguration('converge_thresh').perform(context)
    offset_ms      = LaunchConfiguration('offset_ms').perform(context)

    sync_node = Node(
        package='vimbax_camera',
        executable='vimbax_camera_timestamp_sync',
        name='camera_timestamp_sync',
        parameters=[{
            'left_topic':       left_topic,
            'right_topic':      right_topic,
            'output_topic':     output_topic,
            'detect_frames':    int(detect_frames),
            'converge_thresh': float(converge_thresh),
            'offset_ms':        float(offset_ms),
        }],
        output='screen',
    )

    return [sync_node]


def generate_launch_description():
    declared_arguments = [
        DeclareLaunchArgument(
            'left_topic',
            default_value='/vimbax_camera_left/image_raw',
            description='Left camera image topic'
        ),
        DeclareLaunchArgument(
            'right_topic',
            default_value='/vimbax_camera_right/image_raw',
            description='Right camera image topic'
        ),
        DeclareLaunchArgument(
            'output_topic',
            default_value='/vimbax_camera_right/image_sync',
            description='Corrected right camera image output topic'
        ),
        DeclareLaunchArgument(
            'detect_frames',
            default_value='30',
            description='Number of frames used for auto offset detection'
        ),
        DeclareLaunchArgument(
            'converge_thresh',
            default_value='5.0',
            description='Convergence threshold in milliseconds'
        ),
        DeclareLaunchArgument(
            'offset_ms',
            default_value='0.0',
            description='Manual offset in ms. Non-zero disables auto-detection.'
        ),
    ]

    from launch import LaunchDescription
    from launch.actions import OpaqueFunction
    return LaunchDescription(declared_arguments + [OpaqueFunction(function=launch_setup)])
