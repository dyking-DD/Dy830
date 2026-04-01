"""
东方财富 Choice 终端交易接口

基于 Choice 金融终端的 Python API
需要安装 Choice 终端并获取授权

文档: http://choice.eastmoney.com/
"""

import logging
import time
from datetime import datetime
from typing import Dict, List, Optional, Any
from dataclasses import dataclass

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


@dataclass
class ChoiceOrder:
    """Choice 订单结构"""
    order_id: str
    symbol: str
    action: str
    quantity: int
    price: float
    order_type: str
    status: str
    created_at: str
    filled_quantity: int = 0
    avg_price: float = 0.0


class ChoiceTrader:
    """
    东方财富 Choice 终端交易接口
    
    使用前请确保：
    1. 已安装 Choice 金融终端（策略版）
    2. 已申请量化交易权限
    3. 终端已登录并保持运行
    """
    
    def __init__(self):
        self.api = None
        self.connected = False
        self.account_id = None
        
    def connect(self) -> bool:
        """连接 Choice 终端"""
        try:
            from EmQuantAPI import EmQuantAPI
            
            self.api = EmQuantAPI()
            result = self.api.start()
            
            if result == 0:
                self.connected = True
                logger.info("✅ Choice 终端连接成功")
                
                account_info = self.get_account_info()
                if account_info:
                    self.account_id = account_info.get('account_id')
                    logger.info(f"账户: {self.account_id}")
                
                return True
            else:
                logger.error(f"❌ Choice 连接失败，错误码: {result}")
                return False
                
        except ImportError:
            logger.error("❌ 未找到 EmQuantAPI，请确保已安装 Choice 金融终端")
            logger.error("   下载地址: http://choice.eastmoney.com/")
            return False
        except Exception as e:
            logger.error(f"❌ 连接异常: {e}")
            return False
    
    def disconnect(self):
        """断开连接"""
        if self.api and self.connected:
            try:
                self.api.stop()
                self.connected = False
                logger.info("Choice 连接已断开")
            except Exception as e:
                logger.error(f"断开连接失败: {e}")
    
    def get_account_info(self) -> Optional[Dict]:
        """获取账户信息"""
        if not self.connected or not self.api:
            logger.error("未连接 Choice 终端")
            return None
        
        try:
            result = self.api.queryAccount()
            
            if result:
                return {
                    'account_id': result.get('AccountID', ''),
                    'total_assets': float(result.get('TotalAsset', 0)),
                    'available_cash': float(result.get('Available', 0)),
                    'market_value': float(result.get('MarketValue', 0)),
                    'frozen_cash': float(result.get('Frozen', 0)),
                    'total_pnl': float(result.get('TotalProfit', 0))
                }
            return None
            
        except Exception as e:
            logger.error(f"查询账户失败: {e}")
            return None
    
    def get_positions(self) -> List[Dict]:
        """获取持仓列表"""
        if not self.connected or not self.api:
            logger.error("未连接 Choice 终端")
            return []
        
        try:
            result = self.api.queryPosition()
            positions = []
            
            if result and isinstance(result, list):
                for pos in result:
                    positions.append({
                        'symbol': pos.get('StockCode', ''),
                        'name': pos.get('StockName', ''),
                        'quantity': int(pos.get('Volume', 0)),
                        'available': int(pos.get('AvailableVolume', 0)),
                        'avg_cost': float(pos.get('AvgCost', 0)),
                        'current_price': float(pos.get('CurrentPrice', 0)),
                        'market_value': float(pos.get('MarketValue', 0)),
                        'unrealized_pnl': float(pos.get('Profit', 0)),
                        'unrealized_pnl_pct': float(pos.get('ProfitRate', 0))
                    })
            
            return positions
            
        except Exception as e:
            logger.error(f"查询持仓失败: {e}")
            return []
    
    def submit_order(
        self,
        symbol: str,
        action: str,
        quantity: int,
        price: Optional[float] = None,
        order_type: str = "limit"
    ) -> Optional[str]:
        """提交订单"""
        if not self.connected or not self.api:
            logger.error("未连接 Choice 终端")
            return None
        
        try:
            side = 0 if action == 'buy' else 1
            order_type_code = 0 if order_type == 'limit' else 1
            
            if order_type == 'market':
                price = 0.0
            elif price is None:
                logger.error("限价单必须指定价格")
                return None
            
            order_param = {
                'StockCode': symbol,
                'Price': price,
                'Volume': quantity,
                'Side': side,
                'OrderType': order_type_code
            }
            
            logger.info(f"提交订单: {action.upper()} {symbol} {quantity}股 @ {price}")
            
            result = self.api.trade(order_param)
            
            if result and result.get('OrderID'):
                order_id = str(result['OrderID'])
                logger.info(f"✅ 订单提交成功: {order_id}")
                return order_id
            else:
                error_msg = result.get('ErrorMsg', '未知错误') if result else '无返回'
                logger.error(f"❌ 订单提交失败: {error_msg}")
                return None
                
        except Exception as e:
            logger.error(f"下单异常: {e}")
            return None
    
    def cancel_order(self, order_id: str) -> bool:
        """撤单"""
        if not self.connected or not self.api:
            logger.error("未连接 Choice 终端")
            return False
        
        try:
            result = self.api.cancelOrder({'OrderID': order_id})
            
            if result and result.get('Result') == 0:
                logger.info(f"✅ 撤单成功: {order_id}")
                return True
            else:
                error_msg = result.get('ErrorMsg', '未知错误') if result else '无返回'
                logger.error(f"❌ 撤单失败: {error_msg}")
                return False
                
        except Exception as e:
            logger.error(f"撤单异常: {e}")
            return False
    
    def get_order_status(self, order_id: str) -> Optional[Dict]:
        """查询订单状态"""
        if not self.connected or not self.api:
            logger.error("未连接 Choice 终端")
            return None
        
        try:
            result = self.api.queryOrder({'OrderID': order_id})
            
            if result:
                return {
                    'order_id': str(result.get('OrderID', '')),
                    'symbol': result.get('StockCode', ''),
                    'action': 'buy' if result.get('Side') == 0 else 'sell',
                    'quantity': int(result.get('Volume', 0)),
                    'price': float(result.get('Price', 0)),
                    'filled_quantity': int(result.get('FilledVolume', 0)),
                    'avg_price': float(result.get('AvgPrice', 0)),
                    'status': self._parse_order_status(result.get('Status')),
                    'created_at': result.get('OrderTime', '')
                }
            return None
            
        except Exception as e:
            logger.error(f"查询订单失败: {e}")
            return None
    
    def get_quote(self, symbol: str) -> Optional[Dict]:
        """获取实时行情"""
        if not self.connected or not self.api:
            logger.error("未连接 Choice 终端")
            return None
        
        try:
            result = self.api.getQuote(symbol)
            
            if result:
                return {
                    'symbol': symbol,
                    'price': float(result.get('LastPrice', 0)),
                    'open': float(result.get('Open', 0)),
                    'high': float(result.get('High', 0)),
                    'low': float(result.get('Low', 0)),
                    'pre_close': float(result.get('PreClose', 0)),
                    'volume': int(result.get('Volume', 0)),
                    'amount': float(result.get('Amount', 0)),
                    'bid1': float(result.get('BidPrice1', 0)),
                    'ask1': float(result.get('AskPrice1', 0)),
                    'bid_vol1': int(result.get('BidVolume1', 0)),
                    'ask_vol1': int(result.get('AskVolume1', 0)),
                    'time': result.get('Time', '')
                }
            return None
            
        except Exception as e:
            logger.error(f"获取行情失败: {e}")
            return None
    
    def _parse_order_status(self, status_code) -> str:
        """解析订单状态码"""
        status_map = {
            0: 'pending',
            1: 'reported',
            2: 'partial',
            3: 'filled',
            4: 'cancelled',
            5: 'rejected',
            6: 'unknown'
        }
        return status_map.get(status_code, 'unknown')


def create_choice_trader() -> ChoiceTrader:
    """创建 Choice 交易器实例"""
    return ChoiceTrader()


def test_connection():
    """测试连接"""
    trader = create_choice_trader()
    
    if trader.connect():
        print("✅ 连接成功")
        
        account = trader.get_account_info()
        if account:
            print(f"\n账户信息:")
            print(f"  总资产: {account['total_assets']:,.2f}")
            print(f"  可用资金: {account['available_cash']:,.2f}")
            print(f"  持仓市值: {account['market_value']:,.2f}")
        
        positions = trader.get_positions()
        print(f"\n持仓数量: {len(positions)}")
        for pos in positions[:5]:
            print(f"  {pos['symbol']} {pos['name']}: {pos['quantity']}股")
        
        trader.disconnect()
    else:
        print("❌ 连接失败")


if __name__ == "__main__":
    test_connection()
