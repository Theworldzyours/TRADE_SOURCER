"""
Weekend report generator
"""
import pandas as pd
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional
from jinja2 import Template
from ..utils.logger import get_logger

logger = get_logger()


class ReportGenerator:
    """Generate weekend trading reports"""
    
    def __init__(self, config: Dict = None, output_dir: str = "reports"):
        """
        Initialize report generator
        
        Args:
            config: Configuration dictionary
            output_dir: Output directory for reports
        """
        self.config = config or {}
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)
    
    def generate_weekend_report(
        self,
        top_stocks: pd.DataFrame,
        sector_allocation: pd.DataFrame,
        diversification: Dict,
        analysis_date: Optional[datetime] = None
    ) -> str:
        """
        Generate comprehensive weekend trading report
        
        Args:
            top_stocks: DataFrame with top ranked stocks
            sector_allocation: DataFrame with sector allocation
            diversification: Diversification analysis
            analysis_date: Date of analysis
        
        Returns:
            Path to generated report
        """
        if analysis_date is None:
            analysis_date = datetime.now()
        
        # Generate different report formats
        html_path = self._generate_html_report(
            top_stocks, sector_allocation, diversification, analysis_date
        )
        
        csv_path = self._generate_csv_report(top_stocks, analysis_date)
        
        # Generate summary
        summary = self._generate_summary(top_stocks, sector_allocation)
        
        logger.info(f"Generated weekend report: {html_path}")
        logger.info(f"Summary: {summary}")
        
        return str(html_path)
    
    def _generate_html_report(
        self,
        top_stocks: pd.DataFrame,
        sector_allocation: pd.DataFrame,
        diversification: Dict,
        analysis_date: datetime
    ) -> Path:
        """Generate HTML report"""
        
        html_template = """
<!DOCTYPE html>
<html>
<head>
    <title>Trade Sourcer - Weekend Report {{ date }}</title>
    <style>
        body {
            font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
            max-width: 1200px;
            margin: 0 auto;
            padding: 20px;
            background-color: #f5f5f5;
        }
        h1 {
            color: #2c3e50;
            border-bottom: 3px solid #3498db;
            padding-bottom: 10px;
        }
        h2 {
            color: #34495e;
            margin-top: 30px;
            border-bottom: 2px solid #95a5a6;
            padding-bottom: 5px;
        }
        h3 {
            color: #7f8c8d;
        }
        .report-header {
            background-color: #3498db;
            color: white;
            padding: 20px;
            border-radius: 5px;
            margin-bottom: 20px;
        }
        .summary {
            background-color: #ecf0f1;
            padding: 15px;
            border-radius: 5px;
            margin-bottom: 20px;
        }
        .stock-card {
            background-color: white;
            padding: 20px;
            margin-bottom: 15px;
            border-radius: 5px;
            box-shadow: 0 2px 4px rgba(0,0,0,0.1);
        }
        .stock-header {
            display: flex;
            justify-content: space-between;
            align-items: center;
            margin-bottom: 10px;
        }
        .ticker {
            font-size: 24px;
            font-weight: bold;
            color: #2c3e50;
        }
        .score {
            font-size: 28px;
            font-weight: bold;
            padding: 10px 20px;
            border-radius: 5px;
        }
        .score-a { background-color: #2ecc71; color: white; }
        .score-b { background-color: #3498db; color: white; }
        .score-c { background-color: #f39c12; color: white; }
        .score-d { background-color: #e74c3c; color: white; }
        .metrics {
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
            gap: 10px;
            margin-top: 15px;
        }
        .metric {
            padding: 10px;
            background-color: #f8f9fa;
            border-radius: 3px;
        }
        .metric-label {
            font-size: 12px;
            color: #7f8c8d;
            text-transform: uppercase;
        }
        .metric-value {
            font-size: 18px;
            font-weight: bold;
            color: #2c3e50;
        }
        .positive { color: #27ae60; }
        .negative { color: #e74c3c; }
        .sector-table {
            width: 100%;
            border-collapse: collapse;
            background-color: white;
            margin-top: 10px;
        }
        .sector-table th, .sector-table td {
            padding: 12px;
            text-align: left;
            border-bottom: 1px solid #ddd;
        }
        .sector-table th {
            background-color: #34495e;
            color: white;
        }
        .warning {
            background-color: #fff3cd;
            border-left: 4px solid #ffc107;
            padding: 10px;
            margin: 10px 0;
        }
        .footer {
            margin-top: 40px;
            padding-top: 20px;
            border-top: 2px solid #bdc3c7;
            text-align: center;
            color: #7f8c8d;
        }
    </style>
</head>
<body>
    <div class="report-header">
        <h1>📊 Trade Sourcer - Weekend Report</h1>
        <p><strong>Analysis Date:</strong> {{ date }}</p>
        <p><strong>Total Opportunities:</strong> {{ total_stocks }}</p>
    </div>
    
    <div class="summary">
        <h2>Executive Summary</h2>
        <p>This weekend's analysis identified <strong>{{ total_stocks }}</strong> high-quality trading opportunities 
        using a Venture Capital approach to public markets. The top 5 ideas are highlighted below.</p>
    </div>
    
    {% if warnings %}
    <div class="warning">
        <h3>⚠️ Diversification Warnings</h3>
        <ul>
        {% for warning in warnings %}
            <li>{{ warning }}</li>
        {% endfor %}
        </ul>
    </div>
    {% endif %}
    
    <h2>🌟 Top 5 Ideas</h2>
    {% for stock in top_5 %}
    <div class="stock-card">
        <div class="stock-header">
            <div>
                <div class="ticker">{{ stock.ticker }}</div>
                <div style="color: #7f8c8d;">{{ stock.company_name }}</div>
            </div>
            <div class="score score-{{ stock.grade_class }}">
                {{ stock.composite_score }}
                <div style="font-size: 14px;">{{ stock.grade }}</div>
            </div>
        </div>
        
        <div style="margin: 10px 0;">
            <strong>Sector:</strong> {{ stock.sector }} | 
            <strong>Price:</strong> ${{ "%.2f"|format(stock.current_price) }} |
            <strong>Market Cap:</strong> {{ stock.market_cap_display }}
        </div>
        
        <div class="metrics">
            <div class="metric">
                <div class="metric-label">Innovation Score</div>
                <div class="metric-value">{{ stock.innovation_score }}</div>
            </div>
            <div class="metric">
                <div class="metric-label">Growth Score</div>
                <div class="metric-value">{{ stock.growth_score }}</div>
            </div>
            <div class="metric">
                <div class="metric-label">Technical Score</div>
                <div class="metric-value">{{ stock.technical_score }}</div>
            </div>
            <div class="metric">
                <div class="metric-label">Revenue Growth</div>
                <div class="metric-value positive">{{ "%.1f"|format(stock.revenue_growth * 100) }}%</div>
            </div>
            <div class="metric">
                <div class="metric-label">Gross Margin</div>
                <div class="metric-value">{{ "%.1f"|format(stock.gross_margin * 100) }}%</div>
            </div>
            <div class="metric">
                <div class="metric-label">Conviction</div>
                <div class="metric-value">{{ stock.conviction }}</div>
            </div>
        </div>
        
        <div style="margin-top: 15px; padding: 10px; background-color: #e8f5e9; border-radius: 3px;">
            <strong>💡 Position Sizing:</strong> {{ "%.1f"|format(stock.position_size * 100) }}% of portfolio
        </div>
    </div>
    {% endfor %}
    
    <h2>📊 Sector Allocation</h2>
    <table class="sector-table">
        <thead>
            <tr>
                <th>Sector</th>
                <th>Count</th>
                <th>Percentage</th>
            </tr>
        </thead>
        <tbody>
        {% for sector in sectors %}
            <tr>
                <td>{{ sector.sector }}</td>
                <td>{{ sector.count }}</td>
                <td>{{ "%.1f"|format(sector.percentage) }}%</td>
            </tr>
        {% endfor %}
        </tbody>
    </table>
    
    <h2>📋 Complete List (Top {{ total_stocks }})</h2>
    <table class="sector-table">
        <thead>
            <tr>
                <th>Rank</th>
                <th>Ticker</th>
                <th>Company</th>
                <th>Sector</th>
                <th>Score</th>
                <th>Grade</th>
                <th>Price</th>
            </tr>
        </thead>
        <tbody>
        {% for stock in all_stocks %}
            <tr>
                <td>{{ stock.rank }}</td>
                <td><strong>{{ stock.ticker }}</strong></td>
                <td>{{ stock.company_name }}</td>
                <td>{{ stock.sector }}</td>
                <td>{{ stock.composite_score }}</td>
                <td>{{ stock.grade }}</td>
                <td>${{ "%.2f"|format(stock.current_price) }}</td>
            </tr>
        {% endfor %}
        </tbody>
    </table>
    
    <div class="footer">
        <p>Generated by Trade Sourcer - Venture Capital Approach to Public Markets</p>
        <p>⚠️ This report is for informational purposes only. Not financial advice.</p>
    </div>
</body>
</html>
        """
        
        # Prepare data for template
        top_5 = self._prepare_stock_data(top_stocks.head(5))
        all_stocks = self._prepare_stock_data(top_stocks)
        
        template = Template(html_template)
        html_content = template.render(
            date=analysis_date.strftime("%Y-%m-%d %H:%M"),
            total_stocks=len(top_stocks),
            top_5=top_5,
            all_stocks=all_stocks,
            sectors=sector_allocation.to_dict('records') if not sector_allocation.empty else [],
            warnings=diversification.get('warnings', [])
        )
        
        # Save HTML file
        filename = f"weekend_report_{analysis_date.strftime('%Y%m%d')}.html"
        filepath = self.output_dir / filename
        
        with open(filepath, 'w') as f:
            f.write(html_content)
        
        return filepath
    
    def _prepare_stock_data(self, df: pd.DataFrame) -> List[Dict]:
        """Prepare stock data for template"""
        stocks = []
        
        for _, row in df.iterrows():
            # Format market cap
            market_cap = row.get('market_cap', 0)
            if market_cap >= 1_000_000_000:
                market_cap_display = f"${market_cap/1_000_000_000:.2f}B"
            elif market_cap >= 1_000_000:
                market_cap_display = f"${market_cap/1_000_000:.2f}M"
            else:
                market_cap_display = f"${market_cap:,.0f}"
            
            # Determine grade class for styling
            grade = row.get('grade', 'C')
            if grade.startswith('A'):
                grade_class = 'a'
            elif grade.startswith('B'):
                grade_class = 'b'
            elif grade.startswith('C'):
                grade_class = 'c'
            else:
                grade_class = 'd'
            
            stock_data = {
                'rank': row.get('rank', 0),
                'ticker': row.get('ticker', 'N/A'),
                'company_name': row.get('company_name', 'N/A'),
                'sector': row.get('sector', 'N/A'),
                'current_price': row.get('current_price', 0),
                'market_cap': market_cap,
                'market_cap_display': market_cap_display,
                'composite_score': row.get('composite_score', 0),
                'innovation_score': row.get('innovation_score', 0),
                'growth_score': row.get('growth_score', 0),
                'technical_score': row.get('technical_score', 0),
                'grade': grade,
                'grade_class': grade_class,
                'conviction': row.get('conviction', 'N/A'),
                'position_size': row.get('position_size', 0),
                'revenue_growth': row.get('revenue_growth', 0),
                'gross_margin': row.get('gross_margin', 0),
            }
            stocks.append(stock_data)
        
        return stocks
    
    def _generate_csv_report(self, top_stocks: pd.DataFrame, analysis_date: datetime) -> Path:
        """Generate CSV export"""
        filename = f"stocks_data_{analysis_date.strftime('%Y%m%d')}.csv"
        filepath = self.output_dir / filename
        
        top_stocks.to_csv(filepath, index=False)
        logger.info(f"Generated CSV report: {filepath}")
        
        return filepath
    
    def _generate_summary(self, top_stocks: pd.DataFrame, sector_allocation: pd.DataFrame) -> str:
        """Generate text summary"""
        if top_stocks.empty:
            return "No stocks found matching criteria."
        
        top_3 = top_stocks.head(3)
        
        summary = f"""
Trade Sourcer Weekend Summary
==============================
Total Opportunities: {len(top_stocks)}
Average Score: {top_stocks['composite_score'].mean():.2f}

Top 3 Ideas:
"""
        
        for _, stock in top_3.iterrows():
            summary += f"  {stock['rank']}. {stock['ticker']} - {stock['company_name']} "
            summary += f"(Score: {stock['composite_score']}, Grade: {stock['grade']})\n"
        
        if not sector_allocation.empty:
            summary += f"\nTop Sectors:\n"
            for _, sector in sector_allocation.head(3).iterrows():
                summary += f"  - {sector['sector']}: {sector['percentage']:.1f}%\n"
        
        return summary
