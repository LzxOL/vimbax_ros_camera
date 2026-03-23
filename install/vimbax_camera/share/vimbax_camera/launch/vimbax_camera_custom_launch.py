# Copyright (c) 2024 Allied Vision Technologies GmbH. All rights reserved.

from launch import LaunchDescription
from launch_ros.actions import Node
from launch.actions import DeclareLaunchArgument, TimerAction, ExecuteProcess
from launch.substitutions import LaunchConfiguration
import os


def generate_launch_description():
    # 声明 launch 参数
    declare_throughput_arg = DeclareLaunchArgument(
        'device_throughput_limit',
        default_value='450000000',
        description='Device link throughput limit in bits/s'
    )

    declare_exposure_arg = DeclareLaunchArgument(
        'exposure_time',
        default_value='750000.0',
        description='Exposure time in microseconds'
    )

    declare_width_arg = DeclareLaunchArgument(
        'width',
        default_value='4512',
        description='Image width in pixels'
    )

    declare_height_arg = DeclareLaunchArgument(
        'height',
        default_value='4512',
        description='Image height in pixels'
    )

    declare_pixel_format_arg = DeclareLaunchArgument(
        'pixel_format',
        default_value='Mono8',
        description='Pixel format for the camera (e.g., BayerRG8, RGB8)'
    )

    # 获取参数值
    pixel_format = LaunchConfiguration('pixel_format')
    throughput = LaunchConfiguration('device_throughput_limit')
    exposure = LaunchConfiguration('exposure_time')
    width = LaunchConfiguration('width')
    height = LaunchConfiguration('height')

    # 自定义配置文件路径
    config_dir = os.path.join(
        os.path.dirname(os.path.abspath(__file__)),
        '..', 'config'
    )
    custom_settings_path = os.path.join(config_dir, 'camera_settings_custom.xml')

    # 相机节点
    vimbax_camera_node = Node(
        package='vimbax_camera',
        namespace='vimbax_camera',
        executable='vimbax_camera_node',
        name='vimbax_camera_node',
        parameters=[{
            'autostream': 1,
            'settings_file': custom_settings_path,
        }],
        output='screen',
    )

    # 1. 设置 PixelFormat (在相机启动3秒后执行)
    set_pixel_format = ExecuteProcess(
        cmd=['ros2', 'service', 'call',
             '/vimbax_camera/features/enum_set',
             'vimbax_camera_msgs/srv/FeatureEnumSet',
             '{feature_name: PixelFormat, value: ' + pixel_format + '}'],
        shell=False,
        output='screen'
    )

    # 2. 设置 DeviceLinkThroughputLimit (在相机启动4秒后执行)
    set_throughput = ExecuteProcess(
        cmd=['ros2', 'service', 'call',
             '/vimbax_camera/features/int_set',
             'vimbax_camera_msgs/srv/FeatureIntSet',
             '{feature_name: DeviceLinkThroughputLimit, value: ' + throughput + '}'],
        shell=False,
        output='screen'
    )

    # 3. 设置 ExposureTime (在相机启动5秒后执行)
    set_exposure = ExecuteProcess(
        cmd=['ros2', 'service', 'call',
             '/vimbax_camera/features/float_set',
             'vimbax_camera_msgs/srv/FeatureFloatSet',
             '{feature_name: ExposureTime, value: ' + exposure + '}'],
        shell=False,
        output='screen'
    )

    # 4. 设置 Width (在相机启动6秒后执行)
    set_width = ExecuteProcess(
        cmd=['ros2', 'service', 'call',
             '/vimbax_camera/features/int_set',
             'vimbax_camera_msgs/srv/FeatureIntSet',
             '{feature_name: Width, value: ' + width + '}'],
        shell=False,
        output='screen'
    )

    # 5. 设置 Height (在相机启动7秒后执行)
    set_height = ExecuteProcess(
        cmd=['ros2', 'service', 'call',
             '/vimbax_camera/features/int_set',
             'vimbax_camera_msgs/srv/FeatureIntSet',
             '{feature_name: Height, value: ' + height + '}'],
        shell=False,
        output='screen'
    )

    return LaunchDescription([
        # 声明参数
        declare_pixel_format_arg,
        declare_throughput_arg,
        declare_exposure_arg,
        declare_width_arg,
        declare_height_arg,

        # 启动相机节点
        vimbax_camera_node,

        # 等待相机初始化后设置参数
        TimerAction(
            period=3.0,
            actions=[set_pixel_format]
        ),
        TimerAction(
            period=4.0,
            actions=[set_throughput]
        ),
        TimerAction(
            period=5.0,
            actions=[set_exposure]
        ),
        TimerAction(
            period=6.0,
            actions=[set_width]
        ),
        TimerAction(
            period=7.0,
            actions=[set_height]
        ),
    ])
