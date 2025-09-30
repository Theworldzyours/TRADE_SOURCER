"""
Technical indicators calculator
"""
import pandas as pd
import numpy as np
from typing import Dict, Optional
from ..utils.logger import get_logger

logger = get_logger()


class TechnicalIndicators:
    """Calculate technical indicators for stock data"""
    
    def __init__(self, config: Dict = None):
        """
        Initialize technical indicators calculator
        
        Args:
            config: Configuration dictionary with indicator parameters
        """
        self.config = config or {}
    
    def calculate_rsi(self, df: pd.DataFrame, period: int = 14) -> pd.Series:
        """
        Calculate Relative Strength Index (RSI)
        
        Args:
            df: DataFrame with 'Close' column
            period: RSI period
        
        Returns:
            Series with RSI values
        """
        delta = df['Close'].diff()
        gain = (delta.where(delta > 0, 0)).rolling(window=period).mean()
        loss = (-delta.where(delta < 0, 0)).rolling(window=period).mean()
        
        rs = gain / loss
        rsi = 100 - (100 / (1 + rs))
        return rsi
    
    def calculate_macd(
        self,
        df: pd.DataFrame,
        fast: int = 12,
        slow: int = 26,
        signal: int = 9
    ) -> Dict[str, pd.Series]:
        """
        Calculate MACD (Moving Average Convergence Divergence)
        
        Args:
            df: DataFrame with 'Close' column
            fast: Fast EMA period
            slow: Slow EMA period
            signal: Signal line period
        
        Returns:
            Dictionary with 'macd', 'signal', 'histogram'
        """
        exp1 = df['Close'].ewm(span=fast, adjust=False).mean()
        exp2 = df['Close'].ewm(span=slow, adjust=False).mean()
        
        macd = exp1 - exp2
        signal_line = macd.ewm(span=signal, adjust=False).mean()
        histogram = macd - signal_line
        
        return {
            'macd': macd,
            'signal': signal_line,
            'histogram': histogram
        }
    
    def calculate_bollinger_bands(
        self,
        df: pd.DataFrame,
        period: int = 20,
        std: int = 2
    ) -> Dict[str, pd.Series]:
        """
        Calculate Bollinger Bands
        
        Args:
            df: DataFrame with 'Close' column
            period: Moving average period
            std: Number of standard deviations
        
        Returns:
            Dictionary with 'upper', 'middle', 'lower'
        """
        sma = df['Close'].rolling(window=period).mean()
        rolling_std = df['Close'].rolling(window=period).std()
        
        upper = sma + (rolling_std * std)
        lower = sma - (rolling_std * std)
        
        return {
            'upper': upper,
            'middle': sma,
            'lower': lower
        }
    
    def calculate_sma(self, df: pd.DataFrame, period: int) -> pd.Series:
        """
        Calculate Simple Moving Average
        
        Args:
            df: DataFrame with 'Close' column
            period: Moving average period
        
        Returns:
            Series with SMA values
        """
        return df['Close'].rolling(window=period).mean()
    
    def calculate_ema(self, df: pd.DataFrame, period: int) -> pd.Series:
        """
        Calculate Exponential Moving Average
        
        Args:
            df: DataFrame with 'Close' column
            period: Moving average period
        
        Returns:
            Series with EMA values
        """
        return df['Close'].ewm(span=period, adjust=False).mean()
    
    def calculate_volume_indicators(self, df: pd.DataFrame) -> Dict[str, pd.Series]:
        """
        Calculate volume-based indicators
        
        Args:
            df: DataFrame with 'Close' and 'Volume' columns
        
        Returns:
            Dictionary with volume indicators
        """
        # On-Balance Volume (OBV)
        obv = (np.sign(df['Close'].diff()) * df['Volume']).fillna(0).cumsum()
        
        # Volume Moving Average
        volume_ma = df['Volume'].rolling(window=20).mean()
        
        # Volume Ratio (current vs average)
        volume_ratio = df['Volume'] / volume_ma
        
        return {
            'obv': obv,
            'volume_ma': volume_ma,
            'volume_ratio': volume_ratio
        }
    
    def calculate_atr(self, df: pd.DataFrame, period: int = 14) -> pd.Series:
        """
        Calculate Average True Range (ATR)
        
        Args:
            df: DataFrame with 'High', 'Low', 'Close' columns
            period: ATR period
        
        Returns:
            Series with ATR values
        """
        high_low = df['High'] - df['Low']
        high_close = np.abs(df['High'] - df['Close'].shift())
        low_close = np.abs(df['Low'] - df['Close'].shift())
        
        ranges = pd.concat([high_low, high_close, low_close], axis=1)
        true_range = np.max(ranges, axis=1)
        
        atr = true_range.rolling(window=period).mean()
        return atr
    
    def calculate_stochastic(
        self,
        df: pd.DataFrame,
        k_period: int = 14,
        d_period: int = 3
    ) -> Dict[str, pd.Series]:
        """
        Calculate Stochastic Oscillator
        
        Args:
            df: DataFrame with 'High', 'Low', 'Close' columns
            k_period: %K period
            d_period: %D period
        
        Returns:
            Dictionary with 'k' and 'd' values
        """
        low_min = df['Low'].rolling(window=k_period).min()
        high_max = df['High'].rolling(window=k_period).max()
        
        k = 100 * ((df['Close'] - low_min) / (high_max - low_min))
        d = k.rolling(window=d_period).mean()
        
        return {
            'k': k,
            'd': d
        }
    
    def analyze_all(self, df: pd.DataFrame, ticker: str) -> Dict:
        """
        Calculate all technical indicators for a stock
        
        Args:
            df: DataFrame with OHLCV data
            ticker: Stock ticker symbol
        
        Returns:
            Dictionary with all indicators and signals
        """
        try:
            # Get configuration
            rsi_period = self.config.get('rsi_period', 14)
            macd_fast = self.config.get('macd_fast', 12)
            macd_slow = self.config.get('macd_slow', 26)
            macd_signal = self.config.get('macd_signal', 9)
            
            # Calculate indicators
            rsi = self.calculate_rsi(df, rsi_period)
            macd_data = self.calculate_macd(df, macd_fast, macd_slow, macd_signal)
            bb = self.calculate_bollinger_bands(df)
            volume_indicators = self.calculate_volume_indicators(df)
            
            # SMAs
            sma_20 = self.calculate_sma(df, 20)
            sma_50 = self.calculate_sma(df, 50)
            sma_200 = self.calculate_sma(df, 200)
            
            # Get latest values
            latest = {
                'ticker': ticker,
                'current_price': df['Close'].iloc[-1],
                'rsi': rsi.iloc[-1],
                'macd': macd_data['macd'].iloc[-1],
                'macd_signal': macd_data['signal'].iloc[-1],
                'macd_histogram': macd_data['histogram'].iloc[-1],
                'bb_upper': bb['upper'].iloc[-1],
                'bb_middle': bb['middle'].iloc[-1],
                'bb_lower': bb['lower'].iloc[-1],
                'sma_20': sma_20.iloc[-1],
                'sma_50': sma_50.iloc[-1],
                'sma_200': sma_200.iloc[-1],
                'volume': df['Volume'].iloc[-1],
                'volume_ratio': volume_indicators['volume_ratio'].iloc[-1],
            }
            
            # Generate signals
            signals = self._generate_signals(latest, df)
            latest['signals'] = signals
            latest['technical_score'] = self._calculate_technical_score(latest, signals)
            
            return latest
        
        except Exception as e:
            logger.error(f"Error analyzing {ticker}: {e}")
            return {'ticker': ticker, 'error': str(e)}
    
    def _generate_signals(self, latest: Dict, df: pd.DataFrame) -> Dict:
        """
        Generate trading signals based on indicators
        
        Args:
            latest: Dictionary with latest indicator values
            df: Full DataFrame for trend analysis
        
        Returns:
            Dictionary with signals
        """
        signals = {}
        
        # RSI signals
        if latest['rsi'] < 30:
            signals['rsi'] = 'oversold'
        elif latest['rsi'] > 70:
            signals['rsi'] = 'overbought'
        else:
            signals['rsi'] = 'neutral'
        
        # MACD signal
        if latest['macd'] > latest['macd_signal']:
            signals['macd'] = 'bullish'
        else:
            signals['macd'] = 'bearish'
        
        # Trend signal
        price = latest['current_price']
        if price > latest['sma_20'] > latest['sma_50'] > latest['sma_200']:
            signals['trend'] = 'strong_uptrend'
        elif price > latest['sma_50']:
            signals['trend'] = 'uptrend'
        elif price < latest['sma_50']:
            signals['trend'] = 'downtrend'
        else:
            signals['trend'] = 'neutral'
        
        # Volume signal
        if latest['volume_ratio'] > 1.5:
            signals['volume'] = 'high'
        elif latest['volume_ratio'] < 0.5:
            signals['volume'] = 'low'
        else:
            signals['volume'] = 'normal'
        
        # Bollinger Bands signal
        if price < latest['bb_lower']:
            signals['bb'] = 'oversold'
        elif price > latest['bb_upper']:
            signals['bb'] = 'overbought'
        else:
            signals['bb'] = 'neutral'
        
        return signals
    
    def _calculate_technical_score(self, latest: Dict, signals: Dict) -> float:
        """
        Calculate overall technical score (0-100)
        
        Args:
            latest: Latest indicator values
            signals: Trading signals
        
        Returns:
            Technical score
        """
        score = 50.0  # Start neutral
        
        # RSI contribution
        if signals['rsi'] == 'oversold':
            score += 10
        elif signals['rsi'] == 'overbought':
            score -= 10
        
        # MACD contribution
        if signals['macd'] == 'bullish':
            score += 15
        else:
            score -= 15
        
        # Trend contribution
        if signals['trend'] == 'strong_uptrend':
            score += 20
        elif signals['trend'] == 'uptrend':
            score += 10
        elif signals['trend'] == 'downtrend':
            score -= 15
        
        # Volume contribution
        if signals['volume'] == 'high' and signals['trend'] in ['uptrend', 'strong_uptrend']:
            score += 10
        
        # Normalize to 0-100
        score = max(0, min(100, score))
        
        return round(score, 2)
