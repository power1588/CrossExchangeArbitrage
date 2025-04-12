# CrossArb - 跨交易所套利监控工具

CrossArb是一个用于监控多个交易所之间价格差异的自动化工具，支持实时价差监控、定期播报和自动交易功能。

## 功能特点

- **多交易所支持**：支持Binance、OKX、Gate、HTX等主流交易所
- **灵活的模式切换**：支持public模式（仅获取公开行情）和private模式（支持交易）
- **实时价差监控**：监控指定交易对在不同交易所之间的价差
- **定期播报**：定期发送各交易所的BBO（最佳买卖价）信息
- **多种通知方式**：支持飞书和Telegram通知
- **自动交易**：在private模式下支持自动执行套利交易

## 安装

1. 克隆仓库：
```bash
git clone https://github.com/yourusername/CrossArb.git
cd CrossArb
```

2. 安装依赖：
```bash
pip install -r requirements.txt
```

3. 配置：
复制`config.yaml.example`为`config.yaml`，并根据需要修改配置：
```bash
cp config.yaml.example config.yaml
```

## 配置说明

配置文件`config.yaml`包含以下主要部分：

### 交易所配置
```yaml
exchanges:
  - name: binance
    type: binance
    mode: public  # 可选值: public(仅获取公开行情), private(支持交易)
    api_key: your_api_key_here  # 仅在 mode=private 时需要
    api_secret: your_api_secret_here  # 仅在 mode=private 时需要
    testnet: false
    symbols:
      - ORCA/USDT
      - BTC/USDT
      - ETH/USDT
```

### 通知器配置
```yaml
notifiers:
  - type: lark
    webhook_url: your_webhook_url_here
  
  - type: telegram
    bot_token: your_bot_token_here
    chat_id: your_chat_id_here
```

### 策略参数
```yaml
min_spread: 0.5  # 最小价差阈值（百分比）
check_interval: 60  # 检查间隔（秒）
alert_interval: 300  # 提醒间隔（秒）
periodic_alert_interval: 3600  # 定时播报间隔（秒）
```

## 使用方法

1. 启动监控：
```bash
python src/main.py
```

2. 查看日志：
```bash
tail -f logs/crossarb.log
```

## 项目结构

```
CrossArb/
├── config.yaml.example  # 配置文件示例
├── requirements.txt     # 依赖包列表
├── src/                 # 源代码
│   ├── core/            # 核心功能
│   │   ├── config.py    # 配置管理
│   │   ├── exchange.py  # 交易所管理
│   │   └── notifier.py  # 通知管理
│   ├── strategy/        # 策略实现
│   │   └── spread.py    # 价差策略
│   └── main.py          # 主程序入口
└── logs/                # 日志目录
```

## 版本历史

- v1.0: 初始版本，支持多交易所价差监控和通知功能

## 许可证

MIT 