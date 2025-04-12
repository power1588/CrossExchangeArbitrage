from abc import ABC, abstractmethod
from typing import List, Dict, Any
import aiohttp
import logging

logger = logging.getLogger(__name__)

class Notifier:
    def __init__(self, config: Dict[str, Any]):
        self.config = config
        self.type = config.get('type')
        
        if self.type == 'lark':
            self.webhook_url = config.get('webhook_url')
        elif self.type == 'telegram':
            self.bot_token = config.get('bot_token')
            self.chat_id = config.get('chat_id')
            self.api_url = f"https://api.telegram.org/bot{self.bot_token}/sendMessage"
        else:
            raise ValueError(f"Unknown notifier type: {self.type}")
            
    async def send_spread_alert(self, pair: str, spread: float, prices: Dict[str, Any]) -> None:
        """发送价差提醒"""
        if self.type == 'lark':
            await self._send_lark_spread_alert(pair, spread, prices)
        elif self.type == 'telegram':
            await self._send_telegram_spread_alert(pair, spread, prices)
            
    async def send_periodic_alert(self, bbo_info: Dict[str, Dict[str, Dict[str, Any]]]) -> None:
        """发送定期提醒"""
        if self.type == 'lark':
            await self._send_lark_periodic_alert(bbo_info)
        elif self.type == 'telegram':
            await self._send_telegram_periodic_alert(bbo_info)
            
    async def _send_lark_spread_alert(self, pair: str, spread: float, prices: Dict[str, Any]) -> None:
        """发送价差提醒到飞书"""
        min_exchange = min(prices.items(), key=lambda x: x[1])[0]
        max_exchange = max(prices.items(), key=lambda x: x[1])[0]
        
        message = (
            f"🔔 价差提醒\n"
            f"交易对: {pair}\n"
            f"交易所: {min_exchange} - {max_exchange}\n"
            f"价差: {spread:.2f}%\n"
            f"价格: {prices[min_exchange]:.2f} - {prices[max_exchange]:.2f}"
        )
        
        lark_message = {
            "msg_type": "text",
            "content": {
                "text": message
            }
        }
        
        try:
            async with aiohttp.ClientSession() as session:
                async with session.post(self.webhook_url, json=lark_message) as response:
                    if response.status != 200:
                        logger.error(f"Failed to send spread alert: {await response.text()}")
        except Exception as e:
            logger.error(f"Error sending spread alert: {e}")
            
    async def _send_lark_periodic_alert(self, bbo_info: Dict[str, Dict[str, Dict[str, Any]]]) -> None:
        """发送定期提醒到飞书"""
        message = "📊 定期价差播报\n\n"
        
        for symbol, exchanges in bbo_info.items():
            message += f"🔸 {symbol}:\n"
            
            # 计算最大价差
            max_spread = 0
            max_spread_exchanges = None
            
            for ex1 in exchanges:
                for ex2 in exchanges:
                    if ex1 >= ex2:
                        continue
                        
                    # 计算价差
                    bid1 = exchanges[ex1]['bid']
                    ask1 = exchanges[ex1]['ask']
                    bid2 = exchanges[ex2]['bid']
                    ask2 = exchanges[ex2]['ask']
                    
                    # 计算套利空间
                    spread1 = (bid2 - ask1) / ask1 * 100  # 在 ex1 买入，在 ex2 卖出
                    spread2 = (bid1 - ask2) / ask2 * 100  # 在 ex2 买入，在 ex1 卖出
                    
                    if spread1 > max_spread:
                        max_spread = spread1
                        max_spread_exchanges = (ex1, ex2, 'buy', 'sell')
                        
                    if spread2 > max_spread:
                        max_spread = spread2
                        max_spread_exchanges = (ex2, ex1, 'buy', 'sell')
            
            # 添加最大价差信息
            if max_spread_exchanges:
                ex1, ex2, action1, action2 = max_spread_exchanges
                message += f"最大价差: {max_spread:.2f}%\n"
                message += f"在 {ex1} {action1}，在 {ex2} {action2}\n"
            
            # 添加各交易所的 BBO 信息
            message += "\n各交易所 BBO:\n"
            for exchange, info in exchanges.items():
                message += f"{exchange}: 买 {info['bid']:.4f} 卖 {info['ask']:.4f} (价差: {info['spread']:.2f}%)\n"
            
            message += "\n"
            
        lark_message = {
            "msg_type": "text",
            "content": {
                "text": message
            }
        }
        
        try:
            async with aiohttp.ClientSession() as session:
                async with session.post(self.webhook_url, json=lark_message) as response:
                    if response.status != 200:
                        logger.error(f"Failed to send periodic alert: {await response.text()}")
        except Exception as e:
            logger.error(f"Error sending periodic alert: {e}")
            
    async def _send_telegram_spread_alert(self, pair: str, spread: float, prices: Dict[str, Any]) -> None:
        """发送价差提醒到Telegram"""
        min_exchange = min(prices.items(), key=lambda x: x[1])[0]
        max_exchange = max(prices.items(), key=lambda x: x[1])[0]
        
        message = (
            f"🔔 价差提醒\n"
            f"交易对: {pair}\n"
            f"交易所: {min_exchange} - {max_exchange}\n"
            f"价差: {spread:.2f}%\n"
            f"价格: {prices[min_exchange]:.2f} - {prices[max_exchange]:.2f}"
        )
        
        try:
            async with aiohttp.ClientSession() as session:
                async with session.post(self.api_url, json={
                    "chat_id": self.chat_id,
                    "text": message
                }) as response:
                    if response.status != 200:
                        logger.error(f"Failed to send spread alert: {await response.text()}")
        except Exception as e:
            logger.error(f"Error sending spread alert: {e}")
            
    async def _send_telegram_periodic_alert(self, bbo_info: Dict[str, Dict[str, Dict[str, Any]]]) -> None:
        """发送定期提醒到Telegram"""
        message = "📊 定期价差播报\n\n"
        
        for symbol, exchanges in bbo_info.items():
            message += f"🔸 {symbol}:\n"
            
            # 计算最大价差
            max_spread = 0
            max_spread_exchanges = None
            
            for ex1 in exchanges:
                for ex2 in exchanges:
                    if ex1 >= ex2:
                        continue
                        
                    # 计算价差
                    bid1 = exchanges[ex1]['bid']
                    ask1 = exchanges[ex1]['ask']
                    bid2 = exchanges[ex2]['bid']
                    ask2 = exchanges[ex2]['ask']
                    
                    # 计算套利空间
                    spread1 = (bid2 - ask1) / ask1 * 100  # 在 ex1 买入，在 ex2 卖出
                    spread2 = (bid1 - ask2) / ask2 * 100  # 在 ex2 买入，在 ex1 卖出
                    
                    if spread1 > max_spread:
                        max_spread = spread1
                        max_spread_exchanges = (ex1, ex2, 'buy', 'sell')
                        
                    if spread2 > max_spread:
                        max_spread = spread2
                        max_spread_exchanges = (ex2, ex1, 'buy', 'sell')
            
            # 添加最大价差信息
            if max_spread_exchanges:
                ex1, ex2, action1, action2 = max_spread_exchanges
                message += f"最大价差: {max_spread:.2f}%\n"
                message += f"在 {ex1} {action1}，在 {ex2} {action2}\n"
            
            # 添加各交易所的 BBO 信息
            message += "\n各交易所 BBO:\n"
            for exchange, info in exchanges.items():
                message += f"{exchange}: 买 {info['bid']:.4f} 卖 {info['ask']:.4f} (价差: {info['spread']:.2f}%)\n"
            
            message += "\n"
            
        try:
            async with aiohttp.ClientSession() as session:
                async with session.post(self.api_url, json={
                    "chat_id": self.chat_id,
                    "text": message
                }) as response:
                    if response.status != 200:
                        logger.error(f"Failed to send periodic alert: {await response.text()}")
        except Exception as e:
            logger.error(f"Error sending periodic alert: {e}")

class NotifierFactory:
    @staticmethod
    def create_notifier(config: Dict[str, Any]) -> Notifier:
        """创建通知器实例"""
        return Notifier(config) 