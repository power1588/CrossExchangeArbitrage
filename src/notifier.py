from typing import List

class Notifier:
    def __init__(self, config):
        self.config = config

    async def send_spread_alert(self, symbol: str, ex1: str, ex2: str, spread: float, bid: float, ask: float):
        """发送价差提醒"""
        if not self.config['monitoring']['threshold_alerts']['enabled']:
            return
            
        message = (
            f"🔔 价差提醒\n"
            f"交易对: {symbol}\n"
            f"交易所: {ex1} - {ex2}\n"
            f"价差: {spread:.2%}\n"
            f"价格: {bid:.2f} - {ask:.2f}"
        )
        
        if self.config['monitoring']['threshold_alerts']['notify_telegram']:
            await self._send_telegram(message)
            
        if self.config['monitoring']['threshold_alerts']['notify_discord']:
            await self._send_discord(message)
            
    async def send_periodic_alert(self, symbol: str, spreads_info: List[dict]):
        """发送定时播报"""
        if not self.config['monitoring']['periodic_alerts']['enabled']:
            return
            
        message = f"📊 {symbol} 价差播报\n\n"
        
        for info in spreads_info:
            message += (
                f"{info['ex1']} - {info['ex2']}\n"
                f"价差1: {info['spread1']:.2%}\n"
                f"价差2: {info['spread2']:.2%}\n"
                f"价格: {info['bid1']:.2f}/{info['ask1']:.2f} - {info['bid2']:.2f}/{info['ask2']:.2f}\n\n"
            )
            
        if self.config['monitoring']['periodic_alerts']['notify_telegram']:
            await self._send_telegram(message)
            
        if self.config['monitoring']['periodic_alerts']['notify_discord']:
            await self._send_discord(message) 