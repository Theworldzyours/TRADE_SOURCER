"""
Trade Sourcer - Dark Flow Intelligence System
Weekend stock analysis with hidden signal detection
"""
import sys
import time
import threading
from pathlib import Path
from datetime import datetime
from typing import List, Dict, Optional
from concurrent.futures import ThreadPoolExecutor, as_completed

# Add src to path
sys.path.insert(0, str(Path(__file__).parent))

from src.utils.config_loader import get_config
from src.utils.logger import setup_logger, get_logger

# Data sources
from src.data_sources.trade_republic import TradeRepublicUniverse
from src.data_sources.market_data import MarketDataFetcher

# Traditional indicators
from src.indicators.technical import TechnicalIndicators
from src.indicators.fundamental import FundamentalIndicators
from src.indicators.volatility import VolatilityAnalyzer

# Scoring
from src.scoring.vc_scorer import VCScorer
from src.scoring.conviction_engine import ConvictionEngine

# Ranking & reports
from src.ranking.ranker import StockRanker
from src.reports.report_generator import ReportGenerator

# Signal detectors (graceful imports — each is optional)
try:
    from src.signals.insider_flow import InsiderFlowDetector
except ImportError:
    InsiderFlowDetector = None

try:
    from src.signals.dark_pool import DarkPoolAnalyzer
except ImportError:
    DarkPoolAnalyzer = None

try:
    from src.signals.options_flow import OptionsFlowScanner
except ImportError:
    OptionsFlowScanner = None

try:
    from src.signals.congress_trades import CongressTradesTracker
except ImportError:
    CongressTradesTracker = None

try:
    from src.signals.ftd_tracker import FTDShortTracker
except ImportError:
    FTDShortTracker = None

try:
    from src.signals.social_sentiment import SocialSentimentScorer
except ImportError:
    SocialSentimentScorer = None

# Dark flow report (optional — falls back to standard report)
try:
    from src.reports.dark_flow_report import DarkFlowReportGenerator
except ImportError:
    DarkFlowReportGenerator = None


class TradeSourcer:
    """Main application class for Trade Sourcer — Dark Flow Intelligence"""

    def __init__(self, config_path: str = None):
        # Load configuration
        self.config = get_config(config_path)

        # Setup logger
        log_file = self.config.base_dir / self.config.get('logging.log_file', 'logs/trade_sourcer.log')
        log_level = self.config.get('logging.level', 'INFO')
        self.logger = setup_logger(log_file=str(log_file), level=log_level)

        self.logger.info("=" * 60)
        self.logger.info("Trade Sourcer - Dark Flow Intelligence - Initializing")
        self.logger.info("=" * 60)

        # Initialize data sources
        self.universe = TradeRepublicUniverse(
            str(self.config.data_dir / self.config.get('trade_republic.universe_file', 'trade_republic_stocks.csv'))
        )
        self.market_data = MarketDataFetcher(
            cache_enabled=self.config.get('data_sources.cache_enabled', True)
        )

        # Initialize traditional analyzers
        self.technical_analyzer = TechnicalIndicators(self.config.get('technical_indicators', {}))
        self.fundamental_analyzer = FundamentalIndicators(self.config.get('fundamental_indicators', {}))
        self.volatility_analyzer = VolatilityAnalyzer()

        # Initialize scoring (both old + new)
        self.vc_scorer = VCScorer(self.config.get('scoring', {}))
        self.conviction_engine = ConvictionEngine(self.config.get('conviction', {}))

        # Initialize ranking & reporting
        self.ranker = StockRanker({'filters': self.config.get('filters', {})})
        self.report_generator = ReportGenerator(
            self.config.get('reporting', {}),
            str(self.config.reports_dir)
        )

        # Initialize dark flow report if available
        self.dark_flow_report = None
        if DarkFlowReportGenerator is not None:
            self.dark_flow_report = DarkFlowReportGenerator(
                self.config.get('reporting', {}),
                str(self.config.reports_dir)
            )

        # Initialize signal detectors (graceful — each is optional)
        signals_config = self.config.get('signals', {})
        self.signal_detectors = {}

        if InsiderFlowDetector is not None:
            self.signal_detectors['insider'] = InsiderFlowDetector(signals_config.get('sec_edgar', {}))
            self.logger.info("  Signal: Insider Flow (SEC Form 4) ✓")

        if DarkPoolAnalyzer is not None:
            self.signal_detectors['darkpool'] = DarkPoolAnalyzer(signals_config.get('finra', {}))
            self.logger.info("  Signal: Dark Pool (FINRA) ✓")

        if OptionsFlowScanner is not None:
            self.signal_detectors['options'] = OptionsFlowScanner(signals_config.get('tradier', {}))
            self.logger.info("  Signal: Options Flow (Tradier) ✓")

        if CongressTradesTracker is not None:
            self.signal_detectors['congress'] = CongressTradesTracker(signals_config.get('congress', {}))
            self.logger.info("  Signal: Congressional Trades ✓")

        if FTDShortTracker is not None:
            self.signal_detectors['ftd'] = FTDShortTracker(signals_config.get('ftd', {}))
            self.logger.info("  Signal: FTD/Short Interest ✓")

        if SocialSentimentScorer is not None:
            self.signal_detectors['social'] = SocialSentimentScorer(signals_config.get('social', {}))
            self.logger.info("  Signal: Social Sentiment ✓")

        active_count = len(self.signal_detectors)
        self.logger.info(f"Initialization complete — {active_count}/6 signal detectors active")

    def run_analysis(self, tickers: List[str] = None) -> Dict:
        """Run complete dark flow analysis pipeline"""
        start_time = time.time()
        self.logger.info("Starting dark flow analysis...")

        # Step 1: Get stock universe
        if tickers is None:
            tickers = self.universe.get_active_tickers()

        total = len(tickers)
        self.logger.info(f"Analyzing {total} stocks")
        print(f"\nScanning {total} stocks for dark flow signals...\n")

        # Step 2: Fetch and analyze data (parallelized)
        analyzed_stocks = []
        failed_stocks = []
        progress_lock = threading.Lock()
        completed_count = [0]

        def analyze_stock_safe(ticker):
            try:
                return self._analyze_stock(ticker)
            except Exception as e:
                self.logger.error(f"Error analyzing {ticker}: {e}")
                return {'ticker': ticker, '_exception': str(e)}

        with ThreadPoolExecutor(max_workers=5) as executor:
            futures = {executor.submit(analyze_stock_safe, t): t for t in tickers}
            for future in as_completed(futures):
                ticker = futures[future]
                stock_data = future.result()
                with progress_lock:
                    completed_count[0] += 1
                    idx = f"[{completed_count[0]}/{total}]"
                    if stock_data and '_exception' in stock_data:
                        error_msg = stock_data['_exception']
                        failed_stocks.append((ticker, error_msg))
                        print(f"{idx} {ticker} \u2717 (error: {error_msg})")
                    elif stock_data and 'error' not in stock_data:
                        analyzed_stocks.append(stock_data)
                        conv_level = stock_data.get('conviction_level', 'TECHNICAL_ONLY')
                        conv_score = stock_data.get('conviction_score', stock_data.get('composite_score', 0))
                        dark_count = stock_data.get('active_dark_signal_count', 0)
                        suffix = f" [{dark_count} signals]" if dark_count > 0 else ""
                        print(f"{idx} {ticker} \u2713 ({conv_level} {conv_score:.0f}){suffix}")
                    else:
                        error_msg = stock_data.get('error', 'unknown') if stock_data else 'no data'
                        failed_stocks.append((ticker, error_msg))
                        print(f"{idx} {ticker} \u2717 ({error_msg})")

        success_count = len(analyzed_stocks)
        fail_count = len(failed_stocks)
        print(f"\nAnalysis complete: {success_count}/{total} stocks analyzed, {fail_count} failed")

        # Step 3: Filter and rank
        filtered_stocks = self.ranker.apply_filters(analyzed_stocks)
        ranked_df = self.ranker.rank_stocks(filtered_stocks)

        # Step 4: Get top stocks (use conviction_score if available, else composite_score)
        min_score = self.config.get('scoring.min_composite_score', 60)
        top_count = self.config.get('reporting.detailed_analysis_count', 20)
        top_stocks = self.ranker.get_top_stocks(ranked_df, n=top_count, min_score=min_score)

        # Step 5: Sector analysis
        sector_allocation = self.ranker.get_sector_allocation(top_stocks)
        max_sector_exposure = self.config.get('risk_management.max_sector_exposure', 0.40)
        diversification = self.ranker.check_diversification(top_stocks, max_sector_exposure)

        # Step 6: Identify dark flow alerts
        dark_flow_alerts = [
            s for s in analyzed_stocks
            if s.get('conviction_level') == 'DARK_FLOW_ALERT'
        ]
        strong_signals = [
            s for s in analyzed_stocks
            if s.get('conviction_level') == 'STRONG_SIGNAL'
        ]

        # Step 7: Generate reports
        # Always generate standard report
        report_path = self.report_generator.generate_weekend_report(
            top_stocks, sector_allocation, diversification, datetime.now()
        )

        # Generate dark flow report if available
        dark_flow_report_path = None
        if self.dark_flow_report is not None:
            try:
                dark_flow_report_path = self.dark_flow_report.generate_dark_flow_report(
                    all_stocks=analyzed_stocks,
                    dark_flow_alerts=dark_flow_alerts,
                    sector_allocation=sector_allocation,
                    analysis_date=datetime.now(),
                )
                self.logger.info(f"Dark Flow report generated: {dark_flow_report_path}")
            except Exception as e:
                self.logger.error(f"Dark Flow report generation failed: {e}")

        elapsed_time = time.time() - start_time
        self.logger.info(f"Analysis complete in {elapsed_time:.2f} seconds")

        return {
            'total_analyzed': success_count,
            'total_filtered': len(filtered_stocks),
            'top_stocks_count': len(top_stocks),
            'dark_flow_alerts': len(dark_flow_alerts),
            'strong_signals': len(strong_signals),
            'report_path': report_path,
            'dark_flow_report_path': dark_flow_report_path,
            'elapsed_time': elapsed_time,
            'active_signals': len(self.signal_detectors),
        }

    def _analyze_stock(self, ticker: str) -> Dict:
        """Analyze a single stock with all signals"""
        # Get market data
        historical_days = self.config.get('analysis.historical_days', 365)
        period = f"{historical_days}d"
        df = self.market_data.get_stock_data(ticker, period=period)

        if df is None or df.empty:
            return {'ticker': ticker, 'error': 'No market data'}

        info = self.market_data.get_stock_info(ticker)
        if not info:
            return {'ticker': ticker, 'error': 'No stock info'}

        financials = self.market_data.get_financials(ticker)

        # Traditional analysis
        technical_data = self.technical_analyzer.analyze_all(df, ticker)
        volatility_data = self.volatility_analyzer.analyze_all(df, ticker)
        fundamental_data = self.fundamental_analyzer.analyze_stock(ticker, info, financials)

        # VC scoring (backward compat)
        vc_scores = self.vc_scorer.calculate_composite_score(fundamental_data, technical_data)

        # Dark flow signal analysis
        signal_data = {}

        if 'insider' in self.signal_detectors:
            try:
                signal_data.update(self.signal_detectors['insider'].analyze_stock(ticker))
            except Exception as e:
                self.logger.debug(f"Insider signal failed for {ticker}: {e}")

        if 'darkpool' in self.signal_detectors:
            try:
                signal_data.update(self.signal_detectors['darkpool'].analyze_stock(ticker))
            except Exception as e:
                self.logger.debug(f"Dark pool signal failed for {ticker}: {e}")

        if 'options' in self.signal_detectors:
            try:
                signal_data.update(self.signal_detectors['options'].analyze_stock(ticker))
            except Exception as e:
                self.logger.debug(f"Options signal failed for {ticker}: {e}")

        if 'congress' in self.signal_detectors:
            try:
                signal_data.update(self.signal_detectors['congress'].analyze_stock(ticker))
            except Exception as e:
                self.logger.debug(f"Congress signal failed for {ticker}: {e}")

        if 'ftd' in self.signal_detectors:
            try:
                signal_data.update(self.signal_detectors['ftd'].analyze_stock(ticker))
            except Exception as e:
                self.logger.debug(f"FTD signal failed for {ticker}: {e}")

        if 'social' in self.signal_detectors:
            try:
                signal_data.update(self.signal_detectors['social'].analyze_stock(ticker))
            except Exception as e:
                self.logger.debug(f"Social signal failed for {ticker}: {e}")

        # Combine all data
        _safe_overlaps = {'ticker', 'current_price'}
        all_keys = (
            list(fundamental_data.keys()) + list(technical_data.keys()) +
            list(volatility_data.keys()) + list(vc_scores.keys()) + list(signal_data.keys())
        )
        duplicates = [k for k in set(all_keys) if all_keys.count(k) > 1 and k not in _safe_overlaps]
        if duplicates:
            self.logger.warning(f"Key collisions for {ticker}: {duplicates}")

        result = {
            'ticker': ticker,
            'company_name': info.get('longName', info.get('shortName', ticker)),
            'current_price': info.get('currentPrice', info.get('regularMarketPrice', 0)),
            **fundamental_data,
            **technical_data,
            **volatility_data,
            **vc_scores,
            **signal_data,
        }

        # Conviction scoring (uses combined data including signals)
        conviction_result = self.conviction_engine.calculate_conviction_score(result)
        result.update(conviction_result)

        return result

    def print_summary(self, results: Dict):
        """Print analysis summary"""
        print("\n" + "=" * 60)
        print("TRADE SOURCER - DARK FLOW INTELLIGENCE REPORT")
        print("=" * 60)
        print(f"Stocks Analyzed:     {results['total_analyzed']}")
        print(f"After Filtering:     {results['total_filtered']}")
        print(f"Top Opportunities:   {results['top_stocks_count']}")
        print(f"Dark Flow Alerts:    {results['dark_flow_alerts']}")
        print(f"Strong Signals:      {results['strong_signals']}")
        print(f"Active Detectors:    {results['active_signals']}/6")
        print(f"Analysis Time:       {results['elapsed_time']:.2f}s")
        print(f"\nStandard Report: {results['report_path']}")
        if results.get('dark_flow_report_path'):
            print(f"Dark Flow Report: {results['dark_flow_report_path']}")
        print("=" * 60 + "\n")


def main():
    """Main entry point"""
    print("\n\u26a1 Trade Sourcer - Dark Flow Intelligence System\n")

    try:
        app = TradeSourcer()
        results = app.run_analysis()
        app.print_summary(results)
        print("\u2705 Analysis complete! Check the reports directory for details.\n")

    except FileNotFoundError as e:
        if 'config' in str(e).lower() or 'yaml' in str(e).lower():
            print("\n\n\u274c Config not found at config/config.yaml. Run 'bash setup.sh' to set up the project.\n")
        else:
            print(f"\n\n\u274c File not found: {e}\n")
        sys.exit(1)
    except KeyboardInterrupt:
        print("\n\n\u26a0\ufe0f  Analysis interrupted by user.\n")
        sys.exit(1)
    except Exception as e:
        print(f"\n\n\u274c Error: {e}\n")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()
