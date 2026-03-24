"""Launch file for high-performance C++ color correction node."""

from launch import LaunchDescription
from launch_ros.actions import Node
from launch.actions import DeclareLaunchArgument
from launch.substitutions import LaunchConfiguration
from os.path import join, expanduser, exists


def generate_launch_description():
    """Generate launch description for color correction node."""

    # Default paths
    default_lut_file = '/home/root1/lzx_ws/project/vimbax_ros_camera/config/color_correction_lut.bin'

    # Launch arguments
    arguments = [
        DeclareLaunchArgument(
            'input_topic',
            default_value='/vimbax_camera/image_raw',
            description='Input image topic'
        ),
        DeclareLaunchArgument(
            'output_topic',
            default_value='/color_corrected/image_raw',
            description='Output image topic'
        ),
        DeclareLaunchArgument(
            'camera_info_topic',
            default_value='/vimbax_camera/camera_info',
            description='Input camera info topic'
        ),
        DeclareLaunchArgument(
            'output_camera_info_topic',
            default_value='/color_corrected/camera_info',
            description='Output camera info topic'
        ),
        DeclareLaunchArgument(
            'input_encoding',
            default_value='rgb8',
            description='Input image encoding (rgb8 or bgr8)'
        ),
        DeclareLaunchArgument(
            'output_encoding',
            default_value='rgb8',
            description='Output image encoding (rgb8 or bgr8)'
        ),
        DeclareLaunchArgument(
            'lut_file',
            default_value=default_lut_file,
            description='Path to LUT file (.bin or .npy)'
        ),
        DeclareLaunchArgument(
            'lut_size',
            default_value='33',
            description='LUT dimension size (typically 17, 33, or 65)'
        ),
        DeclareLaunchArgument(
            'num_threads',
            default_value='0',
            description='Number of threads for parallel processing (0 = auto)'
        ),
        DeclareLaunchArgument(
            'enable_color_correction',
            default_value='true',
            description='Enable color correction'
        ),
        DeclareLaunchArgument(
            'verbose',
            default_value='false',
            description='Enable verbose logging'
        ),
    ]

    # Node configuration
    node_config = {
        'package': 'vimbax_camera_color_correction_cpp',
        'executable': 'color_correction_cpp_node',
        'name': 'color_correction_cpp_node',
        'output': 'screen',
        'parameters': [{
            'input_topic': LaunchConfiguration('input_topic'),
            'output_topic': LaunchConfiguration('output_topic'),
            'camera_info_topic': LaunchConfiguration('camera_info_topic'),
            'output_camera_info_topic': LaunchConfiguration('output_camera_info_topic'),
            'input_encoding': LaunchConfiguration('input_encoding'),
            'output_encoding': LaunchConfiguration('output_encoding'),
            'lut_file': LaunchConfiguration('lut_file'),
            'lut_size': LaunchConfiguration('lut_size'),
            'num_threads': LaunchConfiguration('num_threads'),
            'enable_color_correction': LaunchConfiguration('enable_color_correction'),
            'verbose': LaunchConfiguration('verbose'),
        }],
        'remappings': [],
    }

    return LaunchDescription(arguments + [Node(**node_config)])
