"""
Data Sources Module

Provides unified interface for fetching stock data from multiple sources:
- Yahoo Finance (US/HK stocks)
- AkShare (A-shares)
- Tushare (A-shares backup)
"""

from .base import DataSourceBase


class YahooFinanceDataSource(DataSourceBase):
    """Yahoo Finance data source for US and HK stocks."""
    
    def __init__(self):
        super().__init__()
        try:
            import yfinance as yf
            self.yf = yf
        except ImportError:
            raise ImportError("yfinance is required. Install with: pip install yfinance")
    
    def get_quote(self, symbol: str) -> dict:
        """
        Get real-time quote from Yahoo Finance.
        
        Args:
            symbol: Stock symbol (e.g., 'AAPL', '0700.HK')
            
        Returns:
            Dictionary with quote data
        """
        try:
            ticker = self.yf.Ticker(symbol)
            data = ticker.info
            
            return {
                'symbol': symbol,
                'price': data.get('currentPrice', data.get('regularMarketPrice', data.get('previousClose', 0))),
                'change': data.get('regularMarketChange', 0),
                'change_percent': data.get('regularMarketChangePercent', 0),
                'volume': data.get('volume', 0),
                'market_cap': data.get('marketCap', 0),
                'pe_ratio': data.get('trailingPE', 0),
                'high_52w': data.get('fiftyTwoWeekHigh', 0),
                'low_52w': data.get('fiftyTwoWeekLow', 0),
                'source': 'yahoo',
            }
        except Exception as e:
            self.logger.error(f"Yahoo Finance error for {symbol}: {e}")
            return {'symbol': symbol, 'price': 0, 'error': str(e), 'source': 'yahoo'}
    
    def get_history(self, symbol: str, period: str = '6mo') -> dict:
        """Get historical data."""
        try:
            ticker = self.yf.Ticker(symbol)
            hist = ticker.history(period=period)
            
            if len(hist) == 0:
                return {}
            
            # Calculate moving averages
            ma5 = hist['Close'].rolling(window=5).mean().iloc[-1]
            ma10 = hist['Close'].rolling(window=10).mean().iloc[-1]
            ma20 = hist['Close'].rolling(window=20).mean().iloc[-1]
            ma60 = hist['Close'].rolling(window=60).mean().iloc[-1]
            
            current_price = hist['Close'].iloc[-1]
            trend = 'bullish' if ma5 > ma10 > ma20 else 'bearish' if ma5 < ma10 < ma20 else 'neutral'
            
            return {
                'ma5': round(ma5, 2),
                'ma10': round(ma10, 2),
                'ma20': round(ma20, 2),
                'ma60': round(ma60, 2),
                'trend': trend,
                'source': 'yahoo',
            }
        except Exception as e:
            self.logger.error(f"Yahoo Finance history error for {symbol}: {e}")
            return {}


class AkShareDataSource(DataSourceBase):
    """AkShare data source for A-shares."""
    
    def __init__(self):
        super().__init__()
        try:
            import akshare as ak
            self.ak = ak
        except ImportError:
            raise ImportError("akshare is required. Install with: pip install akshare")
    
    def get_quote(self, code: str) -> dict:
        """
        Get real-time quote from AkShare.
        
        Args:
            code: A-share stock code (e.g., '600519', '000001')
            
        Returns:
            Dictionary with quote data
        """
        try:
            # Get all A-share quotes
            df = self.ak.stock_zh_a_spot_em()
            stock_data = df[df['代码'] == code]
            
            if len(stock_data) == 0:
                return {'symbol': code, 'price': 0, 'error': 'Stock not found', 'source': 'akshare'}
            
            stock_data = stock_data.iloc[0]
            
            return {
                'symbol': code,
                'price': float(stock_data['最新价']),
                'change': float(stock_data['涨跌额']),
                'change_percent': float(stock_data['涨跌幅']),
                'volume': float(stock_data['成交量']),
                'market_cap': float(stock_data['总市值']),
                'pe_ratio': float(stock_data['市盈率 - 动态']),
                'source': 'akshare',
            }
        except Exception as e:
            self.logger.error(f"AkShare error for {code}: {e}")
            return {'symbol': code, 'price': 0, 'error': str(e), 'source': 'akshare'}
    
    def get_history(self, code: str, period: str = '6mo') -> dict:
        """Get historical data from AkShare."""
        # Simplified - return basic technical indicators
        return {
            'ma5': 0,
            'ma10': 0,
            'ma20': 0,
            'ma60': 0,
            'trend': 'neutral',
            'source': 'akshare',
        }


class TushareDataSource(DataSourceBase):
    """Tushare data source for A-shares (backup)."""
    
    def __init__(self, token: str = None):
        super().__init__()
        self.token = token or os.getenv('TUSHARE_TOKEN')
        
        if not self.token:
            self.logger.warning("TUSHARE_TOKEN not configured")
            return
        
        try:
            import tushare as ts
            ts.set_token(self.token)
            self.pro = ts.pro_api()
        except ImportError:
            raise ImportError("tushare is required. Install with: pip install tushare")
    
    def get_quote(self, code: str) -> dict:
        """
        Get real-time quote from Tushare.
        
        Args:
            code: A-share stock code (e.g., '600519', '000001')
            
        Returns:
            Dictionary with quote data
        """
        if not self.token:
            return {'symbol': code, 'price': 0, 'error': 'Tushare token not configured', 'source': 'tushare'}
        
        try:
            # Convert code to Tushare format
            if code.startswith('6'):
                ts_code = f"{code}.SH"
            else:
                ts_code = f"{code}.SZ"
            
            # Get quote
            df = self.pro.quote(ts_code=ts_code)
            
            if len(df) == 0:
                return {'symbol': code, 'price': 0, 'error': 'Stock not found', 'source': 'tushare'}
            
            data = df.iloc[0]
            
            return {
                'symbol': code,
                'price': float(data.get('close', 0)),
                'change': float(data.get('change', 0)),
                'change_percent': float(data.get('pct_chg', 0)),
                'volume': float(data.get('vol', 0)) * 100,  # Convert to shares
                'market_cap': float(data.get('total_mv', 0)) * 10000,  # Convert to yuan
                'pe_ratio': float(data.get('pe', 0)),
                'source': 'tushare',
            }
        except Exception as e:
            self.logger.error(f"Tushare error for {code}: {e}")
            return {'symbol': code, 'price': 0, 'error': str(e), 'source': 'tushare'}
    
    def get_history(self, code: str, period: str = '6mo') -> dict:
        """Get historical data from Tushare."""
        return {
            'ma5': 0,
            'ma10': 0,
            'ma20': 0,
            'ma60': 0,
            'trend': 'neutral',
            'source': 'tushare',
        }
