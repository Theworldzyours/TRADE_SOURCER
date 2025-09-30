"""
Venture Capital-style scoring system for stocks
"""
from typing import Dict, Optional
import numpy as np
from ..utils.logger import get_logger

logger = get_logger()


class VCScorer:
    """
    Score stocks using a Venture Capital approach
    Focus on growth potential, innovation, and asymmetric risk/reward
    """
    
    def __init__(self, config: Dict = None):
        """
        Initialize VC scorer
        
        Args:
            config: Configuration dictionary with scoring weights
        """
        self.config = config or {}
        self.weights = {
            'innovation': self.config.get('innovation_weight', 0.25),
            'growth': self.config.get('growth_weight', 0.25),
            'team': self.config.get('team_weight', 0.15),
            'risk_reward': self.config.get('risk_reward_weight', 0.20),
            'technical': self.config.get('technical_weight', 0.15),
        }
    
    def calculate_composite_score(
        self,
        fundamental_data: Dict,
        technical_data: Dict,
        additional_data: Dict = None
    ) -> Dict:
        """
        Calculate composite VC score
        
        Args:
            fundamental_data: Fundamental analysis results
            technical_data: Technical analysis results
            additional_data: Additional data (sentiment, insider trading, etc.)
        
        Returns:
            Dictionary with scores and breakdown
        """
        additional_data = additional_data or {}
        
        # Calculate individual scores
        innovation_score = self._calculate_innovation_score(fundamental_data, additional_data)
        growth_score = self._calculate_growth_score(fundamental_data)
        team_score = self._calculate_team_score(fundamental_data, additional_data)
        risk_reward_score = self._calculate_risk_reward_score(fundamental_data, technical_data)
        technical_score = technical_data.get('technical_score', 50)
        
        # Calculate weighted composite score
        composite = (
            innovation_score * self.weights['innovation'] +
            growth_score * self.weights['growth'] +
            team_score * self.weights['team'] +
            risk_reward_score * self.weights['risk_reward'] +
            technical_score * self.weights['technical']
        )
        
        return {
            'composite_score': round(composite, 2),
            'innovation_score': round(innovation_score, 2),
            'growth_score': round(growth_score, 2),
            'team_score': round(team_score, 2),
            'risk_reward_score': round(risk_reward_score, 2),
            'technical_score': round(technical_score, 2),
            'grade': self._get_grade(composite)
        }
    
    def _calculate_innovation_score(self, fundamental: Dict, additional: Dict) -> float:
        """
        Calculate innovation score (0-100)
        Measures disruptive potential and competitive moat
        
        Args:
            fundamental: Fundamental data
            additional: Additional data
        
        Returns:
            Innovation score
        """
        score = 50.0  # Start neutral
        
        # Sector-based innovation score
        sector = fundamental.get('sector', '')
        high_innovation_sectors = ['Technology', 'Healthcare', 'Communication Services']
        moderate_innovation_sectors = ['Consumer Cyclical', 'Industrials']
        
        if sector in high_innovation_sectors:
            score += 20
        elif sector in moderate_innovation_sectors:
            score += 10
        
        # High gross margins indicate pricing power/moat
        gross_margin = fundamental.get('gross_margin', 0)
        if gross_margin > 0.70:  # 70%+ margins
            score += 15
        elif gross_margin > 0.50:  # 50%+ margins
            score += 10
        elif gross_margin > 0.40:  # 40%+ margins
            score += 5
        
        # High R&D spending (for tech companies)
        # This would require additional data from financial statements
        
        # Market leadership (high market cap in sector)
        market_cap = fundamental.get('market_cap', 0)
        if market_cap > 100_000_000_000:  # $100B+
            score += 10
        elif market_cap > 10_000_000_000:  # $10B+
            score += 5
        
        # Network effects / scalability (high operating leverage)
        op_margin = fundamental.get('operating_margin', 0)
        if op_margin > 0.30:  # 30%+ operating margin
            score += 10
        elif op_margin > 0.20:  # 20%+ operating margin
            score += 5
        
        return min(100, max(0, score))
    
    def _calculate_growth_score(self, fundamental: Dict) -> float:
        """
        Calculate growth score (0-100)
        Measures revenue and earnings growth trajectory
        
        Args:
            fundamental: Fundamental data
        
        Returns:
            Growth score
        """
        score = 0.0
        
        # Revenue growth (50 points max)
        rev_growth = fundamental.get('revenue_growth', 0)
        if rev_growth > 0.50:  # 50%+ growth
            score += 50
        elif rev_growth > 0.40:  # 40%+ growth
            score += 45
        elif rev_growth > 0.30:  # 30%+ growth
            score += 40
        elif rev_growth > 0.20:  # 20%+ growth
            score += 30
        elif rev_growth > 0.15:  # 15%+ growth
            score += 20
        elif rev_growth > 0.10:  # 10%+ growth
            score += 10
        elif rev_growth > 0:  # Positive growth
            score += 5
        
        # Earnings growth (30 points max)
        earnings_growth = fundamental.get('earnings_growth', 0)
        if earnings_growth > 0.50:
            score += 30
        elif earnings_growth > 0.30:
            score += 25
        elif earnings_growth > 0.20:
            score += 20
        elif earnings_growth > 0.15:
            score += 15
        elif earnings_growth > 0:
            score += 10
        
        # Margin expansion (20 points max)
        operating_margin = fundamental.get('operating_margin', 0)
        if operating_margin > 0.20:  # Profitable and expanding
            score += 20
        elif operating_margin > 0.10:
            score += 15
        elif operating_margin > 0:
            score += 10
        
        return min(100, max(0, score))
    
    def _calculate_team_score(self, fundamental: Dict, additional: Dict) -> float:
        """
        Calculate team & execution score (0-100)
        Measures management quality and capital allocation
        
        Args:
            fundamental: Fundamental data
            additional: Additional data (insider trading, etc.)
        
        Returns:
            Team score
        """
        score = 50.0  # Start neutral
        
        # High ROIC indicates good capital allocation
        roic = fundamental.get('roic', 0)
        if roic > 0.20:  # 20%+ ROIC
            score += 20
        elif roic > 0.15:  # 15%+ ROIC
            score += 15
        elif roic > 0.10:  # 10%+ ROIC
            score += 10
        
        # High ROE
        roe = fundamental.get('roe', 0)
        if roe > 0.25:  # 25%+ ROE
            score += 15
        elif roe > 0.15:  # 15%+ ROE
            score += 10
        elif roe > 0.10:  # 10%+ ROE
            score += 5
        
        # Consistent profitability
        profit_margin = fundamental.get('profit_margin', 0)
        if profit_margin > 0.15:  # 15%+ net margin
            score += 10
        elif profit_margin > 0.05:  # 5%+ net margin
            score += 5
        
        # Insider buying (if data available)
        insider_activity = additional.get('insider_buying', None)
        if insider_activity is not None:
            if insider_activity > 0:
                score += 10
            elif insider_activity < 0:
                score -= 10
        
        return min(100, max(0, score))
    
    def _calculate_risk_reward_score(self, fundamental: Dict, technical: Dict) -> float:
        """
        Calculate risk/reward score (0-100)
        Measures asymmetric upside potential vs downside risk
        
        Args:
            fundamental: Fundamental data
            technical: Technical data
        
        Returns:
            Risk/reward score
        """
        score = 50.0  # Start neutral
        
        # Valuation - lower is better for growth stocks
        peg_ratio = fundamental.get('peg_ratio', 0)
        if 0 < peg_ratio < 1.0:  # PEG < 1 is attractive
            score += 20
        elif peg_ratio < 1.5:
            score += 15
        elif peg_ratio < 2.0:
            score += 10
        elif peg_ratio > 3.0:  # Overvalued
            score -= 10
        
        # Balance sheet strength
        current_ratio = fundamental.get('current_ratio', 0)
        if current_ratio > 2.0:
            score += 10
        elif current_ratio > 1.5:
            score += 5
        elif current_ratio < 1.0:
            score -= 10
        
        # Debt levels
        debt_to_equity = fundamental.get('debt_to_equity', 0)
        if debt_to_equity < 0.3:
            score += 10
        elif debt_to_equity < 0.5:
            score += 5
        elif debt_to_equity > 2.0:
            score -= 15
        
        # Technical setup - looking for consolidation/breakout
        signals = technical.get('signals', {})
        
        # Trend
        if signals.get('trend') == 'strong_uptrend':
            score += 10
        elif signals.get('trend') == 'uptrend':
            score += 5
        elif signals.get('trend') == 'downtrend':
            score -= 10
        
        # RSI oversold is good for entry
        if signals.get('rsi') == 'oversold':
            score += 10
        elif signals.get('rsi') == 'overbought':
            score -= 5
        
        return min(100, max(0, score))
    
    def _get_grade(self, score: float) -> str:
        """
        Convert score to letter grade
        
        Args:
            score: Composite score (0-100)
        
        Returns:
            Letter grade
        """
        if score >= 90:
            return 'A+'
        elif score >= 85:
            return 'A'
        elif score >= 80:
            return 'A-'
        elif score >= 75:
            return 'B+'
        elif score >= 70:
            return 'B'
        elif score >= 65:
            return 'B-'
        elif score >= 60:
            return 'C+'
        elif score >= 55:
            return 'C'
        elif score >= 50:
            return 'C-'
        elif score >= 45:
            return 'D+'
        elif score >= 40:
            return 'D'
        else:
            return 'F'
    
    def get_conviction_level(self, score: float) -> str:
        """
        Get conviction level based on score
        
        Args:
            score: Composite score
        
        Returns:
            Conviction level string
        """
        if score >= 85:
            return "Very High"
        elif score >= 75:
            return "High"
        elif score >= 65:
            return "Medium"
        elif score >= 55:
            return "Low"
        else:
            return "Very Low"
    
    def get_position_size_recommendation(self, score: float, risk_tolerance: str = "moderate") -> float:
        """
        Recommend position size based on score and risk tolerance
        
        Args:
            score: Composite score
            risk_tolerance: Risk tolerance level (conservative, moderate, aggressive)
        
        Returns:
            Recommended position size as percentage (0-1)
        """
        # Base position size by score
        if score >= 85:
            base_size = 0.15  # 15%
        elif score >= 75:
            base_size = 0.12  # 12%
        elif score >= 65:
            base_size = 0.08  # 8%
        elif score >= 55:
            base_size = 0.05  # 5%
        else:
            base_size = 0.02  # 2%
        
        # Adjust by risk tolerance
        if risk_tolerance == "conservative":
            base_size *= 0.7
        elif risk_tolerance == "aggressive":
            base_size *= 1.3
        
        # Cap at 15%
        return min(0.15, base_size)
