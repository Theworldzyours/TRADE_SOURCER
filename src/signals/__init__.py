"""
Signal detectors for Trade Sourcer
"""
try:
    from .insider_flow import InsiderFlowDetector
except ImportError:
    InsiderFlowDetector = None

try:
    from .congress_trades import CongressTradesTracker
except ImportError:
    CongressTradesTracker = None

try:
    from .options_flow import OptionsFlowScanner
except ImportError:
    OptionsFlowScanner = None

try:
    from .dark_pool import DarkPoolAnalyzer
except ImportError:
    DarkPoolAnalyzer = None

try:
    from .social_sentiment import SocialSentimentScorer
except ImportError:
    SocialSentimentScorer = None

try:
    from .ftd_tracker import FTDShortTracker
except ImportError:
    FTDShortTracker = None

__all__ = [
    'InsiderFlowDetector',
    'CongressTradesTracker',
    'OptionsFlowScanner',
    'DarkPoolAnalyzer',
    'SocialSentimentScorer',
    'FTDShortTracker',
]
