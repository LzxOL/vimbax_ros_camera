#!/bin/bash

# Camera 参数设置脚本
# 用法: ./camera_setup.sh <camera_pid> [--pixel_format <format>] [--throughput <value>] [--exposure <value>] [--width <value>] [--height <value>]
# 示例: ./camera_setup.sh 92281
# 示例: ./camera_setup.sh 92281 --pixel_format Mono8 --throughput 450000000 --exposure 750000.0 --width 4512 --height 4512

# 默认值
PIXEL_FORMAT="RGB8"
THROUGHPUT=450000000
EXPOSURE=1000000.0
WIDTH=4512
HEIGHT=4512

# 解析参数
CAMERA_PID=""

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
        *)            CAMERA_PID="$1"
            shift
            ;;
    esac
done

# 检查 camera_pid 是否提供
if [ -z "$CAMERA_PID" ]; then
    echo "错误: 请提供 camera_pid"
    echo "用法: $0 <camera_pid> [--pixel_format <format>] [--throughput <value>] [--exposure <value>] [--width <value>] [--height <value>]"
    exit 1
fi

SERVICE_PREFIX="/vimbax_camera_${CAMERA_PID}/features"

echo "正在设置相机参数 (PID: ${CAMERA_PID})..."
echo "--------------------------------------------"

# 1. 设置 PixelFormat
echo "1. 设置 PixelFormat = ${PIXEL_FORMAT}"
ros2 service call ${SERVICE_PREFIX}/enum_set vimbax_camera_msgs/srv/FeatureEnumSet "{feature_name: 'PixelFormat', value: '${PIXEL_FORMAT}'}"

# 2. 设置 DeviceLinkThroughputLimit
echo "2. 设置 DeviceLinkThroughputLimit = ${THROUGHPUT}"
ros2 service call ${SERVICE_PREFIX}/int_set vimbax_camera_msgs/srv/FeatureIntSet "{feature_name: 'DeviceLinkThroughputLimit', value: ${THROUGHPUT}}"

# 3. 设置 ExposureTime
echo "3. 设置 ExposureTime = ${EXPOSURE}"
ros2 service call ${SERVICE_PREFIX}/float_set vimbax_camera_msgs/srv/FeatureFloatSet "{feature_name: 'ExposureTime', value: ${EXPOSURE}}"

# 4. 设置 Width
echo "4. 设置 Width = ${WIDTH}"
ros2 service call ${SERVICE_PREFIX}/int_set vimbax_camera_msgs/srv/FeatureIntSet "{feature_name: 'Width', value: ${WIDTH}}"

# 5. 设置 Height
echo "5. 设置 Height = ${HEIGHT}"
ros2 service call ${SERVICE_PREFIX}/int_set vimbax_camera_msgs/srv/FeatureIntSet "{feature_name: 'Height', value: ${HEIGHT}}"

echo "--------------------------------------------"
echo "相机参数设置完成!"
