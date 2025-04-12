import os
import yaml
from typing import Dict, Any, List
from loguru import logger

class Config:
    def __init__(self, config_path: str = "config.yaml"):
        self.config_path = config_path
        self.config_data = self._load_config()
        self._validate_config()
        self._set_defaults()
        
    def _load_config(self) -> Dict[str, Any]:
        """加载配置文件"""
        if not os.path.exists(self.config_path):
            raise FileNotFoundError(f"配置文件 {self.config_path} 不存在")
            
        try:
            with open(self.config_path, 'r', encoding='utf-8') as f:
                return yaml.safe_load(f)
        except Exception as e:
            raise ValueError(f"加载配置文件失败: {e}")
            
    def _validate_config(self):
        """验证配置"""
        if not self.config_data:
            raise ValueError("配置文件为空")
            
        if 'exchanges' not in self.config_data:
            raise ValueError("配置文件中缺少 'exchanges' 字段")
            
        if not self.config_data['exchanges']:
            raise ValueError("'exchanges' 字段为空")
            
        if 'notifiers' not in self.config_data:
            raise ValueError("配置文件中缺少 'notifiers' 字段")
            
        if not self.config_data['notifiers']:
            raise ValueError("'notifiers' 字段为空")
            
        # 验证每个交易所的配置
        for exchange in self.config_data['exchanges']:
            if 'name' not in exchange:
                raise ValueError("交易所配置缺少 'name' 字段")
                
            if 'type' not in exchange:
                raise ValueError(f"交易所 {exchange['name']} 配置缺少 'type' 字段")
                
            if 'mode' in exchange and exchange['mode'] not in ['public', 'private']:
                raise ValueError(f"交易所 {exchange['name']} 的 mode 必须是 'public' 或 'private'")
                
            if exchange.get('mode') == 'private':
                if not exchange.get('api_key') or not exchange.get('api_secret'):
                    raise ValueError(f"交易所 {exchange['name']} 在 private 模式下必须提供 API 密钥")
                    
    def _set_defaults(self):
        """设置默认值"""
        # 设置默认的价差阈值
        if 'min_spread' not in self.config_data:
            self.config_data['min_spread'] = 0.5
            
        # 设置默认的检查间隔
        if 'check_interval' not in self.config_data:
            self.config_data['check_interval'] = 60
            
        # 设置默认的提醒间隔
        if 'alert_interval' not in self.config_data:
            self.config_data['alert_interval'] = 300
            
        # 设置默认的定时播报间隔
        if 'periodic_alert_interval' not in self.config_data:
            self.config_data['periodic_alert_interval'] = 3600
            
        # 为每个交易所设置默认模式
        for exchange in self.config_data['exchanges']:
            if 'mode' not in exchange:
                exchange['mode'] = 'public'
                
    @property
    def exchanges(self) -> List[Dict[str, Any]]:
        """获取交易所配置列表"""
        return self.config_data['exchanges']
        
    @property
    def notifiers(self) -> List[Dict[str, Any]]:
        """获取通知器配置列表"""
        return self.config_data['notifiers']
        
    @property
    def min_spread(self) -> float:
        """获取最小价差阈值"""
        return self.config_data['min_spread']
        
    @property
    def check_interval(self) -> int:
        """获取检查间隔（秒）"""
        return self.config_data['check_interval']
        
    @property
    def alert_interval(self) -> int:
        """获取提醒间隔（秒）"""
        return self.config_data['alert_interval']
        
    @property
    def periodic_alert_interval(self) -> int:
        """获取定时播报间隔（秒）"""
        return self.config_data['periodic_alert_interval'] 