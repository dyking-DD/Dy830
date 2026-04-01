"""
AkShare 数据获取模块 - 免费数据源
作为 Tushare 的备选方案
"""
import akshare as ak
import pandas as pd
from pathlib import Path
from typing import Optional, List
import logging
from datetime import datetime

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class AkShareFetcher:
    """
    AkShare 免费数据获取器
    
    特点：
    - 完全免费，无需token
    - 支持实时行情
    - 稳定性不如Tushare（偶尔接口变动）
    """
    
    def __init__(self, cache_dir: str = "data/raw/akshare"):
        """初始化
        
        Args:
            cache_dir: 缓存目录
        """
        self.cache_dir = Path(cache_dir)
        self.cache_dir.mkdir(parents=True, exist_ok=True)
        
    def get_stock_list(self, market: str = "all", refresh: bool = False) -> pd.DataFrame:
        """获取股票列表
        
        Args:
            market: 'all'全部, 'sh'沪市, 'sz'深市, 'bj'北交所
            refresh: 是否强制刷新
            
        Returns:
            DataFrame: ts_code, name, industry
        """
        cache_file = self.cache_dir / f"stock_list_{market}.csv"
        
        if not refresh and cache_file.exists():
            logger.info("从缓存加载股票列表")
            return pd.read_csv(cache_file)
        
        logger.info(f"从AkShare获取{market}股票列表")
        
        try:
            if market == "sh":
                df = ak.stock_sh_a_spot_em()
            elif market == "sz":
                df = ak.stock_sz_a_spot_em()
            else:
                # 获取全部
                df_sh = ak.stock_sh_a_spot_em()
                df_sz = ak.stock_sz_a_spot_em()
                df = pd.concat([df_sh, df_sz], ignore_index=True)
            
            # 标准化列名
            df = df.rename(columns={
                '代码': 'symbol',
                '名称': 'name',
                '最新价': 'price',
                '涨跌幅': 'pct_change',
                '成交量': 'volume',
                '成交额': 'amount',
                '所属行业': 'industry'
            })
            
            # 生成ts_code格式
            df['ts_code'] = df['symbol'].apply(
                lambda x: x + '.SH' if x.startswith('6') else x + '.SZ'
            )
            
            # 缓存
            df.to_csv(cache_file, index=False)
            logger.info(f"获取到 {len(df)} 只股票")
            return df
            
        except Exception as e:
            logger.error(f"获取股票列表失败: {e}")
            if cache_file.exists():
                logger.info("使用缓存数据")
                return pd.read_csv(cache_file)
            raise
    
    def get_daily_data(self, symbol: str, period: str = "daily", 
                       start_date: str = None, end_date: str = None) -> pd.DataFrame:
        """获取日线数据
        
        Args:
            symbol: 股票代码 (如 '000001' 或 '000001.SZ')
            period: 'daily'日线, 'weekly'周线, 'monthly'月线
            start_date: 开始日期 (YYYYMMDD)
            end_date: 结束日期 (YYYYMMDD)
            
        Returns:
            DataFrame with OHLCV data
        """
        # 标准化代码
        symbol = symbol.replace('.SZ', '').replace('.SH', '').replace('.BJ', '')
        
        logger.info(f"获取 {symbol} 日线数据")
        
        try:
            # AkShare获取历史数据
            df = ak.stock_zh_a_hist(
                symbol=symbol,
                period=period,
                start_date=start_date or "19700101",
                end_date=end_date or datetime.now().strftime('%Y%m%d'),
                adjust="qfq"  # 前复权
            )
            
            if df.empty:
                logger.warning(f"{symbol} 无数据")
                return df
            
            # 标准化列名
            df = df.rename(columns={
                '日期': 'trade_date',
                '开盘': 'open',
                '收盘': 'close',
                '最高': 'high',
                '最低': 'low',
                '成交量': 'vol',
                '成交额': 'amount',
                '振幅': 'amplitude',
                '涨跌幅': 'pct_chg',
                '涨跌额': 'change',
                '换手率': 'turnover'
            })
            
            # 添加ts_code
            exchange = 'SH' if symbol.startswith('6') else 'SZ'
            df['ts_code'] = f"{symbol}.{exchange}"
            
            # 日期格式转换
            df['trade_date'] = pd.to_datetime(df['trade_date']).dt.strftime('%Y%m%d')
            
            # 计算均线
            for period in [5, 10, 20, 60]:
                df[f'ma{period}'] = df['close'].rolling(period).mean()
            
            # 成交量均线
            df['vol_ma5'] = df['vol'].rolling(5).mean()
            df['vol_ma20'] = df['vol'].rolling(20).mean()
            
            return df.sort_values('trade_date')
            
        except Exception as e:
            logger.error(f"获取 {symbol} 数据失败: {e}")
            return pd.DataFrame()
    
    def get_realtime_quote(self, symbol: str = None) -> pd.DataFrame:
        """获取实时行情
        
        Args:
            symbol: 股票代码 (None则获取全部A股)
            
        Returns:
            DataFrame
        """
        logger.info("获取实时行情...")
        
        try:
            if symbol:
                # 单只股票实时行情
                df = ak.stock_bid_ask_em(symbol=symbol)
                return df
            else:
                # 全部A股实时行情
                df = ak.stock_zh_a_spot_em()
                return df
                
        except Exception as e:
            logger.error(f"获取实时行情失败: {e}")
            return pd.DataFrame()
    
    def get_index_data(self, symbol: str = "000001") -> pd.DataFrame:
        """获取指数数据
        
        Args:
            symbol: 指数代码
                     000001=上证指数, 399001=深证成指, 
                     399006=创业板指, 000300=沪深300
        """
        logger.info(f"获取指数 {symbol} 数据")
        
        try:
            df = ak.index_zh_a_hist(symbol=symbol, period="daily")
            
            df = df.rename(columns={
                '日期': 'trade_date',
                '开盘': 'open',
                '收盘': 'close',
                '最高': 'high',
                '最低': 'low',
                '成交量': 'vol',
                '成交额': 'amount',
                '振幅': 'amplitude',
                '涨跌幅': 'pct_chg',
                '涨跌额': 'change',
                '换手率': 'turnover'
            })
            
            df['trade_date'] = pd.to_datetime(df['trade_date']).dt.strftime('%Y%m%d')
            df['ts_code'] = symbol
            
            return df.sort_values('trade_date')
            
        except Exception as e:
            logger.error(f"获取指数数据失败: {e}")
            return pd.DataFrame()
    
    def get_financial_data(self, symbol: str) -> pd.DataFrame:
        """获取财务数据
        
        Args:
            symbol: 股票代码
        """
        symbol = symbol.replace('.SZ', '').replace('.SH', '')
        
        logger.info(f"获取 {symbol} 财务数据")
        
        try:
            # 主要财务指标
            df = ak.stock_financial_report_sina(stock=symbol, symbol="利润表")
            return df
        except Exception as e:
            logger.error(f"获取财务数据失败: {e}")
            return pd.DataFrame()
    
    def download_batch(self, symbols: List[str], save_dir: str = None) -> None:
        """批量下载历史数据
        
        Args:
            symbols: 股票代码列表
            save_dir: 保存目录
        """
        if save_dir is None:
            save_dir = self.cache_dir / "daily"
        else:
            save_dir = Path(save_dir)
        save_dir.mkdir(parents=True, exist_ok=True)
        
        logger.info(f"批量下载 {len(symbols)} 只股票数据...")
        
        for i, symbol in enumerate(symbols, 1):
            try:
                df = self.get_daily_data(symbol)
                if not df.empty:
                    filename = symbol.replace('.SZ', '').replace('.SH', '')
                    df.to_csv(save_dir / f"{filename}.csv", index=False)
                    logger.info(f"[{i}/{len(symbols)}] {symbol} 下载完成，{len(df)} 条记录")
            except Exception as e:
                logger.error(f"{symbol} 下载失败: {e}")
    
    def get_news(self, symbol: str = None) -> pd.DataFrame:
        """获取个股新闻
        
        Args:
            symbol: 股票代码 (None则获取市场要闻)
        """
        try:
            if symbol:
                symbol = symbol.replace('.SZ', '').replace('.SH', '')
                df = ak.stock_news_em(symbol=symbol)
            else:
                df = ak.stock_news_em()
            return df
        except Exception as e:
            logger.error(f"获取新闻失败: {e}")
            return pd.DataFrame()


def test_akshare():
    """测试AkShare接口"""
    fetcher = AkShareFetcher()
    
    print("=" * 50)
    print("AkShare 接口测试")
    print("=" * 50)
    
    # 1. 测试股票列表
    print("\n1. 获取股票列表 (前10只):")
    stocks = fetcher.get_stock_list()
    print(stocks[['ts_code', 'name']].head(10)) if 'industry' not in stocks.columns else print(stocks[['ts_code', 'name', 'industry']].head(10))
    
    # 2. 测试日线数据
    print("\n2. 获取平安银行日线数据 (最近5天):")
    df = fetcher.get_daily_data('000001', start_date='20240301')
    print(df[['trade_date', 'open', 'close', 'high', 'low', 'vol']].tail())
    
    # 3. 测试指数数据
    print("\n3. 获取上证指数数据 (最近5天):")
    index_df = fetcher.get_index_data('000001')
    print(index_df[['trade_date', 'close', 'pct_chg']].tail())
    
    print("\n" + "=" * 50)
    print("测试完成！")
    print("=" * 50)


if __name__ == "__main__":
    test_akshare()
