"""
Trade Sourcer - Main Application
Weekend stock analysis using VC approach
"""
import sys
import time
from pathlib import Path
from datetime import datetime
from typing import List, Dict

# Add src to path
sys.path.insert(0, str(Path(__file__).parent))

from src.utils.config_loader import get_config
from src.utils.logger import setup_logger, get_logger
from src.data_sources.trade_republic import TradeRepublicUniverse
from src.data_sources.market_data import MarketDataFetcher
from src.indicators.technical import TechnicalIndicators
from src.indicators.fundamental import FundamentalIndicators
from src.indicators.volatility import VolatilityAnalyzer
from src.scoring.vc_scorer import VCScorer
from src.ranking.ranker import StockRanker
from src.reports.report_generator import ReportGenerator


class TradeSourcer:
    """Main application class for Trade Sourcer"""
    
    def __init__(self, config_path: str = None):
        """
        Initialize Trade Sourcer
        
        Args:
            config_path: Path to configuration file
        """
        # Load configuration
        self.config = get_config(config_path)
        
        # Setup logger
        log_file = self.config.base_dir / self.config.get('logging.log_file', 'logs/trade_sourcer.log')
        log_level = self.config.get('logging.level', 'INFO')
        self.logger = setup_logger(log_file=str(log_file), level=log_level)
        
        self.logger.info("=" * 60)
        self.logger.info("Trade Sourcer - Initializing")
        self.logger.info("=" * 60)
        
        # Initialize components
        self.universe = TradeRepublicUniverse(
            str(self.config.data_dir / self.config.get('trade_republic.universe_file', 'trade_republic_stocks.csv'))
        )
        
        self.market_data = MarketDataFetcher(
            cache_enabled=self.config.get('data_sources.cache_enabled', True)
        )
        
        technical_config = self.config.get('technical_indicators', {})
        self.technical_analyzer = TechnicalIndicators(technical_config)
        
        fundamental_config = self.config.get('fundamental_indicators', {})
        self.fundamental_analyzer = FundamentalIndicators(fundamental_config)
        
        # Add volatility analyzer for next week predictions
        self.volatility_analyzer = VolatilityAnalyzer()
        
        scoring_config = self.config.get('scoring', {})
        self.scorer = VCScorer(scoring_config)
        
        filters_config = {'filters': self.config.get('filters', {})}
        self.ranker = StockRanker(filters_config)
        
        reporting_config = self.config.get('reporting', {})
        self.report_generator = ReportGenerator(
            reporting_config,
            str(self.config.reports_dir)
        )
        
        self.logger.info("Initialization complete")
    
    def run_analysis(self, tickers: List[str] = None) -> Dict:
        """
        Run complete analysis pipeline
        
        Args:
            tickers: Optional list of tickers to analyze. If None, uses Trade Republic universe
        
        Returns:
            Dictionary with analysis results
        """
        start_time = time.time()
        self.logger.info("Starting weekend analysis...")
        
        # Step 1: Get stock universe
        if tickers is None:
            tickers = self.universe.get_active_tickers()
        
        self.logger.info(f"Analyzing {len(tickers)} stocks")
        
        # Step 2: Fetch and analyze data
        analyzed_stocks = []
        
        for i, ticker in enumerate(tickers):
            self.logger.info(f"[{i+1}/{len(tickers)}] Analyzing {ticker}")
            
            try:
                stock_data = self._analyze_stock(ticker)
                if stock_data and 'error' not in stock_data:
                    analyzed_stocks.append(stock_data)
            except Exception as e:
                self.logger.error(f"Error analyzing {ticker}: {e}")
            
            # Rate limiting
            if i < len(tickers) - 1:
                time.sleep(0.5)
        
        self.logger.info(f"Successfully analyzed {len(analyzed_stocks)}/{len(tickers)} stocks")
        
        # Step 3: Filter and rank
        filtered_stocks = self.ranker.apply_filters(analyzed_stocks)
        ranked_df = self.ranker.rank_stocks(filtered_stocks)
        
        # Step 4: Get top stocks
        min_score = self.config.get('scoring.min_composite_score', 60)
        top_count = self.config.get('reporting.detailed_analysis_count', 20)
        top_stocks = self.ranker.get_top_stocks(ranked_df, n=top_count, min_score=min_score)
        
        # Step 5: Sector analysis
        sector_allocation = self.ranker.get_sector_allocation(top_stocks)
        max_sector_exposure = self.config.get('risk_management.max_sector_exposure', 0.40)
        diversification = self.ranker.check_diversification(top_stocks, max_sector_exposure)
        
        # Step 6: Generate report
        report_path = self.report_generator.generate_weekend_report(
            top_stocks,
            sector_allocation,
            diversification,
            datetime.now()
        )
        
        elapsed_time = time.time() - start_time
        self.logger.info(f"Analysis complete in {elapsed_time:.2f} seconds")
        self.logger.info(f"Report generated: {report_path}")
        
        return {
            'total_analyzed': len(analyzed_stocks),
            'total_filtered': len(filtered_stocks),
            'top_stocks_count': len(top_stocks),
            'report_path': report_path,
            'elapsed_time': elapsed_time
        }
    
    def _analyze_stock(self, ticker: str) -> Dict:
        """
        Analyze a single stock
        
        Args:
            ticker: Stock ticker symbol
        
        Returns:
            Dictionary with complete analysis
        """
        # Get market data
        historical_days = self.config.get('analysis.historical_days', 365)
        period = f"{historical_days}d"
        df = self.market_data.get_stock_data(ticker, period=period)
        
        if df is None or df.empty:
            return {'ticker': ticker, 'error': 'No market data'}
        
        # Get stock info and financials
        info = self.market_data.get_stock_info(ticker)
        if not info:
            return {'ticker': ticker, 'error': 'No stock info'}
        
        financials = self.market_data.get_financials(ticker)
        
        # Technical analysis
        technical_data = self.technical_analyzer.analyze_all(df, ticker)
        
        # Volatility and next week analysis
        volatility_data = self.volatility_analyzer.analyze_all(df, ticker)
        
        # Fundamental analysis
        fundamental_data = self.fundamental_analyzer.analyze_stock(ticker, info, financials)
        
        # Calculate scores
        scores = self.scorer.calculate_composite_score(
            fundamental_data,
            technical_data
        )
        
        # Get additional metrics
        conviction = self.scorer.get_conviction_level(scores['composite_score'])
        position_size = self.scorer.get_position_size_recommendation(scores['composite_score'])
        
        # Combine all data
        result = {
            'ticker': ticker,
            **fundamental_data,
            **technical_data,
            **volatility_data,
            **scores,
            'conviction': conviction,
            'position_size': position_size,
        }
        
        return result
    
    def print_summary(self, results: Dict):
        """
        Print analysis summary to console
        
        Args:
            results: Analysis results dictionary
        """
        print("\n" + "=" * 60)
        print("TRADE SOURCER - WEEKEND ANALYSIS COMPLETE")
        print("=" * 60)
        print(f"Total Stocks Analyzed: {results['total_analyzed']}")
        print(f"Stocks After Filtering: {results['total_filtered']}")
        print(f"Top Opportunities: {results['top_stocks_count']}")
        print(f"Analysis Time: {results['elapsed_time']:.2f} seconds")
        print(f"\nReport Generated: {results['report_path']}")
        print("=" * 60 + "\n")


def main():
    """Main entry point"""
    print("\n🚀 Trade Sourcer - Venture Capital Approach to Public Markets\n")
    
    try:
        # Initialize application
        app = TradeSourcer()
        
        # Run analysis
        results = app.run_analysis()
        
        # Print summary
        app.print_summary(results)
        
        print("✅ Analysis complete! Check the reports directory for details.\n")
        
    except KeyboardInterrupt:
        print("\n\n⚠️  Analysis interrupted by user.\n")
        sys.exit(1)
    except Exception as e:
        print(f"\n\n❌ Error: {e}\n")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()
