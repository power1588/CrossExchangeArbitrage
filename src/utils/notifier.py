import aiohttp
from loguru import logger

class LarkNotifier:
    def __init__(self, webhook_url: str):
        self.webhook_url = webhook_url
        
    async def send_message(self, title: str, content: str):
        """发送 Lark 消息"""
        try:
            message = {
                "msg_type": "post",
                "content": {
                    "post": {
                        "zh_cn": {
                            "title": title,
                            "content": [[{
                                "tag": "text",
                                "text": content
                            }]]
                        }
                    }
                }
            }
            
            async with aiohttp.ClientSession() as session:
                async with session.post(self.webhook_url, json=message) as response:
                    if response.status != 200:
                        logger.error(f"Failed to send Lark notification: {await response.text()}")
                        
        except Exception as e:
            logger.error(f"Error sending Lark notification: {str(e)}")
            
    async def send_spread_alert(self, symbol: str, exchange1: str, exchange2: str, 
                              spread: float, bid_price: float, ask_price: float):
        """发送价差提醒"""
        title = f"价差提醒 - {symbol}"
        content = (
            f"交易所: {exchange1} vs {exchange2}\n"
            f"价差: {spread:.4%}\n"
            f"买入价: {bid_price:.2f}\n"
            f"卖出价: {ask_price:.2f}"
        )
        await self.send_message(title, content) 