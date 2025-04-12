import asyncio
import ccxt.pro as ccxtpro
from typing import Dict, Optional, List
from loguru import logger

class ExchangeManager:
    def __init__(this, config: dict):
        this.config = config
        this.exchanges: Dict[str, ccxtpro.Exchange] = {}
        this.orderbooks: Dict[str, dict] = {}
        this.running = False
        
    async def initialize(this):
        """初始化交易所连接"""
        for exchange_config in this.config['exchanges']:
            try:
                exchange_name = exchange_config['name']
                exchange_type = exchange_config['type']
                exchange_mode = exchange_config.get('mode', 'public')  # 默认为 public 模式
                
                # 创建交易所实例
                exchange_class = getattr(ccxtpro, exchange_type)
                
                # 准备交易所配置
                ccxt_config = {
                    'options': {
                        'defaultType': 'swap',  # 默认使用永续合约
                        'adjustForTimeDifference': True,
                        'recvWindow': 5000
                    }
                }
                
                # 根据模式配置 API 密钥
                if exchange_mode == 'private':
                    if not exchange_config.get('api_key') or not exchange_config.get('api_secret'):
                        logger.warning(f"Exchange {exchange_name} is in private mode but missing API credentials")
                    
                    ccxt_config['apiKey'] = exchange_config.get('api_key')
                    ccxt_config['secret'] = exchange_config.get('api_secret')
                    if exchange_config.get('password'):
                        ccxt_config['password'] = exchange_config.get('password')
                else:
                    logger.info(f"Exchange {exchange_name} is in public mode, API credentials not required")
                
                # 如果配置了测试网
                if exchange_config.get('testnet', False):
                    ccxt_config['options']['testnet'] = True
                
                exchange = exchange_class(ccxt_config)
                
                # 设置市场类型为永续合约
                await exchange.load_markets()
                
                this.exchanges[exchange_name] = exchange
                logger.info(f"Successfully initialized {exchange_name} ({exchange_type}) in {exchange_mode} mode")
                
            except Exception as e:
                logger.error(f"Failed to initialize {exchange_config.get('name', 'unknown')}: {str(e)}")
                raise
                
    async def start_orderbook_stream(this, symbol: str):
        """启动订单簿数据流"""
        this.running = True
        tasks = []
        
        for exchange_name, exchange in this.exchanges.items():
            task = asyncio.create_task(
                this._watch_orderbook(exchange_name, exchange, symbol)
            )
            tasks.append(task)
            
        return tasks
        
    async def _watch_orderbook(this, exchange_name: str, exchange: ccxtpro.Exchange, symbol: str):
        """监控订单簿数据"""
        while this.running:
            try:
                orderbook = await exchange.watch_order_book(symbol)
                this.orderbooks[exchange_name] = orderbook
                
            except Exception as e:
                logger.error(f"Error in orderbook stream for {exchange_name}: {str(e)}")
                await asyncio.sleep(1)  # 错误后等待一秒再重试
                
    async def get_best_prices(this, symbol: str) -> Dict[str, dict]:
        """获取各个交易所的最优价格"""
        prices = {}
        for exchange_name, orderbook in this.orderbooks.items():
            if orderbook and orderbook['bids'] and orderbook['asks']:
                prices[exchange_name] = {
                    'bid': orderbook['bids'][0][0],
                    'ask': orderbook['asks'][0][0]
                }
        return prices
        
    async def get_bbo_info(this, symbol: str) -> Dict[str, dict]:
        """获取各个交易所的 BBO 信息"""
        bbo_info = {}
        
        for exchange_name, exchange in this.exchanges.items():
            try:
                # 获取订单簿
                orderbook = await exchange.fetch_order_book(symbol)
                
                if orderbook and orderbook['bids'] and orderbook['asks']:
                    bbo_info[exchange_name] = {
                        'bid': orderbook['bids'][0][0],
                        'bid_volume': orderbook['bids'][0][1],
                        'ask': orderbook['asks'][0][0],
                        'ask_volume': orderbook['asks'][0][1],
                        'spread': (orderbook['asks'][0][0] - orderbook['bids'][0][0]) / orderbook['bids'][0][0] * 100
                    }
            except Exception as e:
                logger.error(f"Error fetching BBO for {symbol} on {exchange_name}: {str(e)}")
                continue
                
        return bbo_info
        
    async def get_ticker_info(this, symbol: str) -> Dict[str, dict]:
        """获取各个交易所的 Ticker 信息"""
        ticker_info = {}
        
        for exchange_name, exchange in this.exchanges.items():
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
        
    async def create_order(this, exchange_name: str, symbol: str, order_type: str, 
                          side: str, amount: float, price: Optional[float] = None):
        """创建订单"""
        exchange = this.exchanges[exchange_name]
        
        # 检查交易所是否支持交易
        exchange_config = next((ex for ex in this.config['exchanges'] if ex['name'] == exchange_name), None)
        if not exchange_config or exchange_config.get('mode', 'public') != 'private':
            raise ValueError(f"Exchange {exchange_name} is not in private mode, cannot create orders")
        
        try:
            order = await exchange.create_order(
                symbol=symbol,
                type=order_type,
                side=side,
                amount=amount,
                price=price
            )
            logger.info(f"Order created on {exchange_name}: {order}")
            return order
        except Exception as e:
            logger.error(f"Failed to create order on {exchange_name}: {str(e)}")
            raise
            
    async def get_order_status(this, exchange_name: str, order_id: str) -> dict:
        """获取订单状态"""
        exchange = this.exchanges[exchange_name]
        
        # 检查交易所是否支持交易
        exchange_config = next((ex for ex in this.config['exchanges'] if ex['name'] == exchange_name), None)
        if not exchange_config or exchange_config.get('mode', 'public') != 'private':
            raise ValueError(f"Exchange {exchange_name} is not in private mode, cannot get order status")
        
        try:
            order = await exchange.fetch_order(order_id)
            return order
        except Exception as e:
            logger.error(f"Failed to get order status on {exchange_name}: {str(e)}")
            raise
            
    async def cancel_order(this, exchange_name: str, order_id: str):
        """取消订单"""
        exchange = this.exchanges[exchange_name]
        
        # 检查交易所是否支持交易
        exchange_config = next((ex for ex in this.config['exchanges'] if ex['name'] == exchange_name), None)
        if not exchange_config or exchange_config.get('mode', 'public') != 'private':
            raise ValueError(f"Exchange {exchange_name} is not in private mode, cannot cancel orders")
        
        try:
            await exchange.cancel_order(order_id)
            logger.info(f"Order cancelled on {exchange_name}: {order_id}")
        except Exception as e:
            logger.error(f"Failed to cancel order on {exchange_name}: {str(e)}")
            raise
            
    async def close(this):
        """关闭所有交易所连接"""
        for exchange_name, exchange in this.exchanges.items():
            try:
                await exchange.close()
                logger.info(f"Closed connection to {exchange_name}")
            except Exception as e:
                logger.error(f"Error closing connection to {exchange_name}: {str(e)}")
                
        this.running = False 