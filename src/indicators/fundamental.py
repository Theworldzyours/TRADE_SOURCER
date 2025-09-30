"""
Fundamental indicators calculator
"""
import pandas as pd
import numpy as np
from typing import Dict, Optional
from ..utils.logger import get_logger

logger = get_logger()


class FundamentalIndicators:
    """Calculate fundamental indicators for stocks"""
    
    def __init__(self, config: Dict = None):
        """
        Initialize fundamental indicators calculator
        
        Args:
            config: Configuration dictionary
        """
        self.config = config or {}
    
    def analyze_stock(self, ticker: str, info: Dict, financials: Dict) -> Dict:
        """
        Analyze fundamental indicators for a stock
        
        Args:
            ticker: Stock ticker symbol
            info: Stock information from yfinance
            financials: Financial statements
        
        Returns:
            Dictionary with fundamental analysis
        """
        try:
            result = {
                'ticker': ticker,
                'company_name': info.get('longName', 'N/A'),
                'sector': info.get('sector', 'N/A'),
                'industry': info.get('industry', 'N/A'),
            }
            
            # Market metrics
            result.update(self._calculate_market_metrics(info))
            
            # Growth metrics
            result.update(self._calculate_growth_metrics(info, financials))
            
            # Profitability metrics
            result.update(self._calculate_profitability_metrics(info))
            
            # Quality metrics
            result.update(self._calculate_quality_metrics(info))
            
            # Valuation metrics
            result.update(self._calculate_valuation_metrics(info))
            
            # Calculate fundamental score
            result['fundamental_score'] = self._calculate_fundamental_score(result)
            
            return result
        
        except Exception as e:
            logger.error(f"Error analyzing fundamentals for {ticker}: {e}")
            return {'ticker': ticker, 'error': str(e)}
    
    def _calculate_market_metrics(self, info: Dict) -> Dict:
        """Calculate market-related metrics"""
        return {
            'market_cap': info.get('marketCap', 0),
            'enterprise_value': info.get('enterpriseValue', 0),
            'shares_outstanding': info.get('sharesOutstanding', 0),
            'float_shares': info.get('floatShares', 0),
            'avg_volume': info.get('averageVolume', 0),
        }
    
    def _calculate_growth_metrics(self, info: Dict, financials: Dict) -> Dict:
        """Calculate growth metrics"""
        metrics = {}
        
        # Revenue growth
        metrics['revenue_growth'] = info.get('revenueGrowth', 0)
        metrics['revenue_growth_yoy'] = info.get('revenueGrowth', 0)  # YoY
        
        # Earnings growth
        metrics['earnings_growth'] = info.get('earningsGrowth', 0)
        metrics['earnings_growth_quarterly'] = info.get('earningsQuarterlyGrowth', 0)
        
        # Other growth indicators
        metrics['book_value'] = info.get('bookValue', 0)
        
        # Calculate revenue CAGR if financial data available
        if 'income_statement' in financials and not financials['income_statement'].empty:
            try:
                income = financials['income_statement']
                if 'Total Revenue' in income.index:
                    revenues = income.loc['Total Revenue'].values
                    if len(revenues) >= 2:
                        # Calculate CAGR
                        n_years = len(revenues) - 1
                        if revenues[-1] > 0 and revenues[0] > 0:
                            cagr = (revenues[-1] / revenues[0]) ** (1/n_years) - 1
                            metrics['revenue_cagr'] = cagr
            except Exception as e:
                logger.debug(f"Could not calculate revenue CAGR: {e}")
        
        return metrics
    
    def _calculate_profitability_metrics(self, info: Dict) -> Dict:
        """Calculate profitability metrics"""
        return {
            'gross_margin': info.get('grossMargins', 0),
            'operating_margin': info.get('operatingMargins', 0),
            'profit_margin': info.get('profitMargins', 0),
            'ebitda_margin': info.get('ebitdaMargins', 0),
            'roe': info.get('returnOnEquity', 0),
            'roa': info.get('returnOnAssets', 0),
            'roic': info.get('returnOnCapital', 0),  # Not always available
        }
    
    def _calculate_quality_metrics(self, info: Dict) -> Dict:
        """Calculate quality/health metrics"""
        metrics = {
            'debt_to_equity': info.get('debtToEquity', 0) / 100 if info.get('debtToEquity') else 0,
            'current_ratio': info.get('currentRatio', 0),
            'quick_ratio': info.get('quickRatio', 0),
            'free_cash_flow': info.get('freeCashflow', 0),
            'operating_cash_flow': info.get('operatingCashflow', 0),
        }
        
        # Calculate interest coverage if data available
        if info.get('ebitda') and info.get('interestExpense'):
            ebitda = info.get('ebitda', 0)
            interest = info.get('interestExpense', 1)  # Avoid division by zero
            if interest != 0:
                metrics['interest_coverage'] = ebitda / abs(interest)
        
        return metrics
    
    def _calculate_valuation_metrics(self, info: Dict) -> Dict:
        """Calculate valuation metrics"""
        metrics = {
            'pe_ratio': info.get('trailingPE', 0),
            'forward_pe': info.get('forwardPE', 0),
            'peg_ratio': info.get('pegRatio', 0),
            'price_to_book': info.get('priceToBook', 0),
            'price_to_sales': info.get('priceToSalesTrailing12Months', 0),
            'ev_to_revenue': info.get('enterpriseToRevenue', 0),
            'ev_to_ebitda': info.get('enterpriseToEbitda', 0),
        }
        
        return metrics
    
    def _calculate_fundamental_score(self, result: Dict) -> float:
        """
        Calculate overall fundamental score (0-100)
        Based on VC approach: growth + profitability + quality
        
        Args:
            result: Dictionary with all fundamental metrics
        
        Returns:
            Fundamental score
        """
        score = 0.0
        max_score = 100.0
        
        # Growth Score (40 points)
        growth_score = 0
        
        # Revenue growth (20 points)
        rev_growth = result.get('revenue_growth', 0)
        if rev_growth > 0.30:  # 30%+ growth
            growth_score += 20
        elif rev_growth > 0.20:  # 20%+ growth
            growth_score += 15
        elif rev_growth > 0.15:  # 15%+ growth
            growth_score += 10
        elif rev_growth > 0.10:  # 10%+ growth
            growth_score += 5
        
        # Earnings growth (20 points)
        earnings_growth = result.get('earnings_growth', 0)
        if earnings_growth > 0.30:
            growth_score += 20
        elif earnings_growth > 0.20:
            growth_score += 15
        elif earnings_growth > 0.15:
            growth_score += 10
        elif earnings_growth > 0.10:
            growth_score += 5
        
        # Profitability Score (30 points)
        profitability_score = 0
        
        # Gross margin (10 points)
        gross_margin = result.get('gross_margin', 0)
        if gross_margin > 0.60:  # 60%+ margin
            profitability_score += 10
        elif gross_margin > 0.40:  # 40%+ margin
            profitability_score += 7
        elif gross_margin > 0.20:  # 20%+ margin
            profitability_score += 4
        
        # Operating margin (10 points)
        op_margin = result.get('operating_margin', 0)
        if op_margin > 0.20:  # 20%+ margin
            profitability_score += 10
        elif op_margin > 0.10:  # 10%+ margin
            profitability_score += 7
        elif op_margin > 0.05:  # 5%+ margin
            profitability_score += 4
        
        # ROE (10 points)
        roe = result.get('roe', 0)
        if roe > 0.20:  # 20%+ ROE
            profitability_score += 10
        elif roe > 0.15:  # 15%+ ROE
            profitability_score += 7
        elif roe > 0.10:  # 10%+ ROE
            profitability_score += 4
        
        # Quality Score (30 points)
        quality_score = 0
        
        # Debt to equity (10 points)
        debt_to_equity = result.get('debt_to_equity', 0)
        if debt_to_equity < 0.5:
            quality_score += 10
        elif debt_to_equity < 1.0:
            quality_score += 7
        elif debt_to_equity < 2.0:
            quality_score += 4
        
        # Current ratio (10 points)
        current_ratio = result.get('current_ratio', 0)
        if current_ratio > 2.0:
            quality_score += 10
        elif current_ratio > 1.5:
            quality_score += 7
        elif current_ratio > 1.0:
            quality_score += 4
        
        # Free cash flow positive (10 points)
        fcf = result.get('free_cash_flow', 0)
        if fcf > 0:
            quality_score += 10
        
        # Calculate total score
        score = growth_score + profitability_score + quality_score
        
        # Normalize to 0-100
        score = min(100, max(0, score))
        
        return round(score, 2)
    
    def get_growth_category(self, result: Dict) -> str:
        """
        Categorize company by growth profile
        
        Args:
            result: Fundamental analysis result
        
        Returns:
            Growth category string
        """
        rev_growth = result.get('revenue_growth', 0)
        
        if rev_growth > 0.50:
            return "hyper_growth"
        elif rev_growth > 0.30:
            return "high_growth"
        elif rev_growth > 0.15:
            return "growth"
        elif rev_growth > 0.05:
            return "moderate_growth"
        else:
            return "slow_growth"
