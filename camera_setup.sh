#!/bin/bash

# Camera 参数设置脚本
# 用法: ./camera_setup.sh <camera_pid> [--pixel_format <format>] [--throughput <value>] [--exposure <value>] [--width <value>] [--height <value>] [--color_transform_enable <0|1>] [--ccm <r0c0,r0c1,r0c2,r1c0,r1c1,r1c2,r2c0,r2c1,r2c2>]
# 示例: ./camera_setup.sh 92281
# 示例: ./camera_setup.sh 92281 --pixel_format RGB8 --throughput 450000000 --exposure 750000.0 --width 4512 --height 4512
# 示例: ./camera_setup.sh 92281 --color_transform_enable 1

# 默认值
PIXEL_FORMAT="RGB8"
THROUGHPUT=450000000
EXPOSURE=600000.0
WIDTH=4512
HEIGHT=4512
COLOR_TRANSFORM_ENABLE=0

# 默认 CCM 矩阵值 (从 ColorChecker 标定得到的值)
# ColorTransformationValue 的 Gain00-Gain22 索引对应:
# Gain00=Gain[0], Gain01=Gain[1], Gain02=Gain[2]
# Gain10=Gain[3], Gain11=Gain[4], Gain12=Gain[5]
# Gain20=Gain[6], Gain21=Gain[7], Gain22=Gain[8]
CCM_MATRIX="0.57124758,-0.03391772,0.028312,-0.16821853,0.41293778,-0.12434534,0.22085547,0.11828595,0.48033197"

# 测试用：转置的 CCM 矩阵 (如果原矩阵偏黄，尝试这个)
# CCM_MATRIX="0.94537408,0.0017535,0.01985025,-0.08646678,0.82378604,-0.00229384,0.03070993,-0.05018676,0.56943145"

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
        --color_transform_enable)
            COLOR_TRANSFORM_ENABLE="$2"
            shift 2
            ;;
        --ccm)
            CCM_MATRIX="$2"
            shift 2
            ;;
        *)
            CAMERA_PID="$1"
            shift
            ;;
    esac
done

# 检查 camera_pid 是否提供
if [ -z "$CAMERA_PID" ]; then
    echo "错误: 请提供 camera_pid"
    echo "用法: $0 <camera_pid> [--pixel_format <format>] [--throughput <value>] [--exposure <value>] [--width <value>] [--height <value>] [--color_transform_enable <0|1>] [--ccm <r0c0,r0c1,r0c2,r1c0,r1c1,r1c2,r2c0,r2c1,r2c2>]"
    exit 1
fi

SERVICE_PREFIX="/vimbax_camera_${CAMERA_PID}/features"

echo "正在设置相机参数 (PID: ${CAMERA_PID})..."
echo "--------------------------------------------"

# 1. 设置 PixelFormat
echo "1. 设置 PixelFormat = ${PIXEL_FORMAT}"
ros2 service call ${SERVICE_PREFIX}/enum_set vimbax_camera_msgs/srv/FeatureEnumSet "{feature_name: 'PixelFormat', feature_module: {id: 0}, value: '${PIXEL_FORMAT}'}"

# 2. 设置 DeviceLinkThroughputLimit
echo "2. 设置 DeviceLinkThroughputLimit = ${THROUGHPUT}"
ros2 service call ${SERVICE_PREFIX}/int_set vimbax_camera_msgs/srv/FeatureIntSet "{feature_name: 'DeviceLinkThroughputLimit', feature_module: {id: 0}, value: ${THROUGHPUT}}"

# 3. 设置 ExposureTime
echo "3. 设置 ExposureTime = ${EXPOSURE}"
ros2 service call ${SERVICE_PREFIX}/float_set vimbax_camera_msgs/srv/FeatureFloatSet "{feature_name: 'ExposureTime', feature_module: {id: 0}, value: ${EXPOSURE}}"

# 4. 设置 Width
echo "4. 设置 Width = ${WIDTH}"
ros2 service call ${SERVICE_PREFIX}/int_set vimbax_camera_msgs/srv/FeatureIntSet "{feature_name: 'Width', feature_module: {id: 0}, value: ${WIDTH}}"

# 5. 设置 Height
echo "5. 设置 Height = ${HEIGHT}"
ros2 service call ${SERVICE_PREFIX}/int_set vimbax_camera_msgs/srv/FeatureIntSet "{feature_name: 'Height', feature_module: {id: 0}, value: ${HEIGHT}}"

# 6. 设置 ColorTransformation (CCM 矩阵)
# 需要先设置 ColorTransformationValueSelector，再设置 ColorTransformationValue
echo "6. 设置 ColorTransformationValue (CCM 矩阵)"
IFS=',' read -ra CCM_VALUES <<< "$CCM_MATRIX"

# 设置 Gain00
ros2 service call ${SERVICE_PREFIX}/enum_set vimbax_camera_msgs/srv/FeatureEnumSet "{feature_name: 'ColorTransformationValueSelector', feature_module: {id: 0}, value: 'Gain00'}"
ros2 service call ${SERVICE_PREFIX}/float_set vimbax_camera_msgs/srv/FeatureFloatSet "{feature_name: 'ColorTransformationValue', feature_module: {id: 0}, value: ${CCM_VALUES[0]}}"

# 设置 Gain01
ros2 service call ${SERVICE_PREFIX}/enum_set vimbax_camera_msgs/srv/FeatureEnumSet "{feature_name: 'ColorTransformationValueSelector', feature_module: {id: 0}, value: 'Gain01'}"
ros2 service call ${SERVICE_PREFIX}/float_set vimbax_camera_msgs/srv/FeatureFloatSet "{feature_name: 'ColorTransformationValue', feature_module: {id: 0}, value: ${CCM_VALUES[1]}}"

# 设置 Gain02
ros2 service call ${SERVICE_PREFIX}/enum_set vimbax_camera_msgs/srv/FeatureEnumSet "{feature_name: 'ColorTransformationValueSelector', feature_module: {id: 0}, value: 'Gain02'}"
ros2 service call ${SERVICE_PREFIX}/float_set vimbax_camera_msgs/srv/FeatureFloatSet "{feature_name: 'ColorTransformationValue', feature_module: {id: 0}, value: ${CCM_VALUES[2]}}"

# 设置 Gain10
ros2 service call ${SERVICE_PREFIX}/enum_set vimbax_camera_msgs/srv/FeatureEnumSet "{feature_name: 'ColorTransformationValueSelector', feature_module: {id: 0}, value: 'Gain10'}"
ros2 service call ${SERVICE_PREFIX}/float_set vimbax_camera_msgs/srv/FeatureFloatSet "{feature_name: 'ColorTransformationValue', feature_module: {id: 0}, value: ${CCM_VALUES[3]}}"

# 设置 Gain11
ros2 service call ${SERVICE_PREFIX}/enum_set vimbax_camera_msgs/srv/FeatureEnumSet "{feature_name: 'ColorTransformationValueSelector', feature_module: {id: 0}, value: 'Gain11'}"
ros2 service call ${SERVICE_PREFIX}/float_set vimbax_camera_msgs/srv/FeatureFloatSet "{feature_name: 'ColorTransformationValue', feature_module: {id: 0}, value: ${CCM_VALUES[4]}}"

# 设置 Gain12
ros2 service call ${SERVICE_PREFIX}/enum_set vimbax_camera_msgs/srv/FeatureEnumSet "{feature_name: 'ColorTransformationValueSelector', feature_module: {id: 0}, value: 'Gain12'}"
ros2 service call ${SERVICE_PREFIX}/float_set vimbax_camera_msgs/srv/FeatureFloatSet "{feature_name: 'ColorTransformationValue', feature_module: {id: 0}, value: ${CCM_VALUES[5]}}"

# 设置 Gain20
ros2 service call ${SERVICE_PREFIX}/enum_set vimbax_camera_msgs/srv/FeatureEnumSet "{feature_name: 'ColorTransformationValueSelector', feature_module: {id: 0}, value: 'Gain20'}"
ros2 service call ${SERVICE_PREFIX}/float_set vimbax_camera_msgs/srv/FeatureFloatSet "{feature_name: 'ColorTransformationValue', feature_module: {id: 0}, value: ${CCM_VALUES[6]}}"

# 设置 Gain21
ros2 service call ${SERVICE_PREFIX}/enum_set vimbax_camera_msgs/srv/FeatureEnumSet "{feature_name: 'ColorTransformationValueSelector', feature_module: {id: 0}, value: 'Gain21'}"
ros2 service call ${SERVICE_PREFIX}/float_set vimbax_camera_msgs/srv/FeatureFloatSet "{feature_name: 'ColorTransformationValue', feature_module: {id: 0}, value: ${CCM_VALUES[7]}}"

# 设置 Gain22
ros2 service call ${SERVICE_PREFIX}/enum_set vimbax_camera_msgs/srv/FeatureEnumSet "{feature_name: 'ColorTransformationValueSelector', feature_module: {id: 0}, value: 'Gain22'}"
ros2 service call ${SERVICE_PREFIX}/float_set vimbax_camera_msgs/srv/FeatureFloatSet "{feature_name: 'ColorTransformationValue', feature_module: {id: 0}, value: ${CCM_VALUES[8]}}"

echo "   CCM 矩阵: [${CCM_VALUES[0]}, ${CCM_VALUES[1]}, ${CCM_VALUES[2]}]"
echo "            [${CCM_VALUES[3]}, ${CCM_VALUES[4]}, ${CCM_VALUES[5]}]"
echo "            [${CCM_VALUES[6]}, ${CCM_VALUES[7]}, ${CCM_VALUES[8]}]"

# 7. 启用/禁用 ColorTransformation
echo "7. 设置 ColorTransformationEnable = ${COLOR_TRANSFORM_ENABLE}"
ros2 service call ${SERVICE_PREFIX}/bool_set vimbax_camera_msgs/srv/FeatureBoolSet "{feature_name: 'ColorTransformationEnable', feature_module: {id: 0}, value: ${COLOR_TRANSFORM_ENABLE}}"

echo "--------------------------------------------"
echo "相机参数设置完成!"
