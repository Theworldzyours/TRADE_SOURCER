"""
Market data fetcher using yfinance as primary source
"""
import yfinance as yf
import pandas as pd
from typing import List, Dict, Optional
from datetime import datetime, timedelta
import time
from ..utils.logger import get_logger

logger = get_logger()


class MarketDataFetcher:
    """Fetch market data for stocks"""
    
    def __init__(self, cache_enabled: bool = True):
        """
        Initialize market data fetcher
        
        Args:
            cache_enabled: Enable caching of data
        """
        self.cache_enabled = cache_enabled
        self.cache = {}
    
    def get_stock_data(
        self,
        ticker: str,
        period: str = "1y",
        interval: str = "1d"
    ) -> Optional[pd.DataFrame]:
        """
        Get historical stock data
        
        Args:
            ticker: Stock ticker symbol
            period: Data period (1d, 5d, 1mo, 3mo, 6mo, 1y, 2y, 5y, 10y, ytd, max)
            interval: Data interval (1m, 2m, 5m, 15m, 30m, 60m, 90m, 1h, 1d, 5d, 1wk, 1mo, 3mo)
        
        Returns:
            DataFrame with OHLCV data or None if error
        """
        cache_key = f"{ticker}_{period}_{interval}"
        
        # Check cache
        if self.cache_enabled and cache_key in self.cache:
            logger.debug(f"Using cached data for {ticker}")
            return self.cache[cache_key]
        
        try:
            logger.info(f"Fetching data for {ticker}")
            stock = yf.Ticker(ticker)
            df = stock.history(period=period, interval=interval)
            
            if df.empty:
                logger.warning(f"No data found for {ticker}")
                return None
            
            # Cache the data
            if self.cache_enabled:
                self.cache[cache_key] = df
            
            return df
        
        except Exception as e:
            logger.error(f"Error fetching data for {ticker}: {e}")
            return None
    
    def get_multiple_stocks(
        self,
        tickers: List[str],
        period: str = "1y",
        interval: str = "1d",
        delay: float = 0.5
    ) -> Dict[str, pd.DataFrame]:
        """
        Get historical data for multiple stocks
        
        Args:
            tickers: List of ticker symbols
            period: Data period
            interval: Data interval
            delay: Delay between requests in seconds
        
        Returns:
            Dictionary mapping ticker to DataFrame
        """
        results = {}
        
        for i, ticker in enumerate(tickers):
            df = self.get_stock_data(ticker, period, interval)
            if df is not None:
                results[ticker] = df
            
            # Rate limiting
            if i < len(tickers) - 1:
                time.sleep(delay)
        
        logger.info(f"Fetched data for {len(results)}/{len(tickers)} stocks")
        return results
    
    def get_stock_info(self, ticker: str) -> Optional[Dict]:
        """
        Get stock information (company info, financials, etc.)
        
        Args:
            ticker: Stock ticker symbol
        
        Returns:
            Dictionary with stock information or None
        """
        try:
            stock = yf.Ticker(ticker)
            info = stock.info
            return info
        except Exception as e:
            logger.error(f"Error fetching info for {ticker}: {e}")
            return None
    
    def get_current_price(self, ticker: str) -> Optional[float]:
        """
        Get current stock price
        
        Args:
            ticker: Stock ticker symbol
        
        Returns:
            Current price or None
        """
        try:
            stock = yf.Ticker(ticker)
            data = stock.history(period="1d", interval="1m")
            if not data.empty:
                return data['Close'].iloc[-1]
            return None
        except Exception as e:
            logger.error(f"Error fetching current price for {ticker}: {e}")
            return None
    
    def get_financials(self, ticker: str) -> Dict[str, pd.DataFrame]:
        """
        Get financial statements
        
        Args:
            ticker: Stock ticker symbol
        
        Returns:
            Dictionary with income_statement, balance_sheet, cash_flow
        """
        try:
            stock = yf.Ticker(ticker)
            return {
                'income_statement': stock.financials,
                'balance_sheet': stock.balance_sheet,
                'cash_flow': stock.cashflow,
                'quarterly_financials': stock.quarterly_financials,
            }
        except Exception as e:
            logger.error(f"Error fetching financials for {ticker}: {e}")
            return {}
    
    def clear_cache(self):
        """Clear cached data"""
        self.cache = {}
        logger.info("Cache cleared")
