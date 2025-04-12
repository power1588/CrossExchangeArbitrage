import asyncio
import ccxt.pro as ccxtpro
from typing import Dict, Optional, List
from loguru import logger

class ExchangeManager:
    def __init__(self, config):
        self.config = config
        self.exchanges: Dict[str, ccxtpro.Exchange] = {}
        self.orderbooks: Dict[str, dict] = {}
        self.running = False
        
    async def initialize(self):
        """初始化所有交易所"""
        for exchange_config in self.config.exchanges:
            try:
                exchange_id = exchange_config['name']
                exchange_class = getattr(ccxtpro, exchange_id)
                
                # 获取交易所模式
                exchange_mode = exchange_config.get('mode', 'public')
                
                # 根据模式决定是否需要API密钥
                if exchange_mode == 'private':
                    if not exchange_config.get('api_key') or not exchange_config.get('api_secret'):
                        logger.warning(f"Exchange {exchange_id} is in private mode but missing API credentials")
                        continue
                        
                    exchange = exchange_class({
                        'apiKey': exchange_config['api_key'],
                        'secret': exchange_config['api_secret'],
                        'enableRateLimit': True,
                        'options': {
                            'defaultType': 'swap'
                        }
                    })
                else:
                    exchange = exchange_class({
                        'enableRateLimit': True,
                        'options': {
                            'defaultType': 'swap'
                        }
                    })
                
                if exchange_config.get('testnet', False):
                    exchange.set_sandbox_mode(True)
                    
                self.exchanges[exchange_id] = exchange
                logger.info(f"Initialized {exchange_id} in {exchange_mode} mode")
                
            except Exception as e:
                logger.error(f"Failed to initialize exchange {exchange_id}: {e}")
                
    async def start_orderbook_stream(self, symbol: str):
        """启动订单簿数据流"""
        self.running = True
        tasks = []
        
        for exchange_name, exchange in self.exchanges.items():
            task = asyncio.create_task(
                self._watch_orderbook(exchange_name, exchange, symbol)
            )
            tasks.append(task)
            
        return tasks
        
    async def _watch_orderbook(self, exchange_name: str, exchange: ccxtpro.Exchange, symbol: str):
        """监控订单簿数据"""
        while self.running:
            try:
                orderbook = await exchange.watch_order_book(symbol)
                self.orderbooks[exchange_name] = orderbook
                
            except Exception as e:
                logger.error(f"Error in orderbook stream for {exchange_name}: {str(e)}")
                await asyncio.sleep(1)  # 错误后等待一秒再重试
                
    async def get_best_prices(self, symbol: str) -> Dict[str, dict]:
        """获取各个交易所的最优价格"""
        prices = {}
        for exchange_name, orderbook in self.orderbooks.items():
            if orderbook and orderbook['bids'] and orderbook['asks']:
                prices[exchange_name] = {
                    'bid': orderbook['bids'][0][0],
                    'ask': orderbook['asks'][0][0]
                }
        return prices
        
    async def get_bbo_info(self, exchange_id: str, symbol: str) -> Dict[str, dict]:
        """获取指定交易所和交易对的最佳买卖价信息"""
        try:
            exchange = self.exchanges.get(exchange_id)
            if not exchange:
                raise ValueError(f"Exchange {exchange_id} not found")
                
            # 获取订单簿
            orderbook = await exchange.fetch_order_book(symbol)
            
            # 获取最佳买卖价
            best_bid = orderbook['bids'][0][0] if orderbook['bids'] else None
            best_ask = orderbook['asks'][0][0] if orderbook['asks'] else None
            
            # 计算买卖价差
            spread = ((best_ask - best_bid) / best_bid * 100) if best_bid and best_ask else None
            
            return {
                'bid': best_bid,
                'ask': best_ask,
                'spread': spread
            }
            
        except Exception as e:
            logger.error(f"Error getting BBO info for {exchange_id} {symbol}: {e}")
            return {
                'bid': None,
                'ask': None,
                'spread': None
            }
            
    async def get_ticker_info(self, symbol: str) -> Dict[str, dict]:
        """获取各个交易所的 Ticker 信息"""
        ticker_info = {}
        
        for exchange_name, exchange in self.exchanges.items():
            try:
                ticker = await exchange.fetch_ticker(symbol)
                ticker_info[exchange_name] = {
                    'last': ticker['last'],
                    'bid': ticker['bid'],
                    'ask': ticker['ask'],
                    'volume': ticker['baseVolume'],
                    'high': ticker['high'],
                    'low': ticker['low']
                }
            except Exception as e:
                logger.error(f"Error fetching ticker for {symbol} on {exchange_name}: {str(e)}")
                continue
                
        return ticker_info
        
    async def create_order(self, exchange_id: str, symbol: str, order_type: str, side: str, amount: float, price: float = None) -> Dict[str, dict]:
        """创建订单"""
        try:
            exchange = self.exchanges.get(exchange_id)
            if not exchange:
                raise ValueError(f"Exchange {exchange_id} not found")
                
            if exchange_config.get('mode', 'public') == 'public':
                raise ValueError(f"Exchange {exchange_id} is in public mode, cannot create orders")
                
            order = await exchange.create_order(
                symbol=symbol,
                type=order_type,
                side=side,
                amount=amount,
                price=price
            )
            return order
            
        except Exception as e:
            logger.error(f"Error creating order on {exchange_id}: {e}")
            return None
            
    async def get_order_status(self, exchange_id: str, order_id: str, symbol: str) -> Dict[str, dict]:
        """获取订单状态"""
        try:
            exchange = self.exchanges.get(exchange_id)
            if not exchange:
                raise ValueError(f"Exchange {exchange_id} not found")
                
            if exchange_config.get('mode', 'public') == 'public':
                raise ValueError(f"Exchange {exchange_id} is in public mode, cannot get order status")
                
            order = await exchange.fetch_order(order_id, symbol)
            return order
            
        except Exception as e:
            logger.error(f"Error getting order status from {exchange_id}: {e}")
            return None
            
    async def cancel_order(self, exchange_id: str, order_id: str, symbol: str) -> Dict[str, dict]:
        """取消订单"""
        try:
            exchange = self.exchanges.get(exchange_id)
            if not exchange:
                raise ValueError(f"Exchange {exchange_id} not found")
                
            if exchange_config.get('mode', 'public') == 'public':
                raise ValueError(f"Exchange {exchange_id} is in public mode, cannot cancel orders")
                
            order = await exchange.cancel_order(order_id, symbol)
            return order
            
        except Exception as e:
            logger.error(f"Error canceling order on {exchange_id}: {e}")
            return None
            
    async def close(self):
        """关闭所有交易所连接"""
        for exchange_name, exchange in self.exchanges.items():
            try:
                await exchange.close()
                logger.info(f"Closed connection to {exchange_name}")
            except Exception as e:
                logger.error(f"Error closing connection to {exchange_name}: {str(e)}")
                
        self.running = False 