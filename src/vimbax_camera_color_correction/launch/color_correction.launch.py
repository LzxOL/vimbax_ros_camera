from launch import LaunchDescription
from launch_ros.actions import Node
from launch.actions import DeclareLaunchArgument
from launch.substitutions import LaunchConfiguration


def generate_launch_description():
    # 输入图像话题
    input_topic_arg = DeclareLaunchArgument(
        'input_topic',
        default_value='/vimbax_camera/image_raw',
        description='输入图像话题'
    )

    # 输出图像话题
    output_topic_arg = DeclareLaunchArgument(
        'output_topic',
        default_value='/color_corrected/image_raw',
        description='输出图像话题'
    )

    # 相机信息话题
    camera_info_topic_arg = DeclareLaunchArgument(
        'camera_info_topic',
        default_value='/vimbax_camera/camera_info',
        description='相机信息话题'
    )

    # CCM 矩阵文件路径
    ccm_file_arg = DeclareLaunchArgument(
        'ccm_file',
        default_value='',
        description='CCM 矩阵文件路径（JSON格式），如 /path/to/ccm.json'
    )

    # LUT 文件路径
    lut_file_arg = DeclareLaunchArgument(
        'lut_file',
        default_value='/home/root1/lzx_ws/project/vimbax_ros_camera/config/color_correction_lut.npy',
        description='3D LUT .npy 文件路径，标定完成后自动生成并加载'
    )

    # C++ 快速读取的 LUT 二进制文件路径
    lut_binary_file_arg = DeclareLaunchArgument(
        'lut_binary_file',
        default_value='/home/root1/lzx_ws/project/vimbax_ros_camera/config/color_correction_lut.bin',
        description='C++ 快速读取的 LUT 原始二进制文件路径（header + float32 data）'
    )

    # LUT 大小
    lut_size_arg = DeclareLaunchArgument(
        'lut_size',
        default_value='33',
        description='3D LUT 的大小（2 的幂+1），如 17/33/65，越大越精确但越慢'
    )

    # 是否使用 LUT
    use_lut_arg = DeclareLaunchArgument(
        'use_lut',
        default_value='true',
        description='是否使用 LUT 方式进行颜色校正（推荐 true），false 则回退到直接 CCM'
    )

    # 是否自动检测 ColorChecker
    auto_detect_arg = DeclareLaunchArgument(
        'auto_detect_colorchecker',
        default_value='true',
        description='是否自动检测 ColorChecker 并计算 CCM（建议改为false，使用服务手动校准）'
    )

    # 最大校准尝试次数
    max_attempts_arg = DeclareLaunchArgument(
        'max_calibration_attempts',
        default_value='10',
        description='自动校准的最大尝试次数'
    )

    # 是否显示调试图像（仅在有GUI环境时启用）
    show_debug_arg = DeclareLaunchArgument(
        'show_debug_image',
        default_value='false',
        description='是否显示调试图像窗口'
    )

    # 输出图像编码格式
    output_encoding_arg = DeclareLaunchArgument(
        'output_encoding',
        default_value='rgb8',
        description='输出图像编码格式 (rgb8 或 bgr8)'
    )

    return LaunchDescription([
        input_topic_arg,
        output_topic_arg,
        camera_info_topic_arg,
        ccm_file_arg,
        lut_file_arg,
        lut_binary_file_arg,
        lut_size_arg,
        use_lut_arg,
        auto_detect_arg,
        max_attempts_arg,
        show_debug_arg,
        output_encoding_arg,

        Node(
            package='vimbax_camera_color_correction',
            executable='color_correction_node',
            namespace='color_correction',
            name='color_correction_node',
            parameters=[{
                'input_topic': LaunchConfiguration('input_topic'),
                'output_topic': LaunchConfiguration('output_topic'),
                'camera_info_topic': LaunchConfiguration('camera_info_topic'),
                'ccm_file': LaunchConfiguration('ccm_file'),
                'lut_file': LaunchConfiguration('lut_file'),
                'lut_binary_file': LaunchConfiguration('lut_binary_file'),
                'lut_size': LaunchConfiguration('lut_size'),
                'use_lut': LaunchConfiguration('use_lut'),
                'auto_detect_colorchecker': LaunchConfiguration('auto_detect_colorchecker'),
                'max_calibration_attempts': LaunchConfiguration('max_calibration_attempts'),
                'show_debug_image': LaunchConfiguration('show_debug_image'),
                'output_encoding': LaunchConfiguration('output_encoding'),
            }],
            output='screen',
        )
    ])
