#!/bin/bash

# Dual Camera 参数设置与启动脚本
# 用法: ./dual_camera_setup.sh [--pixel_format <format>] [--throughput <value>] [--exposure <value>] [--width <value>] [--height <value>] [--left_serial <serial>] [--right_serial <serial>] [--left_topic <topic>] [--right_topic <topic>]
# 示例: ./dual_camera_setup.sh
# 示例: ./dual_camera_setup.sh --pixel_format Mono8 --throughput 450000000 --exposure 600000.0 --width 4512 --height 4512
# 示例: ./dual_camera_setup.sh --left_serial 03R47 --right_serial 06HV5 --left_topic vimbax_camera_left --right_topic vimbax_camera_right
#
# 时间戳同步（请另行启动）:
#   ros2 launch vimbax_camera camera_timestamp_sync_launch.py
# 或 ./camera_timestamp_sync.sh

# 默认值
PIXEL_FORMAT="Mono8"
THROUGHPUT=450000000
EXPOSURE=600000.0
WIDTH=4512
HEIGHT=4512
LEFT_SERIAL="03R47"
RIGHT_SERIAL="06HV5"
LEFT_TOPIC="vimbax_camera_left"
RIGHT_TOPIC="vimbax_camera_right"

# ROS 工作空间路径
ROS_WS="/home/root1/lzx_ws/project/vimbax_ros_camera"

# 解析参数
while [[ $# -gt 0 ]]; do
    case $1 in
        --pixel_format)
            PIXEL_FORMAT="$2"
            shift 2
            ;;
        --throughput)
            THROUGHPUT="$2"
            shift 2
            ;;
        --exposure)
            EXPOSURE="$2"
            shift 2
            ;;
        --width)
            WIDTH="$2"
            shift 2
            ;;
        --height)
            HEIGHT="$2"
            shift 2
            ;;
        --left_serial)
            LEFT_SERIAL="$2"
            shift 2
            ;;
        --right_serial)
            RIGHT_SERIAL="$2"
            shift 2
            ;;
        --left_topic)
            LEFT_TOPIC="$2"
            shift 2
            ;;
        --right_topic)
            RIGHT_TOPIC="$2"
            shift 2
            ;;
        *)
            echo "未知参数: $1"
            shift
            ;;
    esac
done

# 检查是否需要 source ROS 环境
if [ -z "$ROS_DISTRO" ]; then
    echo "[dual_camera_setup] 正在 source ROS 环境..."
    source /opt/ros/humble/setup.bash
    source "${ROS_WS}/install/setup.bash"
fi

echo "============================================"
echo "Dual Camera 启动与参数设置"
echo "============================================"
echo "左相机序列号: ${LEFT_SERIAL}"
echo "右相机序列号: ${RIGHT_SERIAL}"
echo "左相机 Topic: ${LEFT_TOPIC}"
echo "右相机 Topic: ${RIGHT_TOPIC}"
echo "像素格式: ${PIXEL_FORMAT}"
echo "吞吐量限制: ${THROUGHPUT}"
echo "曝光时间: ${EXPOSURE}"
echo "图像分辨率: ${WIDTH} x ${HEIGHT}"
echo "============================================"

# 启动 launch 文件（在前台运行，autostream=0 由脚本手动控制）
echo "[1/2] 正在启动 Dual Camera Launch..."
ros2 launch vimbax_camera dual_camera_stream_launch.py \
    left_serial:=${LEFT_SERIAL} \
    right_serial:=${RIGHT_SERIAL} \
    left_topic:=${LEFT_TOPIC} \
    right_topic:=${RIGHT_TOPIC} \
    pixel_format:=${PIXEL_FORMAT} \
    device_throughput_limit:=${THROUGHPUT} \
    exposure_time:=${EXPOSURE} \
    width:=${WIDTH} \
    height:=${HEIGHT} \
    autostream:=0 &

LAUNCH_PID=$!
echo "[dual_camera_setup] Launch 进程 PID: ${LAUNCH_PID}"

# 等待 launch 文件中所有参数设置完成
# launch 文件时间线: t=0启动, t=1.5停流, t=1.8停采集, t=3.0-3.8设参, t=4.5开流(autostream=0时不执行)
# 需要等 launch 全部完成后再操作，这里等待 8 秒
echo "[2/2] 等待相机节点初始化和参数设置完成..."
sleep 8

echo ""
echo "============================================"
echo "相机参数设置"
echo "============================================"

# 左相机参数设置
LEFT_NS="${LEFT_TOPIC}"
LEFT_FEATURES="/${LEFT_NS}/features"

echo "--- 设置左相机 (${LEFT_SERIAL}) ---"

# 先强制停止推流和采集，确保可以修改只能在停采时修改的参数
echo "  [0] 停止推流和采集..."
ros2 service call ${LEFT_FEATURES}/command_run vimbax_camera_msgs/srv/FeatureCommandRun \
    "{feature_name: 'AcquisitionStop', feature_module: {id: 0}}" 2>/dev/null
sleep 0.3
ros2 service call /${LEFT_NS}/stream_stop vimbax_camera_msgs/srv/StreamStartStop "{}" 2>/dev/null
sleep 0.3

echo "  1. 设置 PixelFormat = ${PIXEL_FORMAT}"
ros2 service call ${LEFT_FEATURES}/enum_set vimbax_camera_msgs/srv/FeatureEnumSet \
    "{feature_name: 'PixelFormat', feature_module: {id: 0}, value: '${PIXEL_FORMAT}'}" 2>/dev/null

echo "  2. 设置 DeviceLinkThroughputLimit = ${THROUGHPUT}"
ros2 service call ${LEFT_FEATURES}/int_set vimbax_camera_msgs/srv/FeatureIntSet \
    "{feature_name: 'DeviceLinkThroughputLimit', feature_module: {id: 0}, value: ${THROUGHPUT}}" 2>/dev/null

echo "  3. 设置 ExposureTime = ${EXPOSURE}"
ros2 service call ${LEFT_FEATURES}/float_set vimbax_camera_msgs/srv/FeatureFloatSet \
    "{feature_name: 'ExposureTime', feature_module: {id: 0}, value: ${EXPOSURE}}" 2>/dev/null

echo "  4. 设置 Width = ${WIDTH}"
ros2 service call ${LEFT_FEATURES}/int_set vimbax_camera_msgs/srv/FeatureIntSet \
    "{feature_name: 'Width', feature_module: {id: 0}, value: ${WIDTH}}" 2>/dev/null

echo "  5. 设置 Height = ${HEIGHT}"
ros2 service call ${LEFT_FEATURES}/int_set vimbax_camera_msgs/srv/FeatureIntSet \
    "{feature_name: 'Height', feature_module: {id: 0}, value: ${HEIGHT}}" 2>/dev/null

echo "  [6] 重新启动推流..."
sleep 0.3
ros2 service call /${LEFT_NS}/stream_start vimbax_camera_msgs/srv/StreamStartStop "{}" 2>/dev/null

echo ""

# 右相机参数设置
RIGHT_NS="${RIGHT_TOPIC}"
RIGHT_FEATURES="/${RIGHT_NS}/features"

echo "--- 设置右相机 (${RIGHT_SERIAL}) ---"

# 先强制停止推流和采集，确保可以修改只能在停采时修改的参数
echo "  [0] 停止推流和采集..."
ros2 service call ${RIGHT_FEATURES}/command_run vimbax_camera_msgs/srv/FeatureCommandRun \
    "{feature_name: 'AcquisitionStop', feature_module: {id: 0}}" 2>/dev/null
sleep 0.3
ros2 service call /${RIGHT_NS}/stream_stop vimbax_camera_msgs/srv/StreamStartStop "{}" 2>/dev/null
sleep 0.3

echo "  1. 设置 PixelFormat = ${PIXEL_FORMAT}"
ros2 service call ${RIGHT_FEATURES}/enum_set vimbax_camera_msgs/srv/FeatureEnumSet \
    "{feature_name: 'PixelFormat', feature_module: {id: 0}, value: '${PIXEL_FORMAT}'}" 2>/dev/null

echo "  2. 设置 DeviceLinkThroughputLimit = ${THROUGHPUT}"
ros2 service call ${RIGHT_FEATURES}/int_set vimbax_camera_msgs/srv/FeatureIntSet \
    "{feature_name: 'DeviceLinkThroughputLimit', feature_module: {id: 0}, value: ${THROUGHPUT}}" 2>/dev/null

echo "  3. 设置 ExposureTime = ${EXPOSURE}"
ros2 service call ${RIGHT_FEATURES}/float_set vimbax_camera_msgs/srv/FeatureFloatSet \
    "{feature_name: 'ExposureTime', feature_module: {id: 0}, value: ${EXPOSURE}}" 2>/dev/null

echo "  4. 设置 Width = ${WIDTH}"
ros2 service call ${RIGHT_FEATURES}/int_set vimbax_camera_msgs/srv/FeatureIntSet \
    "{feature_name: 'Width', feature_module: {id: 0}, value: ${WIDTH}}" 2>/dev/null

echo "  5. 设置 Height = ${HEIGHT}"
ros2 service call ${RIGHT_FEATURES}/int_set vimbax_camera_msgs/srv/FeatureIntSet \
    "{feature_name: 'Height', feature_module: {id: 0}, value: ${HEIGHT}}" 2>/dev/null

echo "  [6] 重新启动推流..."
sleep 0.3
ros2 service call /${RIGHT_NS}/stream_start vimbax_camera_msgs/srv/StreamStartStop "{}" 2>/dev/null

echo ""
echo "============================================"
echo "左相机 topic: /${LEFT_NS}/image_raw"
echo "左相机 camera_info: /${LEFT_NS}/camera_info"
echo "右相机 topic: /${RIGHT_NS}/image_raw"
echo "右相机 camera_info: /${RIGHT_NS}/camera_info"
echo "============================================"

# 重置左右相机时间戳，使帧时间戳从零点开始，便于后续同步对比
echo "[*] 重置相机时间戳 (TimestampReset)..."
ros2 service call /${LEFT_NS}/features/command_run vimbax_camera_msgs/srv/FeatureCommandRun \
    "{feature_name: 'TimestampReset', feature_module: {id: 0}}" & \
ros2 service call /${RIGHT_NS}/features/command_run vimbax_camera_msgs/srv/FeatureCommandRun \
    "{feature_name: 'TimestampReset', feature_module: {id: 0}}" & \
wait
echo "Launch 进程仍在后台运行 (PID: ${LAUNCH_PID})"
echo "按 Ctrl+C 终止所有相机节点"
echo ""
echo "注意: 如需时间戳同步，请另开终端运行:"
echo "  ./camera_timestamp_sync.sh"
echo "或: ros2 launch vimbax_camera camera_timestamp_sync_launch.py"
echo "============================================"

# 等待后台 launch 进程结束（前台 Ctrl+C 时关闭）
wait ${LAUNCH_PID}
