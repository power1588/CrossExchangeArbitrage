#!/usr/bin/env python
# -*- coding: utf-8 -*-

import asyncio
import os
import sys
from loguru import logger

# 添加项目根目录到Python路径
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.core.config import Config
from src.core.exchange import ExchangeManager
from src.core.notifier import NotifierFactory
from src.strategy.spread import SpreadStrategy

# 配置日志
logger.add("logs/crossarb.log", rotation="10 MB", level="INFO")

async def main():
    """主函数"""
    try:
        # 加载配置
        config = Config()
        logger.info("配置加载成功")
        
        # 初始化交易所管理器
        exchange_manager = ExchangeManager(config)
        await exchange_manager.initialize()
        logger.info("交易所初始化成功")
        
        # 初始化通知器
        notifiers = [NotifierFactory.create_notifier(notifier_config) for notifier_config in config.notifiers]
        logger.info(f"通知器初始化成功: {len(notifiers)}个")
        
        # 初始化策略
        strategy = SpreadStrategy(
            exchange_manager=exchange_manager,
            notifiers=notifiers,
            min_spread=config.min_spread,
            check_interval=config.check_interval,
            alert_interval=config.alert_interval,
            periodic_alert_interval=config.periodic_alert_interval
        )
        logger.info("策略初始化成功")
        
        # 启动策略
        await strategy.start()
        
    except Exception as e:
        logger.exception(f"程序运行出错: {e}")
        sys.exit(1)
    finally:
        # 关闭交易所连接
        if 'exchange_manager' in locals():
            await exchange_manager.close()
            logger.info("交易所连接已关闭")

if __name__ == "__main__":
    asyncio.run(main()) 