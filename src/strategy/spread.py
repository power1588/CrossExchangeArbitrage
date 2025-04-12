import asyncio
import logging
from typing import Dict, List, Any
from datetime import datetime, timedelta
from core.exchange import ExchangeManager
from core.notifier import Notifier

logger = logging.getLogger(__name__)

class SpreadStrategy:
    def __init__(
        self,
        exchange_manager: ExchangeManager,
        notifiers: List[Notifier],
        min_spread: float = 0.5,
        check_interval: int = 60,
        alert_interval: int = 300,
        periodic_alert_interval: int = 3600
    ):
        self.exchange_manager = exchange_manager
        self.notifiers = notifiers
        self.min_spread = min_spread
        self.check_interval = check_interval
        self.alert_interval = alert_interval
        self.periodic_alert_interval = periodic_alert_interval
        self.last_alert_time: Dict[str, datetime] = {}
        self.last_periodic_alert_time = datetime.now() - timedelta(seconds=periodic_alert_interval)
        self.running = False
        
    async def start(self):
        """启动策略"""
        self.running = True
        logger.info("Starting spread strategy...")
        
        while self.running:
            try:
                await self.check_spreads()
                await self.check_periodic_alert()
                await asyncio.sleep(self.check_interval)
            except Exception as e:
                logger.error(f"Error in spread check: {str(e)}")
                await asyncio.sleep(self.check_interval)
                
    async def stop(self):
        """停止策略"""
        self.running = False
        logger.info("Stopping spread strategy...")
        
    async def check_spreads(self):
        """检查所有交易所之间的价差"""
        # 获取所有交易所的行情
        prices: Dict[str, Dict[str, float]] = {}
        for name, exchange in self.exchange_manager.exchanges.items():
            try:
                # 获取所有交易对的行情
                tickers = {}
                for symbol in exchange.markets.keys():
                    if symbol.endswith('/USDT'):  # 只关注 USDT 交易对
                        try:
                            ticker = await exchange.fetch_ticker(symbol)
                            tickers[symbol] = ticker['last']
                        except Exception as e:
                            logger.error(f"Error fetching ticker for {symbol} on {name}: {str(e)}")
                            continue
                prices[name] = tickers
            except Exception as e:
                logger.error(f"Error getting prices from {name}: {str(e)}")
                continue
                
        # 计算价差
        for pair in self._get_common_pairs(prices):
            for ex1 in self.exchange_manager.exchanges:
                for ex2 in self.exchange_manager.exchanges:
                    if ex1 >= ex2:
                        continue
                        
                    price1 = prices[ex1].get(pair)
                    price2 = prices[ex2].get(pair)
                    
                    if not price1 or not price2:
                        continue
                        
                    spread = abs(price1 - price2) / min(price1, price2) * 100
                    
                    if spread >= self.min_spread:
                        await self._handle_spread_alert(pair, spread, {
                            ex1: price1,
                            ex2: price2
                        })
                        
    async def check_periodic_alert(self):
        """检查是否需要发送定时播报"""
        now = datetime.now()
        if now - self.last_periodic_alert_time >= timedelta(seconds=self.periodic_alert_interval):
            await self._send_periodic_alert()
            self.last_periodic_alert_time = now
            
    async def _send_periodic_alert(self):
        """发送定时播报"""
        # 获取所有交易所的 BBO 信息
        bbo_info = {}
        for symbol in self._get_common_symbols():
            bbo_info[symbol] = await self.exchange_manager.get_bbo_info(symbol)
            
        # 发送定时播报
        for notifier in self.notifiers:
            try:
                await notifier.send_periodic_alert(bbo_info)
            except Exception as e:
                logger.error(f"Error sending periodic alert: {str(e)}")
                
    def _get_common_pairs(self, prices: Dict[str, Dict[str, float]]) -> List[str]:
        """获取所有交易所共同的交易对"""
        common_pairs = set()
        first = True
        
        for exchange_prices in prices.values():
            if first:
                common_pairs = set(exchange_prices.keys())
                first = False
            else:
                common_pairs &= set(exchange_prices.keys())
                
        return list(common_pairs)
        
    def _get_common_symbols(self) -> List[str]:
        """获取所有交易所共同的交易对"""
        common_symbols = set()
        first = True
        
        for exchange in self.exchange_manager.exchanges.values():
            if first:
                common_symbols = set(exchange.markets.keys())
                first = False
            else:
                common_symbols &= set(exchange.markets.keys())
                
        return [symbol for symbol in common_symbols if symbol.endswith('/USDT')]
        
    async def _handle_spread_alert(self, pair: str, spread: float, prices: Dict[str, Any]):
        """处理价差提醒"""
        now = datetime.now()
        last_alert = self.last_alert_time.get(pair)
        
        if last_alert and now - last_alert < timedelta(seconds=self.alert_interval):
            return
            
        self.last_alert_time[pair] = now
        
        # 发送提醒
        for notifier in self.notifiers:
            try:
                await notifier.send_spread_alert(pair, spread, prices)
            except Exception as e:
                logger.error(f"Error sending alert: {str(e)}")
                
    async def get_arbitrage_opportunities(self, symbol: str) -> List[Dict[str, Any]]:
        """获取套利机会"""
        # 获取所有交易所的 BBO 信息
        bbo_info = await this.exchange_manager.get_bbo_info(symbol)
        
        # 计算套利机会
        opportunities = []
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
                
                if spread1 > 0:
                    opportunities.append({
                        'symbol': symbol,
                        'buy_exchange': ex1,
                        'sell_exchange': ex2,
                        'buy_price': ask1,
                        'sell_price': bid2,
                        'spread': spread1,
                        'volume': min(bbo_info[ex1]['ask_volume'], bbo_info[ex2]['bid_volume'])
                    })
                    
                if spread2 > 0:
                    opportunities.append({
                        'symbol': symbol,
                        'buy_exchange': ex2,
                        'sell_exchange': ex1,
                        'buy_price': ask2,
                        'sell_price': bid1,
                        'spread': spread2,
                        'volume': min(bbo_info[ex2]['ask_volume'], bbo_info[ex1]['bid_volume'])
                    })
                    
        # 按套利空间排序
        opportunities.sort(key=lambda x: x['spread'], reverse=True)
        
        return opportunities 