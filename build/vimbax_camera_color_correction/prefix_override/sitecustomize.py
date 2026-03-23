import sys
if sys.prefix == '/usr':
    sys.real_prefix = sys.prefix
    sys.prefix = sys.exec_prefix = '/home/root1/lzx_ws/project/vimbax_ros_camera/install/vimbax_camera_color_correction'
