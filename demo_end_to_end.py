"""
End-to-end working example with sample data
Demonstrates the complete Trade Sourcer workflow
"""
import sys
import pandas as pd
import numpy as np
from pathlib import Path
from datetime import datetime, timedelta

# Add src to path
sys.path.insert(0, str(Path(__file__).parent))

from src.utils.config_loader import get_config
from src.utils.logger import setup_logger
from src.indicators.technical import TechnicalIndicators
from src.indicators.fundamental import FundamentalIndicators
from src.indicators.volatility import VolatilityAnalyzer
from src.scoring.vc_scorer import VCScorer
from src.ranking.ranker import StockRanker
from src.reports.report_generator import ReportGenerator


def create_sample_stock_data(ticker: str, base_price: float, volatility: float, trend: float):
    """Create realistic sample stock data"""
    dates = pd.date_range(end=datetime.now(), periods=252, freq='D')
    np.random.seed(hash(ticker) % 2**32)
    
    # Generate price series
    returns = np.random.normal(trend/252, volatility, len(dates))
    prices = [base_price]
    
    for r in returns[1:]:
        new_price = prices[-1] * (1 + r)
        prices.append(max(new_price, base_price * 0.5))  # Floor at 50% of base
    
    df = pd.DataFrame({
        'Open': [p * 0.995 for p in prices],
        'High': [p * 1.015 for p in prices],
        'Low': [p * 0.985 for p in prices],
        'Close': prices,
        'Volume': np.random.randint(1000000, 10000000, len(dates))
    }, index=dates)
    
    return df


def create_sample_stock_info(ticker: str, profile: dict):
    """Create sample stock info data"""
    return {
        'longName': profile['name'],
        'sector': profile['sector'],
        'industry': profile.get('industry', 'Technology'),
        'marketCap': profile['market_cap'],
        'revenueGrowth': profile.get('revenue_growth', 0.20),
        'earningsGrowth': profile.get('earnings_growth', 0.25),
        'grossMargins': profile.get('gross_margin', 0.60),
        'operatingMargins': profile.get('operating_margin', 0.25),
        'profitMargins': profile.get('profit_margin', 0.15),
        'returnOnEquity': profile.get('roe', 0.20),
        'returnOnAssets': profile.get('roa', 0.10),
        'debtToEquity': profile.get('debt_to_equity', 30),
        'currentRatio': profile.get('current_ratio', 2.0),
        'freeCashflow': profile.get('fcf', 1_000_000_000),
        'trailingPE': profile.get('pe', 25),
        'forwardPE': profile.get('forward_pe', 22),
        'pegRatio': profile.get('peg', 1.2),
        'priceToBook': profile.get('pb', 5),
        'priceToSalesTrailing12Months': profile.get('ps', 8),
        'enterpriseToRevenue': profile.get('ev_revenue', 10),
        'enterpriseValue': profile['market_cap'] * 1.1,
        'sharesOutstanding': profile['market_cap'] / profile['base_price'],
        'averageVolume': 5_000_000,
    }


def run_end_to_end_demo():
    """Run complete end-to-end workflow with sample data"""
    
    print("\n" + "=" * 80)
    print("TRADE SOURCER - END-TO-END WORKING DEMO")
    print("=" * 80)
    print("\nThis demonstrates the complete workflow with sample data")
    print("(In production, this will fetch real data from market APIs)\n")
    
    # Sample stock profiles
    stock_profiles = {
        'AAPL': {
            'name': 'Apple Inc.',
            'sector': 'Technology',
            'base_price': 175,
            'volatility': 0.015,
            'trend': 0.15,
            'market_cap': 2_800_000_000_000,
            'revenue_growth': 0.08,
            'earnings_growth': 0.11,
            'gross_margin': 0.43,
            'operating_margin': 0.30,
            'profit_margin': 0.25,
            'roe': 0.47,
            'debt_to_equity': 20,
            'pe': 28,
            'peg': 2.5,
        },
        'MSFT': {
            'name': 'Microsoft Corporation',
            'sector': 'Technology',
            'base_price': 380,
            'volatility': 0.018,
            'trend': 0.18,
            'market_cap': 2_900_000_000_000,
            'revenue_growth': 0.12,
            'earnings_growth': 0.18,
            'gross_margin': 0.69,
            'operating_margin': 0.42,
            'profit_margin': 0.36,
            'roe': 0.38,
            'debt_to_equity': 25,
            'pe': 32,
            'peg': 1.8,
        },
        'GOOGL': {
            'name': 'Alphabet Inc.',
            'sector': 'Technology',
            'base_price': 140,
            'volatility': 0.020,
            'trend': 0.12,
            'market_cap': 1_800_000_000_000,
            'revenue_growth': 0.09,
            'earnings_growth': 0.15,
            'gross_margin': 0.57,
            'operating_margin': 0.28,
            'profit_margin': 0.21,
            'roe': 0.26,
            'debt_to_equity': 10,
            'pe': 24,
            'peg': 1.6,
        },
        'TSLA': {
            'name': 'Tesla Inc.',
            'sector': 'Consumer Cyclical',
            'base_price': 240,
            'volatility': 0.035,
            'trend': 0.05,
            'market_cap': 760_000_000_000,
            'revenue_growth': 0.37,
            'earnings_growth': 0.45,
            'gross_margin': 0.25,
            'operating_margin': 0.12,
            'profit_margin': 0.10,
            'roe': 0.22,
            'debt_to_equity': 15,
            'pe': 65,
            'peg': 1.4,
        },
        'NVDA': {
            'name': 'NVIDIA Corporation',
            'sector': 'Technology',
            'base_price': 480,
            'volatility': 0.028,
            'trend': 0.45,
            'market_cap': 1_200_000_000_000,
            'revenue_growth': 0.61,
            'earnings_growth': 0.88,
            'gross_margin': 0.72,
            'operating_margin': 0.32,
            'profit_margin': 0.29,
            'roe': 0.48,
            'debt_to_equity': 18,
            'pe': 55,
            'peg': 0.9,
        },
    }
    
    # Initialize analyzers
    tech_analyzer = TechnicalIndicators()
    fund_analyzer = FundamentalIndicators()
    vol_analyzer = VolatilityAnalyzer()
    scorer = VCScorer()
    ranker = StockRanker({'filters': {
        'min_market_cap': 100_000_000,
        'min_avg_volume': 100_000,
        'min_revenue_growth': 0.15,
        'min_gross_margin': 0.20,
        'max_debt_to_equity': 2.0,
        'min_current_ratio': 1.0,
    }})
    
    # Analyze each stock
    analyzed_stocks = []
    
    for ticker, profile in stock_profiles.items():
        print(f"\n{'='*80}")
        print(f"Analyzing {ticker} - {profile['name']}")
        print('='*80)
        
        # Create sample data
        df = create_sample_stock_data(ticker, profile['base_price'], profile['volatility'], profile['trend'])
        info = create_sample_stock_info(ticker, profile)
        
        # Technical analysis
        print("  ⚙️  Running technical analysis...")
        tech_data = tech_analyzer.analyze_all(df, ticker)
        
        # Volatility analysis
        print("  📈 Running volatility analysis...")
        vol_data = vol_analyzer.analyze_all(df, ticker)
        
        # Fundamental analysis
        print("  💼 Running fundamental analysis...")
        fund_data = fund_analyzer.analyze_stock(ticker, info, {})
        
        # Calculate scores
        print("  🎯 Calculating VC scores...")
        scores = scorer.calculate_composite_score(fund_data, tech_data)
        
        # Get conviction and position size
        conviction = scorer.get_conviction_level(scores['composite_score'])
        position_size = scorer.get_position_size_recommendation(scores['composite_score'])
        
        # Combine all data
        result = {
            'ticker': ticker,
            **fund_data,
            **tech_data,
            **vol_data,
            **scores,
            'conviction': conviction,
            'position_size': position_size,
        }
        
        analyzed_stocks.append(result)
        
        # Display key metrics
        print(f"\n  📊 Results:")
        print(f"     Composite Score: {scores['composite_score']:.1f} ({scores['grade']})")
        print(f"     Next Week Range: ${vol_data['next_week_lower']:.2f} - ${vol_data['next_week_upper']:.2f}")
        print(f"     Conviction: {conviction}")
        print(f"     Position Size: {position_size*100:.1f}%")
    
    # Filter and rank
    print(f"\n{'='*80}")
    print("FILTERING AND RANKING STOCKS")
    print('='*80)
    
    filtered_stocks = ranker.apply_filters(analyzed_stocks)
    print(f"  ✅ {len(filtered_stocks)} stocks passed quality filters")
    
    ranked_df = ranker.rank_stocks(filtered_stocks)
    print(f"  📊 Stocks ranked by composite score")
    
    # Get top stocks
    top_stocks = ranker.get_top_stocks(ranked_df, n=5, min_score=60)
    
    # Sector analysis
    sector_allocation = ranker.get_sector_allocation(top_stocks)
    diversification = ranker.check_diversification(top_stocks, 0.40)
    
    # Generate report
    print(f"\n{'='*80}")
    print("GENERATING WEEKEND REPORT")
    print('='*80)
    
    report_gen = ReportGenerator(output_dir="reports")
    report_path = report_gen.generate_weekend_report(
        top_stocks,
        sector_allocation,
        diversification,
        datetime.now()
    )
    
    print(f"  ✅ Report generated: {report_path}")
    
    # Display summary
    print(f"\n{'='*80}")
    print("WEEKEND ANALYSIS SUMMARY")
    print('='*80)
    
    print(f"\nTop 5 Trading Opportunities for Next Week:\n")
    
    for _, stock in top_stocks.head(5).iterrows():
        print(f"  {stock['rank']}. {stock['ticker']} - {stock.get('company_name', 'N/A')}")
        print(f"     Score: {stock['composite_score']:.1f} ({stock['grade']}) | Conviction: {stock['conviction']}")
        print(f"     Current: ${stock['current_price']:.2f}")
        print(f"     Next Week: ${stock.get('next_week_lower', 0):.2f} - ${stock.get('next_week_upper', 0):.2f}")
        print(f"     ({stock.get('next_week_lower_pct', 0):.1f}% to {stock.get('next_week_upper_pct', 0):.1f}%)")
        print()
    
    print(f"{'='*80}")
    print("\n✅ END-TO-END DEMO COMPLETE!")
    print(f"\n📊 View the detailed HTML report: {report_path}")
    print("\n💡 This demonstrates the complete workflow:")
    print("   • Technical analysis with 7+ indicators")
    print("   • Fundamental analysis with growth/profitability metrics")
    print("   • Volatility analysis with next week predictions")
    print("   • VC-style scoring and ranking")
    print("   • Beautiful HTML report generation")
    print("\n🚀 In production, this will use real market data from yfinance")
    print(f"{'='*80}\n")


if __name__ == "__main__":
    run_end_to_end_demo()
