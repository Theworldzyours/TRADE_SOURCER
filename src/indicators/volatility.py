"""
Volatility and forward-looking analysis module
Provides next week price predictions and volatility metrics
"""
import pandas as pd
import numpy as np
from typing import Dict, Tuple
from ..utils.logger import get_logger

logger = get_logger()


class VolatilityAnalyzer:
    """Analyze volatility and predict next week price ranges"""
    
    def __init__(self, config: Dict = None):
        """
        Initialize volatility analyzer
        
        Args:
            config: Configuration dictionary
        """
        self.config = config or {}
    
    def calculate_historical_volatility(
        self,
        df: pd.DataFrame,
        period: int = 20
    ) -> float:
        """
        Calculate historical volatility (annualized)
        
        Args:
            df: DataFrame with 'Close' column
            period: Number of periods for calculation
        
        Returns:
            Annualized historical volatility (%)
        """
        # Calculate daily returns
        returns = df['Close'].pct_change().dropna()
        
        # Calculate standard deviation of returns
        std_dev = returns.tail(period).std()
        
        # Annualize (assuming 252 trading days per year)
        annualized_vol = std_dev * np.sqrt(252) * 100
        
        return annualized_vol
    
    def calculate_parkinson_volatility(self, df: pd.DataFrame, period: int = 20) -> float:
        """
        Calculate Parkinson's volatility (uses high/low prices)
        More accurate than close-to-close volatility
        
        Args:
            df: DataFrame with 'High' and 'Low' columns
            period: Number of periods for calculation
        
        Returns:
            Annualized Parkinson volatility (%)
        """
        # Parkinson volatility formula
        hl_ratio = np.log(df['High'] / df['Low'])
        parkinson = np.sqrt((1 / (4 * np.log(2))) * (hl_ratio ** 2).tail(period).mean())
        
        # Annualize
        annualized_vol = parkinson * np.sqrt(252) * 100
        
        return annualized_vol
    
    def calculate_atr_percentage(self, df: pd.DataFrame, period: int = 14) -> float:
        """
        Calculate ATR as percentage of price
        
        Args:
            df: DataFrame with OHLC data
            period: ATR period
        
        Returns:
            ATR as percentage of current price
        """
        high_low = df['High'] - df['Low']
        high_close = np.abs(df['High'] - df['Close'].shift())
        low_close = np.abs(df['Low'] - df['Close'].shift())
        
        ranges = pd.concat([high_low, high_close, low_close], axis=1)
        true_range = ranges.max(axis=1)
        
        atr = true_range.rolling(window=period).mean().iloc[-1]
        current_price = df['Close'].iloc[-1]
        
        atr_percentage = (atr / current_price) * 100
        
        return atr_percentage
    
    def predict_next_week_range(
        self,
        df: pd.DataFrame,
        confidence_level: float = 0.68
    ) -> Dict[str, float]:
        """
        Predict next week's price range based on volatility
        
        Args:
            df: DataFrame with 'Close' column
            confidence_level: Confidence level (0.68 = 1 std dev, 0.95 = 2 std dev)
        
        Returns:
            Dictionary with predicted range and probabilities
        """
        current_price = df['Close'].iloc[-1]
        
        # Calculate daily volatility
        returns = df['Close'].pct_change().dropna()
        daily_vol = returns.std()
        
        # Weekly volatility (5 trading days)
        weekly_vol = daily_vol * np.sqrt(5)
        
        # Determine z-score based on confidence level
        if confidence_level >= 0.95:
            z_score = 1.96  # 95% confidence
        elif confidence_level >= 0.90:
            z_score = 1.645  # 90% confidence
        else:
            z_score = 1.0  # 68% confidence (1 std dev)
        
        # Calculate range
        expected_move = current_price * weekly_vol * z_score
        
        lower_bound = current_price - expected_move
        upper_bound = current_price + expected_move
        
        # Calculate expected price change percentages
        lower_pct = ((lower_bound - current_price) / current_price) * 100
        upper_pct = ((upper_bound - current_price) / current_price) * 100
        
        return {
            'current_price': current_price,
            'lower_bound': lower_bound,
            'upper_bound': upper_bound,
            'expected_range': expected_move,
            'lower_pct_change': lower_pct,
            'upper_pct_change': upper_pct,
            'weekly_volatility': weekly_vol * 100,
            'confidence_level': confidence_level * 100
        }
    
    def calculate_bollinger_width(self, df: pd.DataFrame, period: int = 20) -> float:
        """
        Calculate Bollinger Band width as volatility indicator
        
        Args:
            df: DataFrame with 'Close' column
            period: Bollinger Band period
        
        Returns:
            Bollinger Band width percentage
        """
        sma = df['Close'].rolling(window=period).mean()
        std = df['Close'].rolling(window=period).std()
        
        upper = sma + (2 * std)
        lower = sma - (2 * std)
        
        # Width as percentage of middle band
        width = ((upper - lower) / sma * 100).iloc[-1]
        
        return width
    
    def analyze_volatility_regime(self, df: pd.DataFrame) -> Dict[str, any]:
        """
        Determine current volatility regime
        
        Args:
            df: DataFrame with OHLC data
        
        Returns:
            Dictionary with volatility regime analysis
        """
        # Calculate short-term (20 days) and long-term (60 days) volatility
        short_term_vol = self.calculate_historical_volatility(df, period=20)
        long_term_vol = self.calculate_historical_volatility(df, period=60)
        
        # Determine regime
        vol_ratio = short_term_vol / long_term_vol if long_term_vol > 0 else 1.0
        
        if vol_ratio > 1.5:
            regime = "high_volatility"
            description = "Volatility is elevated - expect larger price swings"
        elif vol_ratio < 0.7:
            regime = "low_volatility"
            description = "Volatility is compressed - potential breakout ahead"
        else:
            regime = "normal_volatility"
            description = "Volatility is at normal levels"
        
        return {
            'regime': regime,
            'description': description,
            'short_term_vol': short_term_vol,
            'long_term_vol': long_term_vol,
            'vol_ratio': vol_ratio
        }
    
    def generate_next_week_scenarios(
        self,
        df: pd.DataFrame
    ) -> Dict[str, Dict]:
        """
        Generate multiple scenarios for next week
        
        Args:
            df: DataFrame with OHLC data
        
        Returns:
            Dictionary with bear, base, and bull scenarios
        """
        current_price = df['Close'].iloc[-1]
        
        # Get trend (simple: 20-day SMA slope)
        sma_20 = df['Close'].rolling(window=20).mean()
        trend_slope = (sma_20.iloc[-1] - sma_20.iloc[-5]) / sma_20.iloc[-5]
        
        # Get volatility-based ranges
        range_68 = self.predict_next_week_range(df, confidence_level=0.68)
        range_95 = self.predict_next_week_range(df, confidence_level=0.95)
        
        # Bear scenario (downside)
        bear_target = range_68['lower_bound']
        bear_pct = range_68['lower_pct_change']
        
        # Base scenario (trend continuation)
        base_target = current_price * (1 + trend_slope)
        base_pct = ((base_target - current_price) / current_price) * 100
        
        # Bull scenario (upside)
        bull_target = range_68['upper_bound']
        bull_pct = range_68['upper_pct_change']
        
        return {
            'bear_case': {
                'target_price': bear_target,
                'pct_change': bear_pct,
                'probability': 0.16,  # Lower tail of normal distribution
                'description': f"Downside scenario: ${bear_target:.2f} ({bear_pct:.1f}%)"
            },
            'base_case': {
                'target_price': base_target,
                'pct_change': base_pct,
                'probability': 0.68,  # Within 1 std dev
                'description': f"Expected scenario: ${base_target:.2f} ({base_pct:.1f}%)"
            },
            'bull_case': {
                'target_price': bull_target,
                'pct_change': bull_pct,
                'probability': 0.16,  # Upper tail of normal distribution
                'description': f"Upside scenario: ${bull_target:.2f} ({bull_pct:.1f}%)"
            },
            'extreme_range': {
                'lower': range_95['lower_bound'],
                'upper': range_95['upper_bound'],
                'description': f"95% confidence range: ${range_95['lower_bound']:.2f} - ${range_95['upper_bound']:.2f}"
            }
        }
    
    def analyze_all(self, df: pd.DataFrame, ticker: str) -> Dict:
        """
        Complete volatility analysis for a stock
        
        Args:
            df: DataFrame with OHLC data
            ticker: Stock ticker symbol
        
        Returns:
            Dictionary with all volatility metrics
        """
        try:
            # Calculate various volatility metrics
            hist_vol = self.calculate_historical_volatility(df, period=20)
            park_vol = self.calculate_parkinson_volatility(df, period=20)
            atr_pct = self.calculate_atr_percentage(df, period=14)
            bb_width = self.calculate_bollinger_width(df, period=20)
            
            # Analyze volatility regime
            regime = self.analyze_volatility_regime(df)
            
            # Predict next week range
            next_week_range = self.predict_next_week_range(df, confidence_level=0.68)
            
            # Generate scenarios
            scenarios = self.generate_next_week_scenarios(df)
            
            return {
                'ticker': ticker,
                'current_price': df['Close'].iloc[-1],
                'historical_volatility_20d': hist_vol,
                'parkinson_volatility': park_vol,
                'atr_percentage': atr_pct,
                'bollinger_width': bb_width,
                'volatility_regime': regime['regime'],
                'volatility_description': regime['description'],
                'vol_ratio': regime['vol_ratio'],
                'next_week_lower': next_week_range['lower_bound'],
                'next_week_upper': next_week_range['upper_bound'],
                'next_week_lower_pct': next_week_range['lower_pct_change'],
                'next_week_upper_pct': next_week_range['upper_pct_change'],
                'weekly_volatility': next_week_range['weekly_volatility'],
                'scenarios': scenarios,
                'volatility_score': self._calculate_volatility_score(hist_vol, regime['vol_ratio'])
            }
        
        except Exception as e:
            logger.error(f"Error analyzing volatility for {ticker}: {e}")
            return {'ticker': ticker, 'error': str(e)}
    
    def _calculate_volatility_score(self, volatility: float, vol_ratio: float) -> float:
        """
        Calculate a volatility score for trading opportunities
        Moderate volatility is preferred (not too high, not too low)
        
        Args:
            volatility: Historical volatility percentage
            vol_ratio: Short-term to long-term volatility ratio
        
        Returns:
            Volatility score (0-100)
        """
        score = 50.0
        
        # Optimal volatility range: 20-40% annualized
        if 20 <= volatility <= 40:
            score += 20
        elif 15 <= volatility < 20 or 40 < volatility <= 50:
            score += 10
        elif volatility > 60:
            score -= 10  # Too volatile
        
        # Vol ratio - prefer normal or slightly elevated
        if 0.8 <= vol_ratio <= 1.2:
            score += 10
        elif 1.2 < vol_ratio <= 1.5:
            score += 5  # Slight elevation okay
        elif vol_ratio > 2.0:
            score -= 15  # Too unstable
        
        return min(100, max(0, score))
