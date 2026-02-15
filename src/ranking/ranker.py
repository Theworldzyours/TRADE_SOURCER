"""
Stock ranking and filtering system
"""
import pandas as pd
from typing import List, Dict, Optional
from ..utils.logger import get_logger

logger = get_logger()


class StockRanker:
    """Rank and filter stocks based on scores and criteria"""
    
    def __init__(self, config: Dict = None):
        """
        Initialize stock ranker
        
        Args:
            config: Configuration dictionary
        """
        self.config = config or {}
        self.filters = self.config.get('filters', {})
    
    def apply_filters(self, stocks_data: List[Dict]) -> List[Dict]:
        """
        Apply quality and VC filters to stock list
        
        Args:
            stocks_data: List of stock data dictionaries
        
        Returns:
            Filtered list of stocks
        """
        filtered = []
        
        for stock in stocks_data:
            if self._passes_filters(stock):
                filtered.append(stock)
        
        logger.info(f"Filtered {len(stocks_data)} stocks down to {len(filtered)}")

        if len(filtered) == 0 and len(stocks_data) > 0:
            logger.warning(
                f"All {len(stocks_data)} stocks eliminated by filters: "
                f"min_market_cap={self.filters.get('min_market_cap', 100_000_000)}, "
                f"min_avg_volume={self.filters.get('min_avg_volume', 100_000)}, "
                f"min_revenue_growth={self.filters.get('min_revenue_growth', 0.15)}, "
                f"min_gross_margin={self.filters.get('min_gross_margin', 0.20)}, "
                f"max_debt_to_equity={self.filters.get('max_debt_to_equity', 2.0)}, "
                f"min_current_ratio={self.filters.get('min_current_ratio', 1.0)}"
            )

        return filtered
    
    def _passes_filters(self, stock: Dict) -> bool:
        """
        Check if stock passes all filters
        
        Args:
            stock: Stock data dictionary
        
        Returns:
            True if passes all filters
        """
        # Skip if error in data
        if 'error' in stock:
            return False
        
        # Basic filters
        market_cap = stock.get('market_cap', 0)
        avg_volume = stock.get('avg_volume', 0)
        current_price = stock.get('current_price', 0)
        
        if market_cap < self.filters.get('min_market_cap', 100_000_000):
            return False
        
        if avg_volume < self.filters.get('min_avg_volume', 100_000):
            return False
        
        if current_price < self.filters.get('min_price', 1.0):
            return False
        
        if current_price > self.filters.get('max_price', 10000):
            return False
        
        # Quality filters
        debt_to_equity = stock.get('debt_to_equity', 0)
        if debt_to_equity > self.filters.get('max_debt_to_equity', 2.0):
            return False
        
        current_ratio = stock.get('current_ratio', 0)
        if current_ratio < self.filters.get('min_current_ratio', 1.0):
            return False
        
        # Growth filters (VC approach)
        revenue_growth = stock.get('revenue_growth', 0)
        if revenue_growth < self.filters.get('min_revenue_growth', 0.15):
            return False
        
        gross_margin = stock.get('gross_margin', 0)
        if gross_margin < self.filters.get('min_gross_margin', 0.20):
            return False
        
        return True
    
    def rank_stocks(self, stocks_data: List[Dict]) -> pd.DataFrame:
        """
        Rank stocks by composite score
        
        Args:
            stocks_data: List of stock data dictionaries
        
        Returns:
            DataFrame with ranked stocks
        """
        if not stocks_data:
            logger.warning("No stocks to rank")
            return pd.DataFrame()
        
        # Convert to DataFrame
        df = pd.DataFrame(stocks_data)
        
        # Sort by composite score
        if 'composite_score' in df.columns:
            df = df.sort_values('composite_score', ascending=False)
        
        # Add rank
        df['rank'] = range(1, len(df) + 1)
        
        return df
    
    def categorize_by_risk(self, stocks_data: List[Dict]) -> Dict[str, List[Dict]]:
        """
        Categorize stocks by risk profile
        
        Args:
            stocks_data: List of stock data dictionaries
        
        Returns:
            Dictionary with stocks grouped by risk level
        """
        categories = {
            'conservative': [],
            'moderate': [],
            'aggressive': []
        }
        
        for stock in stocks_data:
            category = self._determine_risk_category(stock)
            categories[category].append(stock)
        
        return categories
    
    def _determine_risk_category(self, stock: Dict) -> str:
        """
        Determine risk category for a stock
        
        Args:
            stock: Stock data dictionary
        
        Returns:
            Risk category string
        """
        # Factors to consider
        market_cap = stock.get('market_cap', 0)
        revenue_growth = stock.get('revenue_growth', 0)
        debt_to_equity = stock.get('debt_to_equity', 0)
        profit_margin = stock.get('profit_margin', 0)
        
        risk_score = 0
        
        # Market cap (smaller = riskier)
        if market_cap < 2_000_000_000:  # < $2B
            risk_score += 2
        elif market_cap < 10_000_000_000:  # < $10B
            risk_score += 1
        
        # Growth rate (higher = riskier)
        if revenue_growth > 0.50:  # > 50%
            risk_score += 2
        elif revenue_growth > 0.30:  # > 30%
            risk_score += 1
        
        # Debt (higher = riskier)
        if debt_to_equity > 1.5:
            risk_score += 2
        elif debt_to_equity > 0.8:
            risk_score += 1
        
        # Profitability (unprofitable = riskier)
        if profit_margin < 0:
            risk_score += 2
        elif profit_margin < 0.05:
            risk_score += 1
        
        # Categorize
        if risk_score >= 5:
            return 'aggressive'
        elif risk_score >= 3:
            return 'moderate'
        else:
            return 'conservative'
    
    def group_by_sector(self, stocks_data: List[Dict]) -> Dict[str, List[Dict]]:
        """
        Group stocks by sector
        
        Args:
            stocks_data: List of stock data dictionaries
        
        Returns:
            Dictionary with stocks grouped by sector
        """
        sectors = {}
        
        for stock in stocks_data:
            sector = stock.get('sector', 'Unknown')
            if sector not in sectors:
                sectors[sector] = []
            sectors[sector].append(stock)
        
        return sectors
    
    def get_top_stocks(
        self,
        stocks_df: pd.DataFrame,
        n: int = 20,
        min_score: float = 60
    ) -> pd.DataFrame:
        """
        Get top N stocks above minimum score
        
        Args:
            stocks_df: DataFrame with ranked stocks
            n: Number of top stocks to return
            min_score: Minimum composite score
        
        Returns:
            DataFrame with top stocks
        """
        if stocks_df.empty:
            return stocks_df
        
        # Filter by minimum score
        filtered = stocks_df[stocks_df['composite_score'] >= min_score]
        
        # Return top N
        return filtered.head(n)
    
    def get_sector_allocation(self, stocks_df: pd.DataFrame) -> pd.DataFrame:
        """
        Calculate sector allocation in the portfolio
        
        Args:
            stocks_df: DataFrame with stocks
        
        Returns:
            DataFrame with sector allocation percentages
        """
        if stocks_df.empty or 'sector' not in stocks_df.columns:
            return pd.DataFrame()
        
        # Count stocks per sector
        sector_counts = stocks_df['sector'].value_counts()
        
        # Calculate percentages
        sector_allocation = pd.DataFrame({
            'sector': sector_counts.index,
            'count': sector_counts.values,
            'percentage': (sector_counts.values / len(stocks_df) * 100).round(2)
        })
        
        return sector_allocation
    
    def check_diversification(
        self,
        stocks_df: pd.DataFrame,
        max_sector_exposure: float = 0.40
    ) -> Dict:
        """
        Check if portfolio meets diversification requirements
        
        Args:
            stocks_df: DataFrame with stocks
            max_sector_exposure: Maximum allowed sector exposure
        
        Returns:
            Dictionary with diversification analysis
        """
        if stocks_df.empty:
            return {'diversified': True, 'warnings': []}
        
        sector_allocation = self.get_sector_allocation(stocks_df)
        
        warnings = []
        for _, row in sector_allocation.iterrows():
            if row['percentage'] / 100 > max_sector_exposure:
                warnings.append(
                    f"Sector '{row['sector']}' exceeds maximum exposure "
                    f"({row['percentage']:.1f}% > {max_sector_exposure*100:.1f}%)"
                )
        
        return {
            'diversified': len(warnings) == 0,
            'warnings': warnings,
            'sector_allocation': sector_allocation
        }
