"""
数据获取模块 - Tushare接口封装
"""
import tushare as ts
import pandas as pd
from pathlib import Path
import yaml
from typing import Optional, List
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class DataFetcher:
    """Tushare数据获取器"""
    
    def __init__(self, config_path: str = "config/tushare.yaml"):
        """初始化
        
        Args:
            config_path: 配置文件路径
        """
        self.config = self._load_config(config_path)
        self.pro = self._init_tushare()
        self.data_dir = Path("data")
        self.data_dir.mkdir(exist_ok=True)
        
    def _load_config(self, path: str) -> dict:
        """加载配置"""
        with open(path, 'r', encoding='utf-8') as f:
            return yaml.safe_load(f)
    
    def _init_tushare(self):
        """初始化Tushare Pro"""
        token = self.config['tushare']['token']
        if token == "your_tushare_token_here":
            raise ValueError("请先配置Tushare token到 config/tushare.yaml")
        ts.set_token(token)
        return ts.pro_api()
    
    def get_stock_list(self, refresh: bool = False) -> pd.DataFrame:
        """获取股票列表
        
        Args:
            refresh: 是否强制刷新
            
        Returns:
            DataFrame with columns: ts_code, symbol, name, area, industry, list_date
        """
        cache_file = self.data_dir / "raw" / "stock_list.csv"
        
        if not refresh and cache_file.exists():
            logger.info("从缓存加载股票列表")
            return pd.read_csv(cache_file)
        
        logger.info("从Tushare获取股票列表")
        df = self.pro.stock_basic(exchange='', list_status='L', 
                                   fields='ts_code,symbol,name,area,industry,list_date')
        
        # 缓存
        cache_file.parent.mkdir(exist_ok=True)
        df.to_csv(cache_file, index=False)
        logger.info(f"获取到 {len(df)} 只股票")
        return df
    
    def get_daily_data(self, ts_code: str, start_date: str = None, 
                       end_date: str = None) -> pd.DataFrame:
        """获取日线数据
        
        Args:
            ts_code: 股票代码 (如 '000001.SZ')
            start_date: 开始日期 (YYYYMMDD)
            end_date: 结束日期 (YYYYMMDD)
            
        Returns:
            DataFrame with OHLCV data
        """
        if start_date is None:
            start_date = self.config['data']['daily']['start_date']
        if end_date is None:
            end_date = pd.Timestamp.now().strftime('%Y%m%d')
            
        logger.info(f"获取 {ts_code} 日线数据: {start_date} ~ {end_date}")
        
        df = self.pro.daily(ts_code=ts_code, start_date=start_date, end_date=end_date)
        if df.empty:
            logger.warning(f"{ts_code} 无数据")
            return df
            
        # 添加均线
        df['ma5'] = df['close'].rolling(5).mean()
        df['ma10'] = df['close'].rolling(10).mean()
        df['ma20'] = df['close'].rolling(20).mean()
        df['ma60'] = df['close'].rolling(60).mean()
        
        # 成交量均线
        df['vol_ma5'] = df['vol'].rolling(5).mean()
        df['vol_ma20'] = df['vol'].rolling(20).mean()
        
        return df.sort_values('trade_date')
    
    def get_daily_all(self, trade_date: str) -> pd.DataFrame:
        """获取某日所有股票日线数据
        
        Args:
            trade_date: 交易日期 (YYYYMMDD)
            
        Returns:
            DataFrame
        """
        logger.info(f"获取 {trade_date} 全市场日线数据")
        df = self.pro.daily(trade_date=trade_date)
        return df
    
    def get_index_daily(self, ts_code: str = "000001.SH") -> pd.DataFrame:
        """获取指数日线数据
        
        Args:
            ts_code: 指数代码，默认上证指数
            
        Returns:
            DataFrame
        """
        df = self.pro.index_daily(ts_code=ts_code)
        return df.sort_values('trade_date')
    
    def download_history_batch(self, stock_list: List[str], 
                               start_date: str = None) -> None:
        """批量下载历史数据
        
        Args:
            stock_list: 股票代码列表
            start_date: 起始日期
        """
        output_dir = self.data_dir / "raw" / "daily"
        output_dir.mkdir(parents=True, exist_ok=True)
        
        for i, ts_code in enumerate(stock_list, 1):
            try:
                df = self.get_daily_data(ts_code, start_date)
                if not df.empty:
                    df.to_csv(output_dir / f"{ts_code}.csv", index=False)
                    logger.info(f"[{i}/{len(stock_list)}] {ts_code} 下载完成，{len(df)} 条记录")
            except Exception as e:
                logger.error(f"{ts_code} 下载失败: {e}")
    
    def get_trade_cal(self, start_date: str, end_date: str) -> pd.DataFrame:
        """获取交易日历
        
        Returns:
            DataFrame with is_open标记
        """
        return self.pro.trade_cal(exchange='SSE', start_date=start_date, end_date=end_date)


if __name__ == "__main__":
    # 测试
    fetcher = DataFetcher()
    
    # 获取股票列表
    stocks = fetcher.get_stock_list()
    print(f"股票总数: {len(stocks)}")
    print(stocks.head(10))
    
    # 获取单只股票数据
    df = fetcher.get_daily_data('000001.SZ', '20240101')
    print(f"\n平安银行数据:")
    print(df.tail())
