"""
Trade Republic stock universe manager
"""
import pandas as pd
from pathlib import Path
from typing import List, Optional
from ..utils.logger import get_logger

logger = get_logger()


class TradeRepublicUniverse:
    """Manage the universe of stocks tradable on Trade Republic"""
    
    def __init__(self, universe_file: str = "data/trade_republic_stocks.csv"):
        """
        Initialize Trade Republic stock universe
        
        Args:
            universe_file: Path to CSV file with stock list
        """
        self.universe_file = Path(universe_file)
        self.stocks = None
        self.load_universe()
    
    def load_universe(self) -> Optional[pd.DataFrame]:
        """
        Load stock universe from file or create default
        
        Returns:
            DataFrame with stock information
        """
        if self.universe_file.exists():
            logger.info(f"Loading stock universe from {self.universe_file}")
            self.stocks = pd.read_csv(self.universe_file)
            logger.info(f"Loaded {len(self.stocks)} stocks")
        else:
            logger.warning(f"Universe file not found: {self.universe_file}")
            logger.info("Creating default stock universe")
            self.stocks = self._create_default_universe()
            self.save_universe()
        
        return self.stocks
    
    def _create_default_universe(self) -> pd.DataFrame:
        """
        Create a default stock universe with popular stocks on Trade Republic
        
        Returns:
            DataFrame with default stock list
        """
        # Sample of popular stocks available on Trade Republic
        # In production, this should be fetched from Trade Republic API or scraped
        default_stocks = [
            # US Tech Giants
            {'ticker': 'AAPL', 'name': 'Apple Inc.', 'exchange': 'NASDAQ', 'sector': 'Technology'},
            {'ticker': 'MSFT', 'name': 'Microsoft Corp.', 'exchange': 'NASDAQ', 'sector': 'Technology'},
            {'ticker': 'GOOGL', 'name': 'Alphabet Inc.', 'exchange': 'NASDAQ', 'sector': 'Technology'},
            {'ticker': 'AMZN', 'name': 'Amazon.com Inc.', 'exchange': 'NASDAQ', 'sector': 'Consumer Cyclical'},
            {'ticker': 'META', 'name': 'Meta Platforms Inc.', 'exchange': 'NASDAQ', 'sector': 'Technology'},
            {'ticker': 'TSLA', 'name': 'Tesla Inc.', 'exchange': 'NASDAQ', 'sector': 'Consumer Cyclical'},
            {'ticker': 'NVDA', 'name': 'NVIDIA Corp.', 'exchange': 'NASDAQ', 'sector': 'Technology'},
            
            # Growth Tech
            {'ticker': 'NFLX', 'name': 'Netflix Inc.', 'exchange': 'NASDAQ', 'sector': 'Communication Services'},
            {'ticker': 'ADBE', 'name': 'Adobe Inc.', 'exchange': 'NASDAQ', 'sector': 'Technology'},
            {'ticker': 'CRM', 'name': 'Salesforce Inc.', 'exchange': 'NYSE', 'sector': 'Technology'},
            {'ticker': 'SHOP', 'name': 'Shopify Inc.', 'exchange': 'NYSE', 'sector': 'Technology'},
            {'ticker': 'SQ', 'name': 'Block Inc.', 'exchange': 'NYSE', 'sector': 'Technology'},
            
            # FinTech & Payments
            {'ticker': 'PYPL', 'name': 'PayPal Holdings Inc.', 'exchange': 'NASDAQ', 'sector': 'Financial Services'},
            {'ticker': 'V', 'name': 'Visa Inc.', 'exchange': 'NYSE', 'sector': 'Financial Services'},
            {'ticker': 'MA', 'name': 'Mastercard Inc.', 'exchange': 'NYSE', 'sector': 'Financial Services'},
            
            # Healthcare & Biotech
            {'ticker': 'JNJ', 'name': 'Johnson & Johnson', 'exchange': 'NYSE', 'sector': 'Healthcare'},
            {'ticker': 'PFE', 'name': 'Pfizer Inc.', 'exchange': 'NYSE', 'sector': 'Healthcare'},
            {'ticker': 'MRNA', 'name': 'Moderna Inc.', 'exchange': 'NASDAQ', 'sector': 'Healthcare'},
            
            # German DAX Stocks
            {'ticker': 'SAP', 'name': 'SAP SE', 'exchange': 'XETRA', 'sector': 'Technology'},
            {'ticker': 'SIE.DE', 'name': 'Siemens AG', 'exchange': 'XETRA', 'sector': 'Industrials'},
            {'ticker': 'VOW3.DE', 'name': 'Volkswagen AG', 'exchange': 'XETRA', 'sector': 'Consumer Cyclical'},
            {'ticker': 'BMW.DE', 'name': 'BMW AG', 'exchange': 'XETRA', 'sector': 'Consumer Cyclical'},
            
            # European Stocks
            {'ticker': 'ASML', 'name': 'ASML Holding NV', 'exchange': 'NASDAQ', 'sector': 'Technology'},
            {'ticker': 'MC.PA', 'name': 'LVMH', 'exchange': 'EPA', 'sector': 'Consumer Cyclical'},
            
            # Semiconductors
            {'ticker': 'AMD', 'name': 'Advanced Micro Devices', 'exchange': 'NASDAQ', 'sector': 'Technology'},
            {'ticker': 'INTC', 'name': 'Intel Corp.', 'exchange': 'NASDAQ', 'sector': 'Technology'},
            
            # Electric Vehicles & Clean Energy
            {'ticker': 'NIO', 'name': 'NIO Inc.', 'exchange': 'NYSE', 'sector': 'Consumer Cyclical'},
            {'ticker': 'RIVN', 'name': 'Rivian Automotive', 'exchange': 'NASDAQ', 'sector': 'Consumer Cyclical'},
            
            # Cloud & Software
            {'ticker': 'SNOW', 'name': 'Snowflake Inc.', 'exchange': 'NYSE', 'sector': 'Technology'},
            {'ticker': 'PLTR', 'name': 'Palantir Technologies', 'exchange': 'NYSE', 'sector': 'Technology'},
        ]
        
        df = pd.DataFrame(default_stocks)
        df['active'] = True
        df['added_date'] = pd.Timestamp.now().strftime('%Y-%m-%d')
        
        logger.info(f"Created default universe with {len(df)} stocks")
        return df
    
    def save_universe(self):
        """Save stock universe to file"""
        self.universe_file.parent.mkdir(parents=True, exist_ok=True)
        self.stocks.to_csv(self.universe_file, index=False)
        logger.info(f"Saved stock universe to {self.universe_file}")
    
    def get_active_tickers(self) -> List[str]:
        """
        Get list of active tickers
        
        Returns:
            List of ticker symbols
        """
        if self.stocks is not None:
            active = self.stocks[self.stocks['active'] == True]
            return active['ticker'].tolist()
        return []
    
    def get_tickers_by_sector(self, sector: str) -> List[str]:
        """
        Get tickers filtered by sector
        
        Args:
            sector: Sector name
        
        Returns:
            List of ticker symbols
        """
        if self.stocks is not None:
            filtered = self.stocks[
                (self.stocks['active'] == True) & 
                (self.stocks['sector'] == sector)
            ]
            return filtered['ticker'].tolist()
        return []
    
    def add_stock(self, ticker: str, name: str, exchange: str, sector: str):
        """
        Add a new stock to the universe
        
        Args:
            ticker: Stock ticker symbol
            name: Company name
            exchange: Exchange name
            sector: Sector name
        """
        new_row = pd.DataFrame([{
            'ticker': ticker,
            'name': name,
            'exchange': exchange,
            'sector': sector,
            'active': True,
            'added_date': pd.Timestamp.now().strftime('%Y-%m-%d')
        }])
        
        self.stocks = pd.concat([self.stocks, new_row], ignore_index=True)
        self.save_universe()
        logger.info(f"Added {ticker} to universe")
    
    def deactivate_stock(self, ticker: str):
        """
        Deactivate a stock (mark as inactive)
        
        Args:
            ticker: Stock ticker symbol
        """
        self.stocks.loc[self.stocks['ticker'] == ticker, 'active'] = False
        self.save_universe()
        logger.info(f"Deactivated {ticker}")
    
    def update_universe(self):
        """
        Update the stock universe
        This is a placeholder for future implementation with Trade Republic API
        """
        logger.warning("Universe update not implemented - using existing list")
        # TODO: Implement actual Trade Republic stock list fetching
        # This would require scraping or API access to Trade Republic
