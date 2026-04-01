"""
黑名单管理器 - 自动维护ST股、退市股、停牌股黑名单

数据源：
- AkShare: 获取ST股票列表、退市股票列表
- 本地缓存: 每日更新，避免频繁调用API
"""

import pandas as pd
import akshare as ak
from datetime import datetime, timedelta
from typing import Set, List
import os
import json
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class BlacklistManager:
    """黑名单管理器"""
    
    def __init__(self, cache_dir: str = "config"):
        self.cache_dir = cache_dir
        self.cache_file = os.path.join(cache_dir, "blacklist_cache.json")
        self.blacklist_file = os.path.join(cache_dir, "blacklist.txt")
        
        # 确保目录存在
        os.makedirs(cache_dir, exist_ok=True)
        
        # 内存中的黑名单
        self.st_stocks: Set[str] = set()
        self.delisting_stocks: Set[str] = set()
        self.suspended_stocks: Set[str] = set()
        self.manual_blacklist: Set[str] = set()
        
        # 加载缓存
        self._load_cache()
    
    def _load_cache(self):
        """加载缓存数据"""
        if os.path.exists(self.cache_file):
            try:
                with open(self.cache_file, 'r', encoding='utf-8') as f:
                    cache = json.load(f)
                    self.st_stocks = set(cache.get('st_stocks', []))
                    self.delisting_stocks = set(cache.get('delisting_stocks', []))
                    self.suspended_stocks = set(cache.get('suspended_stocks', []))
                    self.manual_blacklist = set(cache.get('manual_blacklist', []))
                logger.info(f"已加载黑名单缓存: {len(self.get_all_blacklist())} 只股票")
            except Exception as e:
                logger.warning(f"加载缓存失败: {e}")
    
    def _save_cache(self):
        """保存缓存数据"""
        cache = {
            'last_update': datetime.now().isoformat(),
            'st_stocks': list(self.st_stocks),
            'delisting_stocks': list(self.delisting_stocks),
            'suspended_stocks': list(self.suspended_stocks),
            'manual_blacklist': list(self.manual_blacklist)
        }
        with open(self.cache_file, 'w', encoding='utf-8') as f:
            json.dump(cache, f, ensure_ascii=False, indent=2)
    
    def _save_blacklist_txt(self):
        """保存为文本格式（供风控模块使用）"""
        all_blacklist = self.get_all_blacklist()
        with open(self.blacklist_file, 'w', encoding='utf-8') as f:
            for symbol in sorted(all_blacklist):
                f.write(f"{symbol}\n")
        logger.info(f"黑名单已保存到: {self.blacklist_file}")
    
    def update_st_stocks(self) -> Set[str]:
        """
        更新ST股票列表
        
        Returns:
            当前ST股票集合
        """
        try:
            # 获取风险警示板股票
            df = ak.stock_zh_a_st_em()
            if df is not None and not df.empty:
                # 提取股票代码
                self.st_stocks = set(df['代码'].apply(lambda x: f"{x}.SZ" if x.startswith('0') or x.startswith('3') else f"{x}.SH"))
                logger.info(f"已更新ST股票: {len(self.st_stocks)} 只")
            else:
                logger.warning("获取ST股票列表为空")
        except Exception as e:
            logger.error(f"更新ST股票失败: {e}")
        
        return self.st_stocks
    
    def update_delisting_stocks(self) -> Set[str]:
        """
        更新退市股票列表
        
        Returns:
            当前退市股票集合
        """
        try:
            # 获取退市股票列表
            df = ak.stock_zh_a_new_em()
            if df is not None and not df.empty:
                # 筛选退市整理期的股票
                if '名称' in df.columns:
                    delisting = df[df['名称'].str.contains('退市', na=False)]
                    self.delisting_stocks = set(delisting['代码'].apply(
                        lambda x: f"{x}.SZ" if x.startswith('0') or x.startswith('3') else f"{x}.SH"
                    ))
                    logger.info(f"已更新退市股票: {len(self.delisting_stocks)} 只")
        except Exception as e:
            logger.error(f"更新退市股票失败: {e}")
        
        return self.delisting_stocks
    
    def update_suspended_stocks(self, stock_list: List[str] = None) -> Set[str]:
        """
        更新停牌股票列表
        
        Args:
            stock_list: 要检查的股票列表，为None时检查全部
        
        Returns:
            当前停牌股票集合
        """
        suspended = set()
        
        try:
            if stock_list is None:
                # 获取全部股票列表
                df = ak.stock_zh_a_spot_em()
                if df is not None and not df.empty:
                    # 成交量为0或特定状态的视为停牌
                    suspended_df = df[df['成交量'] == 0]
                    suspended = set(suspended_df['代码'].apply(
                        lambda x: f"{x}.SZ" if x.startswith('0') or x.startswith('3') else f"{x}.SH"
                    ))
            
            self.suspended_stocks = suspended
            logger.info(f"已更新停牌股票: {len(self.suspended_stocks)} 只")
            
        except Exception as e:
            logger.error(f"更新停牌股票失败: {e}")
        
        return self.suspended_stocks
    
    def add_manual(self, symbol: str, reason: str = ""):
        """手动添加黑名单"""
        self.manual_blacklist.add(symbol)
        logger.info(f"手动添加黑名单: {symbol}, 原因: {reason}")
    
    def remove_manual(self, symbol: str):
        """手动移除黑名单"""
        self.manual_blacklist.discard(symbol)
        logger.info(f"手动移除黑名单: {symbol}")
    
    def update_all(self, check_suspended: bool = True) -> Set[str]:
        """
        更新所有黑名单
        
        Args:
            check_suspended: 是否检查停牌（耗时较长）
        
        Returns:
            完整黑名单集合
        """
        logger.info("开始更新黑名单...")
        
        self.update_st_stocks()
        self.update_delisting_stocks()
        
        if check_suspended:
            self.update_suspended_stocks()
        
        # 保存缓存
        self._save_cache()
        self._save_blacklist_txt()
        
        all_blacklist = self.get_all_blacklist()
        logger.info(f"黑名单更新完成，共 {len(all_blacklist)} 只股票")
        
        return all_blacklist
    
    def get_all_blacklist(self) -> Set[str]:
        """获取完整黑名单"""
        return self.st_stocks | self.delisting_stocks | self.suspended_stocks | self.manual_blacklist
    
    def get_blacklist_by_category(self) -> dict:
        """按类别获取黑名单"""
        return {
            'st_stocks': self.st_stocks,
            'delisting_stocks': self.delisting_stocks,
            'suspended_stocks': self.suspended_stocks,
            'manual_blacklist': self.manual_blacklist
        }
    
    def is_blacklisted(self, symbol: str) -> bool:
        """检查股票是否在黑名单中"""
        return symbol in self.get_all_blacklist()
    
    def get_blacklist_reason(self, symbol: str) -> str:
        """获取股票被拉黑的原因"""
        if symbol in self.manual_blacklist:
            return "手动拉黑"
        if symbol in self.st_stocks:
            return "ST股票"
        if symbol in self.delisting_stocks:
            return "退市股票"
        if symbol in self.suspended_stocks:
            return "停牌股票"
        return ""


if __name__ == "__main__":
    print("=" * 60)
    print("黑名单管理器测试")
    print("=" * 60)
    
    # 初始化
    manager = BlacklistManager()
    
    # 更新黑名单（不检查停牌，节省测试时间）
    print("\n更新ST股票列表...")
    st_stocks = manager.update_st_stocks()
    print(f"当前ST股票数量: {len(st_stocks)}")
    
    if st_stocks:
        print(f"示例: {list(st_stocks)[:5]}")
    
    print("\n更新退市股票列表...")
    delisting = manager.update_delisting_stocks()
    print(f"当前退市股票数量: {len(delisting)}")
    
    # 手动添加测试
    manager.add_manual('000001.SZ', '测试')
    
    # 获取完整黑名单
    all_blacklist = manager.get_all_blacklist()
    print(f"\n完整黑名单数量: {len(all_blacklist)}")
    
    # 分类查看
    categories = manager.get_blacklist_by_category()
    print("\n黑名单分类统计:")
    for category, symbols in categories.items():
        print(f"  {category}: {len(symbols)} 只")
    
    # 保存
    manager._save_cache()
    manager._save_blacklist_txt()
    
    print("\n" + "=" * 60)
    print("黑名单管理器测试完成")
    print("=" * 60)
