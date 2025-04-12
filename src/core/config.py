import os
import yaml
from typing import Dict, Any, List

class Config:
    def __init__(self, config_path: str = "config.yaml"):
        self.config_path = config_path
        self.config = self._load_config()
        
        # 验证配置
        self._validate_config()
        
        # 设置默认值
        self._set_defaults()
    
    def _load_config(self) -> Dict[str, Any]:
        """加载配置文件"""
        if not os.path.exists(self.config_path):
            raise FileNotFoundError(f"Config file not found: {self.config_path}")
        
        with open(self.config_path, 'r') as f:
            return yaml.safe_load(f)
    
    def _validate_config(self) -> None:
        """验证配置"""
        required_fields = ['exchanges', 'notifiers']
        for field in required_fields:
            if field not in self.config:
                raise ValueError(f"Missing required field: {field}")
        
        if not self.config['exchanges']:
            raise ValueError("No exchanges configured")
        
        if not self.config['notifiers']:
            raise ValueError("No notifiers configured")
            
        # 验证交易所配置
        for exchange in self.config['exchanges']:
            if 'name' not in exchange:
                raise ValueError("Exchange name is required")
                
            if 'type' not in exchange:
                raise ValueError(f"Exchange type is required for {exchange.get('name', 'unknown')}")
                
            # 验证模式
            mode = exchange.get('mode', 'public')
            if mode not in ['public', 'private']:
                raise ValueError(f"Invalid mode '{mode}' for exchange {exchange.get('name', 'unknown')}. Must be 'public' or 'private'")
                
            # 如果是私有模式，验证 API 密钥
            if mode == 'private':
                if not exchange.get('api_key') or not exchange.get('api_secret'):
                    raise ValueError(f"API credentials are required for private mode exchange {exchange.get('name', 'unknown')}")
    
    def _set_defaults(self) -> None:
        """设置默认值"""
        self.config.setdefault('min_spread', 0.5)
        self.config.setdefault('check_interval', 60)
        self.config.setdefault('alert_interval', 300)
        self.config.setdefault('periodic_alert_interval', 3600)
        
        # 为交易所设置默认模式
        for exchange in self.config['exchanges']:
            if 'mode' not in exchange:
                exchange['mode'] = 'public'
    
    @property
    def exchanges(self) -> List[Dict[str, Any]]:
        """获取交易所配置"""
        return self.config['exchanges']
    
    @property
    def notifiers(self) -> List[Dict[str, Any]]:
        """获取通知器配置"""
        return self.config['notifiers']
    
    @property
    def min_spread(self) -> float:
        """获取最小价差阈值"""
        return self.config['min_spread']
    
    @property
    def check_interval(self) -> int:
        """获取检查间隔（秒）"""
        return self.config['check_interval']
    
    @property
    def alert_interval(self) -> int:
        """获取提醒间隔（秒）"""
        return self.config['alert_interval']
        
    @property
    def periodic_alert_interval(self) -> int:
        """获取定时播报间隔（秒）"""
        return self.config['periodic_alert_interval'] 