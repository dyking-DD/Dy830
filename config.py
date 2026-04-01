"""
配置模块 - Configuration Module

简化版配置管理，提供与 PortfolioConfig 的兼容
"""
import os
import yaml
from typing import Dict, Any
from strategies.portfolio import PortfolioConfig


class Config:
    """配置管理类"""
    
    # 默认配置
    DEFAULT_STRATEGY_WEIGHTS = {
        'rsi': 0.2,
        'macd': 0.2,
        'bollinger': 0.2,
        'momentum': 0.2,
        'combined': 0.2
    }
    
    DEFAULT_MAX_POSITIONS = 10
    DEFAULT_SIGNAL_THRESHOLD = 0.5
    
    def __init__(self, config_path: str = None):
        """
        初始化配置
        
        Args:
            config_path: 配置文件路径（可选）
        """
        self.config_path = config_path
        self.strategy_weights = self.DEFAULT_STRATEGY_WEIGHTS.copy()
        self.max_positions = self.DEFAULT_MAX_POSITIONS
        self.signal_threshold = self.DEFAULT_SIGNAL_THRESHOLD
        
        # 尝试加载配置文件
        if config_path and os.path.exists(config_path):
            self._load_from_file(config_path)
        else:
            # 尝试加载默认配置
            self._load_default_configs()
    
    def _load_from_file(self, path: str):
        """从文件加载配置"""
        try:
            with open(path, 'r') as f:
                if path.endswith('.yaml') or path.endswith('.yml'):
                    data = yaml.safe_load(f)
                else:
                    import json
                    data = json.load(f)
                
                # 更新配置
                if 'strategies' in data:
                    for name, cfg in data['strategies'].items():
                        if 'weight' in cfg:
                            self.strategy_weights[name] = cfg['weight']
                
                if 'portfolio' in data:
                    portfolio = data['portfolio']
                    if 'max_positions' in portfolio:
                        self.max_positions = portfolio['max_positions']
                    if 'signal_threshold' in portfolio:
                        self.signal_threshold = portfolio['signal_threshold']
        except Exception as e:
            print(f"加载配置文件失败: {e}，使用默认配置")
    
    def _load_default_configs(self):
        """加载默认配置文件"""
        # 尝试加载策略配置
        strategy_config_path = 'config/strategy.yaml'
        if os.path.exists(strategy_config_path):
            try:
                with open(strategy_config_path, 'r') as f:
                    data = yaml.safe_load(f)
                    if 'strategies' in data:
                        weights = {}
                        for name, cfg in data['strategies'].items():
                            if isinstance(cfg, dict) and 'weight' in cfg:
                                weights[name] = cfg['weight']
                            elif isinstance(cfg, (int, float)):
                                weights[name] = cfg
                        if weights:
                            self.strategy_weights = weights
            except Exception as e:
                print(f"加载策略配置失败: {e}")
        
        # 尝试加载投资组合配置
        portfolio_config_path = 'config/portfolio.yaml'
        if os.path.exists(portfolio_config_path):
            try:
                with open(portfolio_config_path, 'r') as f:
                    data = yaml.safe_load(f)
                    if 'max_positions' in data:
                        self.max_positions = data['max_positions']
                    if 'signal_threshold' in data:
                        self.signal_threshold = data['signal_threshold']
            except Exception as e:
                print(f"加载投资组合配置失败: {e}")
    
    def to_portfolio_config(self) -> PortfolioConfig:
        """
        转换为 PortfolioConfig 对象
        
        Returns:
            PortfolioConfig 实例
        """
        return PortfolioConfig(
            name="量化组合",
            strategy_weights=self.strategy_weights,
            signal_threshold=self.signal_threshold,
            max_positions=self.max_positions,
            rebalance_freq='daily'
        )
    
    def get(self, key: str, default=None):
        """获取配置值"""
        if hasattr(self, key):
            return getattr(self, key)
        return default
    
    def __getitem__(self, key: str):
        """支持字典式访问"""
        return self.get(key)
    
    def __repr__(self):
        return f"Config(weights={self.strategy_weights}, max_pos={self.max_positions}, threshold={self.signal_threshold})"


# 保持向后兼容
PortfolioConfig = PortfolioConfig
