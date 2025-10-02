"""
Demo script with sample data (no network required)
Demonstrates the enhanced volatility analysis and next week predictions
"""
import sys
import pandas as pd
import numpy as np
from pathlib import Path
from datetime import datetime, timedelta

# Add src to path
sys.path.insert(0, str(Path(__file__).parent))

from src.indicators.volatility import VolatilityAnalyzer
from src.indicators.technical import TechnicalIndicators
from src.utils.logger import setup_logger

# Setup logging
logger = setup_logger(log_to_console=True, level='INFO')

def create_sample_stock_data(ticker: str, base_price: float = 100, volatility: float = 0.02):
    """
    Create realistic sample stock data
    
    Args:
        ticker: Stock ticker
        base_price: Starting price
        volatility: Daily volatility (0.02 = 2%)
    
    Returns:
        DataFrame with OHLCV data
    """
    dates = pd.date_range(end=datetime.now(), periods=252, freq='D')  # 1 year
    np.random.seed(hash(ticker) % 2**32)
    
    # Generate price series with realistic characteristics
    returns = np.random.normal(0.0005, volatility, len(dates))  # Slight upward drift
    prices = [base_price]
    
    for r in returns[1:]:
        new_price = prices[-1] * (1 + r)
        prices.append(new_price)
    
    # Add some trending behavior
    trend = np.linspace(0, 0.2, len(dates))
    prices = [p * (1 + t) for p, t in zip(prices, trend)]
    
    df = pd.DataFrame({
        'Open': [p * 0.995 for p in prices],
        'High': [p * 1.01 for p in prices],
        'Low': [p * 0.99 for p in prices],
        'Close': prices,
        'Volume': np.random.randint(1000000, 10000000, len(dates))
    }, index=dates)
    
    return df


def demo_volatility_analysis():
    """Demonstrate volatility analysis and next week predictions"""
    
    print("\n" + "=" * 80)
    print("TRADE SOURCER - VOLATILITY & NEXT WEEK PREDICTION DEMO")
    print("=" * 80)
    print("\nThis demo showcases the new volatility analysis features")
    print("using sample data (no network connection required)\n")
    
    # Create sample stocks with different characteristics
    stocks = {
        'AAPL': {'base_price': 175, 'volatility': 0.015, 'name': 'Apple Inc.'},
        'TSLA': {'base_price': 240, 'volatility': 0.035, 'name': 'Tesla Inc.'},
        'MSFT': {'base_price': 380, 'volatility': 0.018, 'name': 'Microsoft Corp.'},
    }
    
    # Initialize analyzers
    vol_analyzer = VolatilityAnalyzer()
    tech_analyzer = TechnicalIndicators()
    
    for ticker, params in stocks.items():
        print("-" * 80)
        print(f"\n📊 {ticker} - {params['name']}")
        print("-" * 80)
        
        # Generate sample data
        df = create_sample_stock_data(ticker, params['base_price'], params['volatility'])
        
        # Run volatility analysis
        vol_result = vol_analyzer.analyze_all(df, ticker)
        
        # Display current price
        current_price = vol_result['current_price']
        print(f"\n💰 Current Price: ${current_price:.2f}")
        
        # Display volatility metrics
        print(f"\n📈 Volatility Metrics:")
        print(f"   Historical Volatility (20d): {vol_result['historical_volatility_20d']:.1f}%")
        print(f"   Parkinson Volatility:        {vol_result['parkinson_volatility']:.1f}%")
        print(f"   ATR Percentage:              {vol_result['atr_percentage']:.1f}%")
        print(f"   Bollinger Width:             {vol_result['bollinger_width']:.1f}%")
        
        # Display volatility regime
        print(f"\n🎯 Volatility Regime: {vol_result['volatility_regime'].replace('_', ' ').title()}")
        print(f"   {vol_result['volatility_description']}")
        print(f"   Volatility Score: {vol_result['volatility_score']:.1f}/100")
        
        # Display next week prediction
        print(f"\n📅 Next Week Prediction:")
        print(f"   Expected Range: ${vol_result['next_week_lower']:.2f} - ${vol_result['next_week_upper']:.2f}")
        print(f"   Change Range:   {vol_result['next_week_lower_pct']:.1f}% to {vol_result['next_week_upper_pct']:.1f}%")
        print(f"   Weekly Volatility: {vol_result['weekly_volatility']:.1f}%")
        
        # Display scenarios
        scenarios = vol_result['scenarios']
        print(f"\n🎲 Next Week Scenarios:")
        print(f"   🐻 Bear Case:  ${scenarios['bear_case']['target_price']:.2f}")
        print(f"      ({scenarios['bear_case']['pct_change']:.1f}%) - Probability: {scenarios['bear_case']['probability']*100:.0f}%")
        
        print(f"   📊 Base Case:  ${scenarios['base_case']['target_price']:.2f}")
        print(f"      ({scenarios['base_case']['pct_change']:.1f}%) - Probability: {scenarios['base_case']['probability']*100:.0f}%")
        
        print(f"   🚀 Bull Case:  ${scenarios['bull_case']['target_price']:.2f}")
        print(f"      ({scenarios['bull_case']['pct_change']:.1f}%) - Probability: {scenarios['bull_case']['probability']*100:.0f}%")
        
        # Extreme range
        extreme = scenarios['extreme_range']
        print(f"\n   ⚠️  Extreme Range (95%): ${extreme['lower']:.2f} - ${extreme['upper']:.2f}")
        
        # Run technical analysis
        tech_result = tech_analyzer.analyze_all(df, ticker)
        print(f"\n📊 Technical Indicators:")
        print(f"   RSI: {tech_result['rsi']:.1f}")
        print(f"   MACD Signal: {tech_result['signals']['macd']}")
        print(f"   Trend: {tech_result['signals']['trend'].replace('_', ' ').title()}")
        print(f"   Technical Score: {tech_result['technical_score']:.1f}/100")
        
        print()
    
    print("=" * 80)
    print("\n✅ Demo Complete!")
    print("\nKey Features Demonstrated:")
    print("  ✓ Historical volatility calculations")
    print("  ✓ Next week price range predictions")
    print("  ✓ Bear/Base/Bull scenario generation")
    print("  ✓ Volatility regime analysis")
    print("  ✓ Integration with technical indicators")
    print("\nThese features are now integrated into the main application!")
    print("Run 'python main.py' to analyze real stocks (requires internet connection)")
    print("=" * 80 + "\n")


if __name__ == "__main__":
    demo_volatility_analysis()
