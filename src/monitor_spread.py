import asyncio
import yaml
import os
import argparse
import time
from typing import Dict
from dotenv import load_dotenv
from loguru import logger
from core.exchange import ExchangeManager
from utils.notifier import LarkNotifier

class SpreadMonitor:
    def __init__(self, config: dict, symbol: str = None):
        self.config = config
        self.exchange_manager = None
        self.running = False
        self.last_alert_time = {}  # 记录上次提醒时间
        self.last_periodic_alert_time = 0  # 记录上次定时提醒时间
        
        # 如果指定了symbol，覆盖配置文件中的设置
        if symbol:
            self.config['strategy']['symbol'] = symbol
            
        # 初始化通知器
        if config.get('notifications', {}).get('lark_webhook'):
            self.notifier = LarkNotifier(config['notifications']['lark_webhook'])
        else:
            self.notifier = None
            
    async def initialize(self):
        """初始化交易所连接"""
        self.exchange_manager = ExchangeManager(self.config)
        await self.exchange_manager.initialize()
        logger.info(f"Monitoring spread for {self.config['strategy']['symbol']}")
        
    async def start(self):
        """启动监控"""
        self.running = True
        symbol = self.config['strategy']['symbol']
        
        # 启动订单簿数据流
        orderbook_tasks = await self.exchange_manager.start_orderbook_stream(symbol)
        
        # 启动监控主循环
        monitor_task = asyncio.create_task(self._run_monitor())
        
        return orderbook_tasks + [monitor_task]
        
    async def _run_monitor(self):
        """监控主循环"""
        while self.running:
            try:
                # 获取各交易所最优价格
                prices = await self.exchange_manager.get_best_prices(
                    self.config['strategy']['symbol']
                )
                
                if len(prices) < 2:
                    await asyncio.sleep(0.1)
                    continue
                    
                # 监控价差
                await self._monitor_spreads(prices)
                
                # 打印当前价差
                self._print_spreads(prices)
                
                # 检查是否需要定时播报
                await self._check_periodic_alert(prices)
                
                await asyncio.sleep(0.1)  # 控制循环频率
                
            except Exception as e:
                logger.error(f"Error in monitor loop: {str(e)}")
                await asyncio.sleep(1)
                
    async def _monitor_spreads(self, prices: Dict[str, dict]):
        """监控价差并发送提醒"""
        # 检查是否启用阈值告警
        if not self.config['monitoring']['threshold_alerts']['enabled']:
            return
            
        alert_threshold = self.config['monitoring']['threshold_alerts']['threshold']
        alert_interval = self.config['monitoring']['threshold_alerts']['interval']
        current_time = asyncio.get_event_loop().time()
        
        for ex1 in prices:
            for ex2 in prices:
                if ex1 >= ex2:
                    continue
                    
                # 计算价差
                spread1 = prices[ex2]['bid'] / prices[ex1]['ask'] - 1
                spread2 = prices[ex1]['bid'] / prices[ex2]['ask'] - 1
                
                # 检查是否需要发送提醒
                pair_key = f"{ex1}_{ex2}"
                last_alert = self.last_alert_time.get(pair_key, 0)
                
                if (spread1 > alert_threshold or spread2 > alert_threshold) and \
                   (current_time - last_alert) > alert_interval:
                    if self.notifier:
                        await self.notifier.send_spread_alert(
                            self.config['strategy']['symbol'],
                            ex1, ex2,
                            max(spread1, spread2),
                            prices[ex1]['bid'],
                            prices[ex2]['ask']
                        )
                    self.last_alert_time[pair_key] = current_time
                    
    async def _check_periodic_alert(self, prices: Dict[str, dict]):
        """检查是否需要定时播报"""
        # 检查是否启用定时播报
        if not self.config['monitoring']['periodic_alerts']['enabled']:
            return
            
        current_time = asyncio.get_event_loop().time()
        periodic_interval = self.config['monitoring']['periodic_alerts']['interval']
        
        if current_time - self.last_periodic_alert_time > periodic_interval:
            if self.notifier:
                # 收集所有价差信息
                spreads_info = []
                for ex1 in prices:
                    for ex2 in prices:
                        if ex1 >= ex2:
                            continue
                            
                        # 计算价差
                        spread1 = prices[ex2]['bid'] / prices[ex1]['ask'] - 1
                        spread2 = prices[ex1]['bid'] / prices[ex2]['ask'] - 1
                        
                        spreads_info.append({
                            'ex1': ex1,
                            'ex2': ex2,
                            'spread1': spread1,
                            'spread2': spread2,
                            'bid1': prices[ex1]['bid'],
                            'ask1': prices[ex1]['ask'],
                            'bid2': prices[ex2]['bid'],
                            'ask2': prices[ex2]['ask']
                        })
                
                # 发送定时播报
                await self._send_periodic_alert(spreads_info)
                
            self.last_periodic_alert_time = current_time
            
    async def _send_periodic_alert(self, spreads_info):
        """发送定时价差播报"""
        symbol = self.config['strategy']['symbol']
        current_time = time.strftime("%Y-%m-%d %H:%M:%S")
        
        title = f"价差定时播报 - {symbol} - {current_time}"
        
        # 构建内容
        content = f"交易对: {symbol}\n时间: {current_time}\n\n"
        
        for info in spreads_info:
            content += f"{info['ex1']} -> {info['ex2']}: {info['spread1']:.4%}\n"
            content += f"  买入价: {info['bid1']:.2f}, 卖出价: {info['ask1']:.2f}\n"
            content += f"{info['ex2']} -> {info['ex1']}: {info['spread2']:.4%}\n"
            content += f"  买入价: {info['bid2']:.2f}, 卖出价: {info['ask2']:.2f}\n\n"
            
        await self.notifier.send_message(title, content)
                    
    def _print_spreads(self, prices: Dict[str, dict]):
        """打印当前价差"""
        symbol = self.config['strategy']['symbol']
        print(f"\n=== {symbol} 价差监控 ===")
        print(f"时间: {time.strftime('%Y-%m-%d %H:%M:%S')}")
        
        for ex1 in prices:
            for ex2 in prices:
                if ex1 >= ex2:
                    continue
                    
                # 计算价差
                spread1 = prices[ex2]['bid'] / prices[ex1]['ask'] - 1
                spread2 = prices[ex1]['bid'] / prices[ex2]['ask'] - 1
                
                print(f"{ex1} -> {ex2}: {spread1:.4%}")
                print(f"{ex2} -> {ex1}: {spread2:.4%}")
                
        print("=" * 30)
        
    def stop(self):
        """停止监控"""
        self.running = False
        logger.info("Monitor stopped")
        
async def main():
    # 解析命令行参数
    parser = argparse.ArgumentParser(description='监控特定symbol的价差')
    parser.add_argument('--symbol', type=str, help='要监控的交易对，例如 BTC/USDT:USDT')
    parser.add_argument('--config', type=str, default='config/config.yaml', help='配置文件路径')
    args = parser.parse_args()
    
    # 加载环境变量
    load_dotenv()
    
    # 加载配置
    with open(args.config, 'r') as f:
        config = yaml.safe_load(f)
        
    # 设置日志
    logger.add(
        config['logging']['file'],
        level=config['logging']['level'],
        rotation="1 day"
    )
    
    try:
        # 初始化监控器
        monitor = SpreadMonitor(config, args.symbol)
        await monitor.initialize()
        
        # 启动监控
        tasks = await monitor.start()
        
        # 等待监控运行
        await asyncio.gather(*tasks)
        
    except KeyboardInterrupt:
        logger.info("Shutting down...")
    except Exception as e:
        logger.error(f"Error in main loop: {str(e)}")
    finally:
        # 清理资源
        monitor.stop()
        if monitor.exchange_manager:
            await monitor.exchange_manager.close()
        
if __name__ == "__main__":
    asyncio.run(main()) 