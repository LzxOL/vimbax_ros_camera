#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
VimbaX Camera Launch 文件 - 支持运行时参数配置

用法:
    ros2 launch vimbax_camera vimbax_camera_param_launch.py camera_id:=12345

参数:
    camera_id: 相机ID (如 92281)
    pixel_format: 像素格式 (默认 RGB8)
    throughput: 设备链路吞吐量限制 (默认 450000000)
    exposure: 曝光时间，微秒 (默认 600000.0)
    width: 图像宽度 (默认 4512)
    height: 图像高度 (默认 4512)
    settings_file: 相机配置文件路径

示例:
    ros2 launch vimbax_camera vimbax_camera_param_launch.py camera_id:=92281
    ros2 launch vimbax_camera vimbax_camera_param_launch.py camera_id:=92281 pixel_format:=BayerRG8 exposure:=750000.0
"""

from launch import LaunchDescription
from launch.actions import DeclareLaunchArgument, TimerAction, ExecuteProcess, OpaqueFunction
from launch.substitutions import LaunchConfiguration
from launch_ros.actions import Node


def launch_setup(context, *args, **kwargs):
    # 获取参数值
    camera_id = LaunchConfiguration('camera_id').perform(context)
    pixel_format = LaunchConfiguration('pixel_format').perform(context)
    throughput = LaunchConfiguration('device_throughput_limit').perform(context)
    exposure = LaunchConfiguration('exposure_time').perform(context)
    width = LaunchConfiguration('width').perform(context)
    height = LaunchConfiguration('height').perform(context)
    settings_file = LaunchConfiguration('settings_file').perform(context)
    autostream = LaunchConfiguration('autostream').perform(context)

    # 根据 camera_id 确定 namespace
    if camera_id:
        namespace = f'vimbax_camera_{camera_id}'
        service_prefix = f'/vimbax_camera_{camera_id}/features'
    else:
        namespace = 'vimbax_camera'
        service_prefix = '/vimbax_camera/features'

    # 相机节点
    vimbax_camera_node = Node(
        package='vimbax_camera',
        executable='vimbax_camera_node',
        name='vimbax_camera_node',
        namespace=namespace,
        parameters=[{
            'autostream': int(autostream),
            'settings_file': settings_file,
        }],
        output='screen',
    )

    # 1. 设置 PixelFormat (在相机启动 3 秒后执行)
    set_pixel_format = ExecuteProcess(
        cmd=[
            'ros2', 'service', 'call',
            f'{service_prefix}/enum_set',
            'vimbax_camera_msgs/srv/FeatureEnumSet',
            f'{{feature_name: PixelFormat, feature_module: {{id: 0}}, value: \'{pixel_format}\'}}'
        ],
        shell=False,
        output='screen'
    )

    # 2. 设置 DeviceLinkThroughputLimit (在相机启动 4 秒后执行)
    set_throughput = ExecuteProcess(
        cmd=[
            'ros2', 'service', 'call',
            f'{service_prefix}/int_set',
            'vimbax_camera_msgs/srv/FeatureIntSet',
            f'{{feature_name: DeviceLinkThroughputLimit, feature_module: {{id: 0}}, value: {throughput}}}'
        ],
        shell=False,
        output='screen'
    )

    # 3. 设置 ExposureTime (在相机启动 5 秒后执行)
    set_exposure = ExecuteProcess(
        cmd=[
            'ros2', 'service', 'call',
            f'{service_prefix}/float_set',
            'vimbax_camera_msgs/srv/FeatureFloatSet',
            f'{{feature_name: ExposureTime, feature_module: {{id: 0}}, value: {exposure}}}'
        ],
        shell=False,
        output='screen'
    )

    # 4. 设置 Width (在相机启动 6 秒后执行)
    set_width = ExecuteProcess(
        cmd=[
            'ros2', 'service', 'call',
            f'{service_prefix}/int_set',
            'vimbax_camera_msgs/srv/FeatureIntSet',
            f'{{feature_name: Width, feature_module: {{id: 0}}, value: {width}}}'
        ],
        shell=False,
        output='screen'
    )

    # 5. 设置 Height (在相机启动 7 秒后执行)
    set_height = ExecuteProcess(
        cmd=[
            'ros2', 'service', 'call',
            f'{service_prefix}/int_set',
            'vimbax_camera_msgs/srv/FeatureIntSet',
            f'{{feature_name: Height, feature_module: {{id: 0}}, value: {height}}}'
        ],
        shell=False,
        output='screen'
    )

    return [
        vimbax_camera_node,
        TimerAction(period=3.0, actions=[set_pixel_format]),
        TimerAction(period=4.0, actions=[set_throughput]),
        TimerAction(period=5.0, actions=[set_exposure]),
        TimerAction(period=6.0, actions=[set_width]),
        TimerAction(period=7.0, actions=[set_height]),
    ]


def generate_launch_description():
    # 声明 launch 参数
    declared_arguments = [
        DeclareLaunchArgument(
            'camera_id',
            default_value='',
            description='Camera ID (PID). If empty, will auto-detect first camera.'
        ),
        DeclareLaunchArgument(
            'pixel_format',
            default_value='RGB8',
            description='Pixel format for the camera (e.g., BayerRG8, RGB8, Mono8)'
        ),
        DeclareLaunchArgument(
            'device_throughput_limit',
            default_value='450000000',
            description='Device link throughput limit in bits/s'
        ),
        DeclareLaunchArgument(
            'exposure_time',
            default_value='600000.0',
            description='Exposure time in microseconds'
        ),
        DeclareLaunchArgument(
            'width',
            default_value='4512',
            description='Image width in pixels'
        ),
        DeclareLaunchArgument(
            'height',
            default_value='4512',
            description='Image height in pixels'
        ),
        DeclareLaunchArgument(
            'settings_file',
            default_value='/home/root1/lzx_ws/project/vimbax_ros_camera/config/camera_settings.xml',
            description='Path to camera settings XML file'
        ),
        DeclareLaunchArgument(
            'autostream',
            default_value='1',
            description='Auto start streaming (0: disable, 1: enable)'
        ),
    ]

    return LaunchDescription(declared_arguments + [OpaqueFunction(function=launch_setup)])
