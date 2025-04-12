#!/bin/bash

# 默认配置
SYMBOL="BTC/USDT:USDT"
CONFIG="config/config.yaml"

# 解析命令行参数
while [[ $# -gt 0 ]]; do
  case $1 in
    --symbol)
      SYMBOL="$2"
      shift 2
      ;;
    --config)
      CONFIG="$2"
      shift 2
      ;;
    *)
      echo "未知参数: $1"
      exit 1
      ;;
  esac
done

# 创建日志目录
mkdir -p logs

# 运行监控脚本
echo "开始监控 $SYMBOL 的价差..."
python src/monitor_spread.py --symbol "$SYMBOL" --config "$CONFIG" 