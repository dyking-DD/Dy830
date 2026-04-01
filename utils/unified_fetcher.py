"""
统一数据获取接口
整合 Tushare + AkShare，自动故障转移
"""
import pandas as pd
from typing import Optional, List
from pathlib import Path
import logging

from utils.data_fetcher import DataFetcher as TushareFetcher
from utils.akshare_fetcher import AkShareFetcher

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class UnifiedDataFetcher:
    """
    统一数据获取器
    
    优先级:
    1. Tushare Pro (稳定，数据质量高)
    2. AkShare (免费，实时性好，作为备选)
    """
    
    def __init__(self, 
                 tushare_config: str = "config/tushare.yaml",
                 prefer_tushare: bool = True):
        """初始化
        
        Args:
            tushare_config: Tushare配置文件
            prefer_tushare: 是否优先使用Tushare
        """
        self.prefer_tushare = prefer_tushare
        self.tushare = None
        self.akshare = None
        
        # 初始化Tushare
        if prefer_tushare:
            try:
                self.tushare = TushareFetcher(tushare_config)
                logger.info("✅ Tushare 初始化成功")
            except Exception as e:
                logger.warning(f"⚠️ Tushare 初始化失败: {e}，将使用AkShare")
                self.prefer_tushare = False
        
        # 初始化AkShare
        try:
            self.akshare = AkShareFetcher()
            logger.info("✅ AkShare 初始化成功")
        except Exception as e:
            logger.error(f"❌ AkShare 初始化失败: {e}")
            if self.tushare is None:
                raise RuntimeError("无可用数据源")
    
    def get_stock_list(self, refresh: bool = False) -> pd.DataFrame:
        """获取股票列表"""
        if self.prefer_tushare and self.tushare:
            try:
                return self.tushare.get_stock_list(refresh)
            except Exception as e:
                logger.warning(f"Tushare失败，切换到AkShare: {e}")
        
        return self.akshare.get_stock_list(refresh=refresh)
    
    def get_daily_data(self, 
                       code: str, 
                       start_date: str = None,
                       end_date: str = None,
                       prefer_source: str = None) -> pd.DataFrame:
        """获取日线数据
        
        Args:
            code: 股票代码 (支持 000001.SZ / 000001 格式)
            start_date: 开始日期
            end_date: 结束日期
            prefer_source: 'tushare' / 'akshare' / None(自动)
        """
        # 确定数据源
        use_tushare = self.prefer_tushare
        if prefer_source == 'tushare':
            use_tushare = True
        elif prefer_source == 'akshare':
            use_tushare = False
        
        # 标准化代码
        symbol = code.replace('.SZ', '').replace('.SH', '').replace('.BJ', '')
        
        # 尝试主数据源
        if use_tushare and self.tushare:
            try:
                # Tushare使用 ts_code 格式
                ts_code = code if '.' in code else self._to_ts_code(code)
                return self.tushare.get_daily_data(ts_code, start_date, end_date)
            except Exception as e:
                logger.warning(f"Tushare获取 {code} 失败: {e}")
        
        # 切换到AkShare
        if self.akshare:
            try:
                return self.akshare.get_daily_data(symbol, start_date=start_date, end_date=end_date)
            except Exception as e:
                logger.error(f"AkShare获取 {code} 失败: {e}")
        
        return pd.DataFrame()
    
    def get_index_data(self, code: str = "000001") -> pd.DataFrame:
        """获取指数数据"""
        code = code.replace('.SH', '').replace('.SZ', '')
        
        if self.prefer_tushare and self.tushare:
            try:
                ts_code = f"{code}.SH" if code.startswith('0') else f"{code}.SZ"
                return self.tushare.get_index_daily(ts_code)
            except Exception as e:
                logger.warning(f"Tushare失败: {e}")
        
        return self.akshare.get_index_data(code)
    
    def get_realtime_quote(self, code: str = None) -> pd.DataFrame:
        """获取实时行情（仅AkShare支持）"""
        return self.akshare.get_realtime_quote(code)
    
    def _to_ts_code(self, symbol: str) -> str:
        """转换代码格式: 000001 -> 000001.SZ"""
        symbol = symbol.replace('.SZ', '').replace('.SH', '').replace('.BJ', '')
        if symbol.startswith('6'):
            return f"{symbol}.SH"
        elif symbol.startswith('8') or symbol.startswith('4'):
            return f"{symbol}.BJ"
        else:
            return f"{symbol}.SZ"
    
    def download_history(self, 
                        codes: List[str],
                        start_date: str = None,
                        output_dir: str = "data/raw/daily") -> None:
        """批量下载历史数据
        
        Args:
            codes: 股票代码列表
            start_date: 开始日期
            output_dir: 输出目录
        """
        output_path = Path(output_dir)
        output_path.mkdir(parents=True, exist_ok=True)
        
        logger.info(f"开始下载 {len(codes)} 只股票历史数据...")
        
        for i, code in enumerate(codes, 1):
            try:
                df = self.get_daily_data(code, start_date)
                if not df.empty:
                    symbol = code.replace('.SZ', '').replace('.SH', '')
                    df.to_csv(output_path / f"{symbol}.csv", index=False)
                    logger.info(f"[{i}/{len(codes)}] {code} ✓ {len(df)}条记录")
                else:
                    logger.warning(f"[{i}/{len(codes)}] {code} ⚠ 无数据")
            except Exception as e:
                logger.error(f"[{i}/{len(codes)}] {code} ✗ 失败: {e}")


def test_unified_fetcher():
    """测试统一数据获取器"""
    print("=" * 60)
    print("统一数据获取器测试 (Tushare + AkShare)")
    print("=" * 60)
    
    fetcher = UnifiedDataFetcher()
    
    # 测试1: 股票列表
    print("\n1. 获取股票列表 (前5只):")
    stocks = fetcher.get_stock_list()
    print(stocks[['ts_code', 'name']].head())
    
    # 测试2: 日线数据
    print("\n2. 获取平安银行日线 (最近5天):")
    df = fetcher.get_daily_data('000001.SZ', start_date='20240301')
    if not df.empty:
        print(df[['trade_date', 'open', 'close', 'vol']].tail())
    
    # 测试3: 实时行情
    print("\n3. 获取实时行情 (前3只):")
    realtime = fetcher.get_realtime_quote()
    if not realtime.empty:
        print(realtime.head(3))
    
    print("\n" + "=" * 60)
    print("测试完成！")
    print("=" * 60)


if __name__ == "__main__":
    test_unified_fetcher()
