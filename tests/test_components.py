"""
Unit tests for Trade Sourcer components
"""
import unittest
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
import sys
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.indicators.technical import TechnicalIndicators
from src.indicators.fundamental import FundamentalIndicators
from src.scoring.vc_scorer import VCScorer
from src.ranking.ranker import StockRanker


class TestTechnicalIndicators(unittest.TestCase):
    """Test technical indicators calculations"""
    
    def setUp(self):
        """Create sample OHLCV data"""
        dates = pd.date_range(end=datetime.now(), periods=100, freq='D')
        np.random.seed(42)
        
        # Create realistic price data
        price = 100
        prices = []
        for _ in range(100):
            change = np.random.normal(0, 2)
            price = max(price + change, 50)  # Don't go too low
            prices.append(price)
        
        self.df = pd.DataFrame({
            'Open': prices,
            'High': [p * 1.02 for p in prices],
            'Low': [p * 0.98 for p in prices],
            'Close': prices,
            'Volume': np.random.randint(1000000, 5000000, 100)
        }, index=dates)
    
    def test_rsi_calculation(self):
        """Test RSI calculation"""
        tech = TechnicalIndicators()
        rsi = tech.calculate_rsi(self.df)
        
        self.assertIsNotNone(rsi)
        self.assertTrue(0 <= rsi.iloc[-1] <= 100)
    
    def test_macd_calculation(self):
        """Test MACD calculation"""
        tech = TechnicalIndicators()
        macd = tech.calculate_macd(self.df)
        
        self.assertIn('macd', macd)
        self.assertIn('signal', macd)
        self.assertIn('histogram', macd)
    
    def test_bollinger_bands(self):
        """Test Bollinger Bands calculation"""
        tech = TechnicalIndicators()
        bb = tech.calculate_bollinger_bands(self.df)
        
        self.assertIn('upper', bb)
        self.assertIn('middle', bb)
        self.assertIn('lower', bb)
        
        # Upper should be above lower
        self.assertGreater(bb['upper'].iloc[-1], bb['lower'].iloc[-1])
    
    def test_full_analysis(self):
        """Test complete technical analysis"""
        tech = TechnicalIndicators({'rsi_period': 14})
        result = tech.analyze_all(self.df, 'TEST')
        
        self.assertEqual(result['ticker'], 'TEST')
        self.assertIn('rsi', result)
        self.assertIn('technical_score', result)
        self.assertIn('signals', result)
        
        # Score should be between 0 and 100
        self.assertTrue(0 <= result['technical_score'] <= 100)


class TestFundamentalIndicators(unittest.TestCase):
    """Test fundamental indicators calculations"""
    
    def setUp(self):
        """Create sample fundamental data"""
        self.info = {
            'longName': 'Test Company Inc.',
            'sector': 'Technology',
            'industry': 'Software',
            'marketCap': 10_000_000_000,
            'revenueGrowth': 0.25,
            'earningsGrowth': 0.30,
            'grossMargins': 0.70,
            'operatingMargins': 0.25,
            'profitMargins': 0.20,
            'returnOnEquity': 0.25,
            'debtToEquity': 50,
            'currentRatio': 2.0,
            'freeCashflow': 1_000_000_000,
            'trailingPE': 30,
            'pegRatio': 1.2,
        }
        
        self.financials = {}
    
    def test_market_metrics(self):
        """Test market metrics calculation"""
        fund = FundamentalIndicators()
        result = fund._calculate_market_metrics(self.info)
        
        self.assertEqual(result['market_cap'], 10_000_000_000)
    
    def test_growth_metrics(self):
        """Test growth metrics calculation"""
        fund = FundamentalIndicators()
        result = fund._calculate_growth_metrics(self.info, self.financials)
        
        self.assertEqual(result['revenue_growth'], 0.25)
        self.assertEqual(result['earnings_growth'], 0.30)
    
    def test_profitability_metrics(self):
        """Test profitability metrics calculation"""
        fund = FundamentalIndicators()
        result = fund._calculate_profitability_metrics(self.info)
        
        self.assertEqual(result['gross_margin'], 0.70)
        self.assertEqual(result['operating_margin'], 0.25)
    
    def test_fundamental_score(self):
        """Test fundamental score calculation"""
        fund = FundamentalIndicators()
        result = fund.analyze_stock('TEST', self.info, self.financials)
        
        self.assertEqual(result['ticker'], 'TEST')
        self.assertIn('fundamental_score', result)
        self.assertTrue(0 <= result['fundamental_score'] <= 100)


class TestVCScorer(unittest.TestCase):
    """Test VC scoring system"""
    
    def setUp(self):
        """Create sample data"""
        self.fundamental = {
            'ticker': 'TEST',
            'sector': 'Technology',
            'market_cap': 5_000_000_000,
            'revenue_growth': 0.30,
            'earnings_growth': 0.25,
            'gross_margin': 0.60,
            'operating_margin': 0.20,
            'profit_margin': 0.15,
            'roe': 0.20,
            'roic': 0.18,
            'debt_to_equity': 0.5,
            'current_ratio': 2.0,
            'peg_ratio': 1.5,
        }
        
        self.technical = {
            'technical_score': 75,
            'signals': {
                'trend': 'uptrend',
                'rsi': 'neutral',
                'macd': 'bullish',
                'volume': 'normal',
            }
        }
    
    def test_innovation_score(self):
        """Test innovation score calculation"""
        scorer = VCScorer()
        score = scorer._calculate_innovation_score(self.fundamental, {})
        
        self.assertTrue(0 <= score <= 100)
    
    def test_growth_score(self):
        """Test growth score calculation"""
        scorer = VCScorer()
        score = scorer._calculate_growth_score(self.fundamental)
        
        self.assertTrue(0 <= score <= 100)
        # Should be high due to 30% revenue growth
        self.assertGreater(score, 50)
    
    def test_composite_score(self):
        """Test composite score calculation"""
        scorer = VCScorer()
        result = scorer.calculate_composite_score(
            self.fundamental,
            self.technical
        )
        
        self.assertIn('composite_score', result)
        self.assertIn('innovation_score', result)
        self.assertIn('growth_score', result)
        self.assertIn('grade', result)
        
        # Should be a reasonable grade
        self.assertIn(result['grade'][0], ['A', 'B', 'C', 'D', 'F'])
    
    def test_position_sizing(self):
        """Test position sizing recommendation"""
        scorer = VCScorer()
        
        # High score should recommend larger position
        size_high = scorer.get_position_size_recommendation(85, 'moderate')
        size_low = scorer.get_position_size_recommendation(55, 'moderate')
        
        self.assertGreater(size_high, size_low)
        self.assertLessEqual(size_high, 0.15)  # Max 15%


class TestStockRanker(unittest.TestCase):
    """Test stock ranking and filtering"""
    
    def setUp(self):
        """Create sample stock data"""
        self.stocks = [
            {
                'ticker': 'STOCK1',
                'market_cap': 5_000_000_000,
                'avg_volume': 500_000,
                'current_price': 100,
                'debt_to_equity': 0.5,
                'current_ratio': 2.0,
                'revenue_growth': 0.30,
                'gross_margin': 0.60,
                'composite_score': 85,
                'sector': 'Technology',
            },
            {
                'ticker': 'STOCK2',
                'market_cap': 200_000_000,
                'avg_volume': 50_000,
                'current_price': 50,
                'debt_to_equity': 3.0,
                'current_ratio': 0.8,
                'revenue_growth': 0.05,
                'gross_margin': 0.15,
                'composite_score': 45,
                'sector': 'Energy',
            },
            {
                'ticker': 'STOCK3',
                'market_cap': 2_000_000_000,
                'avg_volume': 200_000,
                'current_price': 75,
                'debt_to_equity': 1.0,
                'current_ratio': 1.5,
                'revenue_growth': 0.20,
                'gross_margin': 0.40,
                'composite_score': 72,
                'sector': 'Technology',
            },
        ]
    
    def test_filtering(self):
        """Test stock filtering"""
        ranker = StockRanker({'filters': {
            'min_market_cap': 500_000_000,
            'min_avg_volume': 100_000,
            'min_revenue_growth': 0.15,
            'min_gross_margin': 0.20,
        }})
        
        filtered = ranker.apply_filters(self.stocks)
        
        # STOCK2 should be filtered out (fails multiple filters)
        self.assertEqual(len(filtered), 2)
        tickers = [s['ticker'] for s in filtered]
        self.assertIn('STOCK1', tickers)
        self.assertIn('STOCK3', tickers)
        self.assertNotIn('STOCK2', tickers)
    
    def test_ranking(self):
        """Test stock ranking"""
        ranker = StockRanker()
        ranked_df = ranker.rank_stocks(self.stocks)
        
        self.assertEqual(len(ranked_df), 3)
        # STOCK1 should be ranked first (highest score)
        self.assertEqual(ranked_df.iloc[0]['ticker'], 'STOCK1')
        self.assertEqual(ranked_df.iloc[0]['rank'], 1)
    
    def test_sector_allocation(self):
        """Test sector allocation calculation"""
        ranker = StockRanker()
        df = pd.DataFrame(self.stocks)
        
        allocation = ranker.get_sector_allocation(df)
        
        self.assertIn('sector', allocation.columns)
        # Technology should have 2 stocks (66.7%)
        tech_row = allocation[allocation['sector'] == 'Technology']
        self.assertEqual(tech_row['count'].values[0], 2)


def run_tests():
    """Run all tests"""
    print("\n" + "=" * 60)
    print("Running Trade Sourcer Unit Tests")
    print("=" * 60 + "\n")
    
    # Create test suite
    loader = unittest.TestLoader()
    suite = unittest.TestSuite()
    
    # Add tests
    suite.addTests(loader.loadTestsFromTestCase(TestTechnicalIndicators))
    suite.addTests(loader.loadTestsFromTestCase(TestFundamentalIndicators))
    suite.addTests(loader.loadTestsFromTestCase(TestVCScorer))
    suite.addTests(loader.loadTestsFromTestCase(TestStockRanker))
    
    # Run tests
    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(suite)
    
    # Print summary
    print("\n" + "=" * 60)
    print(f"Tests run: {result.testsRun}")
    print(f"Failures: {len(result.failures)}")
    print(f"Errors: {len(result.errors)}")
    print(f"Success rate: {(result.testsRun - len(result.failures) - len(result.errors)) / result.testsRun * 100:.1f}%")
    print("=" * 60 + "\n")
    
    return result.wasSuccessful()


if __name__ == '__main__':
    success = run_tests()
    sys.exit(0 if success else 1)
