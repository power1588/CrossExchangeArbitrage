import asyncio
import argparse
import logging
from typing import Dict, Any, List
from loguru import logger
import sys
import os
import time

# 添加项目根目录到Python路径
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.core.config import Config
from src.core.exchange import ExchangeManager
from src.core.notifier import NotifierFactory

class SpreadMonitor:
    def __init__(self, config: Config):
        self.config = config
        self.exchange_manager = ExchangeManager(config)
        self.notifiers = [NotifierFactory.create_notifier(notifier_config) for notifier_config in config.notifiers]
        self.running = False
        self.last_alert_time = 0
        self.last_periodic_alert_time = 0
        
    async def initialize(self):
        """初始化监控器"""
        await self.exchange_manager.initialize()
        logger.info("交易所初始化成功")
        
    async def start(self):
        """启动监控"""
        self.running = True
        logger.info("开始监控价差")
        
        while self.running:
            try:
                await self.check_spreads()
                await self.check_periodic_alert()
                await asyncio.sleep(self.config.check_interval)
            except Exception as e:
                logger.error(f"监控循环出错: {e}")
                await asyncio.sleep(5)  # 出错后等待5秒再重试
                
    async def stop(self):
        """停止监控"""
        self.running = False
        await self.exchange_manager.close()
        logger.info("监控已停止")
        
    async def check_spreads(self):
        """检查价差"""
        for symbol in self._get_common_symbols():
            try:
                # 获取所有交易所的BBO信息
                bbo_info = {}
                for exchange in self.config.exchanges:
                    exchange_id = exchange['name']
                    info = await self.exchange_manager.get_bbo_info(exchange_id, symbol)
                    if info['bid'] and info['ask']:
                        bbo_info[exchange_id] = info
                        
                if len(bbo_info) < 2:
                    continue
                    
                # 计算最大价差
                max_spread = 0
                max_spread_exchanges = None
                
                for ex1 in bbo_info:
                    for ex2 in bbo_info:
                        if ex1 >= ex2:
                            continue
                            
                        # 计算价差
                        bid1 = bbo_info[ex1]['bid']
                        ask1 = bbo_info[ex1]['ask']
                        bid2 = bbo_info[ex2]['bid']
                        ask2 = bbo_info[ex2]['ask']
                        
                        # 计算套利空间
                        spread1 = (bid2 - ask1) / ask1 * 100  # 在 ex1 买入，在 ex2 卖出
                        spread2 = (bid1 - ask2) / ask2 * 100  # 在 ex2 买入，在 ex1 卖出
                        
                        if spread1 > max_spread:
                            max_spread = spread1
                            max_spread_exchanges = (ex1, ex2, 'buy', 'sell')
                            
                        if spread2 > max_spread:
                            max_spread = spread2
                            max_spread_exchanges = (ex2, ex1, 'buy', 'sell')
                            
                # 如果价差超过阈值，发送提醒
                if max_spread >= self.config.min_spread:
                    current_time = time.time()
                    if current_time - self.last_alert_time >= self.config.alert_interval:
                        await self._send_spread_alert(symbol, max_spread, bbo_info, max_spread_exchanges)
                        self.last_alert_time = current_time
                        
            except Exception as e:
                logger.error(f"检查 {symbol} 价差时出错: {e}")
                
    async def check_periodic_alert(self):
        """检查是否需要发送定期提醒"""
        current_time = time.time()
        if current_time - self.last_periodic_alert_time >= self.config.periodic_alert_interval:
            await self._send_periodic_alert()
            self.last_periodic_alert_time = current_time
            
    async def _send_spread_alert(self, symbol: str, spread: float, bbo_info: Dict[str, Dict[str, Any]], max_spread_exchanges: tuple):
        """发送价差提醒"""
        if not self.notifiers:
            return
            
        ex1, ex2, action1, action2 = max_spread_exchanges
        
        # 准备价格信息
        prices = {
            ex1: bbo_info[ex1]['bid'] if action1 == 'sell' else bbo_info[ex1]['ask'],
            ex2: bbo_info[ex2]['bid'] if action2 == 'sell' else bbo_info[ex2]['ask']
        }
        
        for notifier in self.notifiers:
            try:
                await notifier.send_spread_alert(symbol, spread, prices)
            except Exception as e:
                logger.error(f"发送价差提醒失败: {e}")
                
    async def _send_periodic_alert(self):
        """发送定期提醒"""
        if not self.notifiers:
            return
            
        # 获取所有交易对的BBO信息
        bbo_info = {}
        for symbol in self._get_common_symbols():
            symbol_info = {}
            for exchange in self.config.exchanges:
                exchange_id = exchange['name']
                try:
                    info = await self.exchange_manager.get_bbo_info(exchange_id, symbol)
                    if info['bid'] and info['ask']:
                        symbol_info[exchange_id] = info
                except Exception as e:
                    logger.error(f"获取 {exchange_id} {symbol} BBO信息时出错: {e}")
                    
            if symbol_info:
                bbo_info[symbol] = symbol_info
                
        if not bbo_info:
            return
            
        for notifier in self.notifiers:
            try:
                await notifier.send_periodic_alert(bbo_info)
            except Exception as e:
                logger.error(f"发送定期提醒失败: {e}")
                
    def _get_common_symbols(self) -> List[str]:
        """获取所有交易所共同的交易对"""
        common_symbols = set()
        first = True
        
        for exchange in self.config.exchanges:
            symbols = set(symbol for symbol in exchange['symbols'] if symbol.endswith('/USDT'))
            if first:
                common_symbols = symbols
                first = False
            else:
                common_symbols &= symbols
                
        return list(common_symbols)

async def main():
    """主函数"""
    parser = argparse.ArgumentParser(description='监控交易所价差')
    parser.add_argument('--config', type=str, default='config.yaml', help='配置文件路径')
    args = parser.parse_args()
    
    try:
        # 加载配置
        config = Config(args.config)
        logger.info("配置加载成功")
        
        # 创建并启动监控器
        monitor = SpreadMonitor(config)
        await monitor.initialize()
        
        try:
            await monitor.start()
        except KeyboardInterrupt:
            logger.info("收到停止信号")
        finally:
            await monitor.stop()
            
    except Exception as e:
        logger.error(f"程序运行出错: {e}")
        sys.exit(1)

if __name__ == "__main__":
    asyncio.run(main()) 