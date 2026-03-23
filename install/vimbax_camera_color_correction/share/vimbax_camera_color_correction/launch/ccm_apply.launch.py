from launch import LaunchDescription
from launch_ros.actions import Node
from launch.actions import DeclareLaunchArgument
from launch.substitutions import LaunchConfiguration


def generate_launch_description():
    # 输入图像话题
    input_topic_arg = DeclareLaunchArgument(
        'input_topic',
        default_value='/vimbax_camera_90333/image_raw',
        description='输入图像话题'
    )

    # 输出图像话题
    output_topic_arg = DeclareLaunchArgument(
        'output_topic',
        default_value='/ccm_corrected/image_raw',
        description='输出图像话题'
    )

    # CCM 矩阵值 (3x3 = 9 个值)
    ccm_values_arg = DeclareLaunchArgument(
        'ccm_values',
        default_value='[0.89450421, -0.06810288, 0.03710562, 0.01028388, 0.78203871, -0.02730229, -0.0050129, -0.02470507, 0.50913979]',
        description='CCM 矩阵值 (9个浮点数，按行展开)'
    )

    # 调试模式
    enable_debug_arg = DeclareLaunchArgument(
        'enable_debug',
        default_value='false',
        description='启用调试日志'
    )

    return LaunchDescription([
        input_topic_arg,
        output_topic_arg,
        ccm_values_arg,
        enable_debug_arg,

        Node(
            package='vimbax_camera_color_correction',
            executable='ccm_apply_node',
            namespace='ccm',
            name='ccm_apply_node',
            parameters=[{
                'input_topic': LaunchConfiguration('input_topic'),
                'output_topic': LaunchConfiguration('output_topic'),
                'ccm_values': LaunchConfiguration('ccm_values'),
                'enable_debug': LaunchConfiguration('enable_debug'),
            }],
            output='screen',
        )
    ])
