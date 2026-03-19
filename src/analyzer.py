#!/usr/bin/env python3
"""
Stock Analysis Skill for OpenClaw

Intelligent stock analysis system with:
- Multi-market support (A/H/US stocks)
- Real-time news and sentiment analysis
- Technical and fundamental analysis
- AI-powered decision dashboard
- Multi-channel notifications (uses OpenClaw's built-in messaging)
"""

import os
import json
from typing import List, Dict, Optional
from pathlib import Path
from datetime import datetime, timedelta
import yahoofinance as yf
import akshare as ak


class StockAnalyzer:
    """Stock analysis engine."""
    
    def __init__(self):
        """Initialize stock analyzer."""
        self.cache_dir = Path(__file__).parent.parent / 'cache'
        self.cache_dir.mkdir(parents=True, exist_ok=True)
    
    def get_realtime_quotes(self, stock_codes: List[str]) -> Dict[str, Dict]:
        """
        Get real-time quotes for multiple stocks.
        
        Args:
            stock_codes: List of stock codes (e.g., ['600519', 'hk00700', 'AAPL'])
            
        Returns:
            Dictionary with stock data
        """
        quotes = {}
        
        for code in stock_codes:
            try:
                # Detect market
                if code.startswith('hk'):
                    # Hong Kong stock
                    symbol = code.replace('hk', '') + '.HK'
                    data = yf.Ticker(symbol).info
                elif code.startswith('us') or code in ['SPX', 'DJI', 'IXIC']:
                    # US stock
                    symbol = code.replace('us', '')
                    data = yf.Ticker(symbol).info
                else:
                    # A-share (use AkShare)
                    symbol = code
                    data = self._get_akshare_quote(symbol)
                
                quotes[code] = {
                    'symbol': code,
                    'price': data.get('currentPrice', data.get('regularMarketPrice', 0)),
                    'change': data.get('regularMarketChange', 0),
                    'change_percent': data.get('regularMarketChangePercent', 0),
                    'volume': data.get('volume', 0),
                    'market_cap': data.get('marketCap', 0),
                    'pe_ratio': data.get('trailingPE', 0),
                    'high_52w': data.get('fiftyTwoWeekHigh', 0),
                    'low_52w': data.get('fiftyTwoWeekLow', 0),
                }
            except Exception as e:
                quotes[code] = {'error': str(e)}
        
        return quotes
    
    def _get_akshare_quote(self, code: str) -> Dict:
        """Get A-share quote from AkShare."""
        try:
            # AkShare real-time quote
            df = ak.stock_zh_a_spot_em()
            stock_data = df[df['代码'] == code].iloc[0]
            return {
                'currentPrice': stock_data['最新价'],
                'regularMarketChange': stock_data['涨跌额'],
                'regularMarketChangePercent': stock_data['涨跌幅'],
                'volume': stock_data['成交量'],
            }
        except Exception as e:
            return {}
    
    def get_technical_analysis(self, stock_code: str, period: str = '6mo') -> Dict:
        """
        Get technical analysis for a stock.
        
        Args:
            stock_code: Stock code
            period: Time period (1d, 5d, 1mo, 3mo, 6mo, 1y, 2y, 5y, 10y, ytd, max)
            
        Returns:
            Technical indicators
        """
        try:
            # Detect market and get history
            if stock_code.startswith('hk'):
                symbol = stock_code.replace('hk', '') + '.HK'
            elif stock_code.startswith('us'):
                symbol = stock_code.replace('us', '')
            else:
                # A-share
                return self._get_akshare_technical(stock_code)
            
            ticker = yf.Ticker(symbol)
            hist = ticker.history(period=period)
            
            # Calculate moving averages
            ma5 = hist['Close'].rolling(window=5).mean().iloc[-1]
            ma10 = hist['Close'].rolling(window=10).mean().iloc[-1]
            ma20 = hist['Close'].rolling(window=20).mean().iloc[-1]
            ma60 = hist['Close'].rolling(window=60).mean().iloc[-1]
            
            # Determine trend
            current_price = hist['Close'].iloc[-1]
            trend = 'bullish' if ma5 > ma10 > ma20 else 'bearish' if ma5 < ma10 < ma20 else 'neutral'
            
            return {
                'ma5': round(ma5, 2),
                'ma10': round(ma10, 2),
                'ma20': round(ma20, 2),
                'ma60': round(ma60, 2),
                'trend': trend,
                'rsi': 50,  # Simplified
                'macd': 0,  # Simplified
            }
        except Exception as e:
            return {'error': str(e)}
    
    def _get_akshare_technical(self, code: str) -> Dict:
        """Get A-share technical analysis from AkShare."""
        try:
            # Simplified technical analysis for A-shares
            return {
                'ma5': 0,
                'ma10': 0,
                'ma20': 0,
                'ma60': 0,
                'trend': 'neutral',
            }
        except Exception:
            return {}
    
    def get_news_sentiment(self, stock_code: str, days: int = 3) -> Dict:
        """
        Get news and sentiment analysis using Tavily Search or OpenClaw's web search.
        
        Args:
            stock_code: Stock code
            days: Number of days to search news
            
        Returns:
            News and sentiment data
        """
        try:
            # Try to use Tavily Search API
            tavily_api_key = os.getenv('TAVILY_API_KEY')
            
            if tavily_api_key:
                return self._get_tavily_sentiment(stock_code, tavily_api_key, days)
            else:
                # Fallback: Use OpenClaw's built-in web search if available
                return self._get_opclaw_search_sentiment(stock_code, days)
        except Exception as e:
            return {
                'news_count': 0,
                'sentiment': 'neutral',
                'sentiment_score': 0.5,
                'key_topics': [],
                'error': str(e),
            }
    
    def _get_tavily_sentiment(self, stock_code: str, api_key: str, days: int) -> Dict:
        """Get news sentiment using Tavily Search API."""
        try:
            # Search for recent news
            search_query = f"{stock_code} stock news analysis {days} days"
            
            url = "https://api.tavily.com/search"
            headers = {
                'Content-Type': 'application/json',
                'Authorization': f'Bearer {api_key}'
            }
            data = {
                'query': search_query,
                'search_depth': 'advanced',
                'max_results': 10,
                'include_answer': True,
                'include_raw_content': False
            }
            
            response = requests.post(url, json=data, headers=headers, timeout=30)
            response.raise_for_status()
            
            results = response.json()
            
            # Analyze sentiment from results
            news_items = []
            positive_count = 0
            negative_count = 0
            neutral_count = 0
            
            for result in results.get('results', []):
                title = result.get('title', '')
                content = result.get('content', '')
                
                # Simple sentiment analysis based on keywords
                positive_words = ['buy', 'upgrade', 'beat', 'surge', 'gain', 'rise', 'positive', 'bullish', 'outperform', 'growth']
                negative_words = ['sell', 'downgrade', 'miss', 'drop', 'loss', 'fall', 'negative', 'bearish', 'underperform', 'decline']
                
                text = (title + ' ' + content).lower()
                
                pos_score = sum(1 for word in positive_words if word in text)
                neg_score = sum(1 for word in negative_words if word in text)
                
                if pos_score > neg_score:
                    positive_count += 1
                    sentiment = 'positive'
                elif neg_score > pos_score:
                    negative_count += 1
                    sentiment = 'negative'
                else:
                    neutral_count += 1
                    sentiment = 'neutral'
                
                news_items.append({
                    'title': title,
                    'url': result.get('url', ''),
                    'sentiment': sentiment,
                    'published_date': result.get('published_date', ''),
                })
            
            # Calculate overall sentiment
            total = positive_count + negative_count + neutral_count
            if total == 0:
                overall_sentiment = 'neutral'
                sentiment_score = 0.5
            else:
                sentiment_score = (positive_count * 1.0 + neutral_count * 0.5 + negative_count * 0.0) / total
                
                if sentiment_score > 0.6:
                    overall_sentiment = 'positive'
                elif sentiment_score < 0.4:
                    overall_sentiment = 'negative'
                else:
                    overall_sentiment = 'neutral'
            
            return {
                'news_count': len(news_items),
                'sentiment': overall_sentiment,
                'sentiment_score': round(sentiment_score, 2),
                'positive_count': positive_count,
                'negative_count': negative_count,
                'neutral_count': neutral_count,
                'key_topics': [],  # Could extract from news
                'news_items': news_items[:5],  # Top 5 news
            }
            
        except Exception as e:
            return {
                'news_count': 0,
                'sentiment': 'neutral',
                'sentiment_score': 0.5,
                'error': str(e),
            }
    
    def _get_opclaw_search_sentiment(self, stock_code: str, days: int) -> Dict:
        """
        Get news sentiment using OpenClaw's built-in search capabilities.
        This is a fallback when Tavily API is not configured.
        """
        # In a real OpenClaw integration, this would call OpenClaw's search tools
        # For now, return basic placeholder
        return {
            'news_count': 0,
            'sentiment': 'neutral',
            'sentiment_score': 0.5,
            'key_topics': [],
            'note': 'Configure TAVILY_API_KEY for news sentiment analysis',
        }
    
    def generate_decision_dashboard(self, stock_code: str, quotes: Dict, technical: Dict, news: Dict) -> Dict:
        """
        Generate AI-powered decision dashboard with news sentiment integration.
        
        Args:
            stock_code: Stock code
            quotes: Real-time quotes
            technical: Technical analysis
            news: News and sentiment
            
        Returns:
            Decision dashboard with buy/sell/hold recommendation
        """
        # Simple rule-based analysis (would use LLM in production)
        price = quotes.get('price', 0)
        change_percent = quotes.get('change_percent', 0)
        trend = technical.get('trend', 'neutral')
        
        # News sentiment
        sentiment = news.get('sentiment', 'neutral')
        sentiment_score = news.get('sentiment_score', 0.5)
        news_count = news.get('news_count', 0)
        
        # Scoring system
        score = 50  # Base score
        
        # Technical score
        if trend == 'bullish':
            score += 20
        elif trend == 'bearish':
            score -= 20
        
        # Price change score
        if change_percent > 3:
            score += 10
        elif change_percent < -3:
            score -= 10
        
        # News sentiment score (adds up to ±20 points)
        if sentiment == 'positive':
            score += int(sentiment_score * 20)
        elif sentiment == 'negative':
            score -= int((1 - sentiment_score) * 20)
        
        # Determine recommendation
        if score >= 70:
            recommendation = 'BUY'
            action = '🟢 买入'
        elif score <= 30:
            recommendation = 'SELL'
            action = '🔴 卖出'
        else:
            recommendation = 'HOLD'
            action = '🟡 观望'
        
        # Calculate target and stop-loss prices
        if recommendation == 'BUY':
            target_price = round(price * 1.1, 2)
            stop_loss = round(price * 0.95, 2)
        elif recommendation == 'SELL':
            target_price = round(price * 0.9, 2)
            stop_loss = round(price * 1.05, 2)
        else:
            target_price = round(price * 1.05, 2)
            stop_loss = round(price * 0.95, 2)
        
        # Build reasoning with news sentiment
        reasoning_parts = [f"技术趋势：{trend}", f"涨跌幅：{change_percent:.2f}%"]
        if news_count > 0:
            reasoning_parts.append(f"舆情：{sentiment} ({sentiment_score:.2f})")
        
        return {
            'stock_code': stock_code,
            'recommendation': recommendation,
            'action': action,
            'score': score,
            'current_price': price,
            'target_price': target_price,
            'stop_loss': stop_loss,
            'confidence': 'high' if score >= 70 or score <= 30 else 'medium',
            'reasoning': ', '.join(reasoning_parts),
            'news_sentiment': sentiment,
            'news_count': news_count,
        }


def analyze_stocks(stock_codes: List[str], use_llm: bool = True) -> str:
    """
    Analyze multiple stocks and generate report.
    
    Args:
        stock_codes: List of stock codes
        use_llm: Whether to use LLM for analysis (uses OpenClaw's built-in LLM)
        
    Returns:
        Formatted analysis report
    """
    analyzer = StockAnalyzer()
    
    # Get real-time quotes
    quotes = analyzer.get_realtime_quotes(stock_codes)
    
    # Generate analysis for each stock
    results = []
    for code in stock_codes:
        if code not in quotes or 'error' in quotes[code]:
            continue
        
        technical = analyzer.get_technical_analysis(code)
        news = analyzer.get_news_sentiment(code)
        dashboard = analyzer.generate_decision_dashboard(code, quotes[code], technical, news)
        
        results.append({
            'code': code,
            'quote': quotes[code],
            'technical': technical,
            'news': news,
            'dashboard': dashboard,
        })
    
    # Format report
    report = []
    report.append(f"📊 股票智能分析报告\n")
    report.append(f"分析时间：{datetime.now().strftime('%Y-%m-%d %H:%M')}\n")
    report.append(f"分析股票数：{len(results)}\n")
    report.append("=" * 50 + "\n\n")
    
    for result in results:
        dashboard = result['dashboard']
        quote = result['quote']
        
        report.append(f"{dashboard['action']} {result['code']}")
        report.append(f"当前价格：{quote.get('price', 'N/A')}")
        report.append(f"涨跌幅：{quote.get('change_percent', 0):.2f}%")
        report.append(f"建议：{dashboard['recommendation']}")
        report.append(f"目标价：{dashboard['target_price']}")
        report.append(f"止损价：{dashboard['stop_loss']}")
        report.append(f"置信度：{dashboard['confidence']}")
        report.append(f"理由：{dashboard['reasoning']}")
        report.append("-" * 50 + "\n")
    
    report.append("\n⚠️ 免责声明：本报告仅供参考，不构成投资建议。股市有风险，投资需谨慎。")
    
    return '\n'.join(report)


if __name__ == '__main__':
    import sys
    
    if len(sys.argv) < 2:
        print("Usage: python analyze.py <stock_codes>")
        print("  stock_codes: Comma-separated stock codes (e.g., 600519,hk00700,AAPL)")
        sys.exit(1)
    
    stock_codes = [code.strip() for code in sys.argv[1].split(',')]
    report = analyze_stocks(stock_codes)
    print(report)
