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
<html lang="en">
<head>
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Trade Sourcer - Weekend Report {{ date }}</title>
    <style>
        .skip-link {
            position: absolute;
            top: -40px;
            left: 0;
            padding: 8px;
            background: #000;
            color: #fff;
            z-index: 100;
        }
        .skip-link:focus {
            top: 0;
        }
        *:focus {
            outline: 2px solid #3498db;
            outline-offset: 2px;
        }
        body {
            font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
            max-width: 1200px;
            margin: 0 auto;
            padding: 20px;
            background-color: #f5f5f5;
            line-height: 1.5;
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
            color: #555555;
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
            color: #555555;
        }
    </style>
</head>
<body>
    <a href="#main-content" class="skip-link">Skip to main content</a>
    <div class="report-header">
        <h1>📊 Trade Sourcer - Weekend Report</h1>
        <h2 style="color: #ecf0f1; font-weight: normal;">Next Week Trading Opportunities</h2>
        <p><strong>Analysis Date:</strong> {{ date }}</p>
        <p><strong>Total Opportunities:</strong> {{ total_stocks }}</p>
    </div>

    <main id="main-content" role="main">
    <section aria-label="Executive Summary">
    <div class="summary">
        <h2>Executive Summary</h2>
        <p>This weekend's analysis identified <strong>{{ total_stocks }}</strong> high-quality trading opportunities
        for the upcoming week using a Venture Capital approach to public markets. Each stock includes volatility analysis
        and predicted price ranges for next week's trading.</p>
    </div>
    </section>

    {% if warnings %}
    <section aria-label="Diversification Warnings">
    <div class="warning">
        <h3>⚠️ Diversification Warnings</h3>
        <ul>
        {% for warning in warnings %}
            <li>{{ warning }}</li>
        {% endfor %}
        </ul>
    </div>
    </section>
    {% endif %}

    <section aria-label="Top 5 stock ideas for next week">
    <h2>🌟 Top 5 Ideas for Next Week</h2>
    {% if top_5 %}
    {% for stock in top_5 %}
    <article class="stock-card">
        <header class="stock-header">
            <div>
                <h3 class="ticker">{{ stock.ticker }}</h3>
                <div style="color: #555555;">{{ stock.company_name }}</div>
            </div>
            <div class="score score-{{ stock.grade_class }}">
                {{ stock.composite_score }}
                <div style="font-size: 14px;">{{ stock.grade }}</div>
            </div>
        </header>

        <div style="margin: 10px 0;">
            <strong>Sector:</strong> {{ stock.sector }} |
            <strong>Price:</strong> ${{ "%.2f"|format(stock.current_price) }} |
            <strong>Market Cap:</strong> {{ stock.market_cap_display }}
        </div>

        {% if stock.next_week_lower %}
        <div style="margin: 15px 0; padding: 12px; background-color: #e3f2fd; border-radius: 3px; border-left: 4px solid #2196f3;">
            <strong>📈 Next Week Outlook:</strong><br/>
            <div style="margin-top: 8px;">
                <strong>Expected Range:</strong> ${{ "%.2f"|format(stock.next_week_lower) }} - ${{ "%.2f"|format(stock.next_week_upper) }}
                ({{ "%.1f"|format(stock.next_week_lower_pct) }}% to {{ "%.1f"|format(stock.next_week_upper_pct) }}%)<br/>
                <strong>Volatility:</strong> {{ "%.1f"|format(stock.weekly_volatility) }}% weekly |
                {{ stock.volatility_regime|replace("_", " ")|title }}<br/>
                <div style="margin-top: 5px; font-size: 12px; color: #555;">
                    {{ stock.volatility_description }}
                </div>
            </div>
        </div>
        {% endif %}

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
    </article>
    {% endfor %}
    {% else %}
    <div class="stock-card">
        <p><strong>No stocks matched your criteria.</strong></p>
        <p>Current filters: {{ filter_summary }}</p>
        <p style="margin-top: 10px; color: #555;">Try loosening your filter thresholds in <code>config/config.yaml</code></p>
    </div>
    {% endif %}
    </section>

    <section aria-label="Sector Allocation">
    <h2>📊 Sector Allocation</h2>
    <div style="overflow-x: auto;">
    <table class="sector-table">
        <caption>Sector allocation and stock distribution</caption>
        <thead>
            <tr>
                <th scope="col">Sector</th>
                <th scope="col">Count</th>
                <th scope="col">Percentage</th>
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
    </div>
    </section>

    <section aria-label="Complete stock list">
    <h2>📋 Complete List (Top {{ total_stocks }})</h2>
    {% if all_stocks %}
    <div style="overflow-x: auto;">
    <table class="sector-table">
        <caption>Complete ranked list of top trading opportunities</caption>
        <thead>
            <tr>
                <th scope="col">Rank</th>
                <th scope="col">Ticker</th>
                <th scope="col">Company</th>
                <th scope="col">Sector</th>
                <th scope="col">Score</th>
                <th scope="col">Grade</th>
                <th scope="col">Price</th>
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
    </div>
    {% else %}
    <div class="stock-card">
        <p>No stocks to display. All candidates were filtered out by the current criteria.</p>
    </div>
    {% endif %}
    </section>
    </main>

    <footer class="footer">
        <p>Generated by Trade Sourcer - Venture Capital Approach to Public Markets</p>
        <p>⚠️ This report is for informational purposes only. Not financial advice.</p>
    </footer>
</body>
</html>
        """
        
        # Prepare data for template
        top_5 = self._prepare_stock_data(top_stocks.head(5))
        all_stocks = self._prepare_stock_data(top_stocks)

        # Build filter summary for empty-state messaging
        filter_summary = self._build_filter_summary()

        template = Template(html_template)
        html_content = template.render(
            date=analysis_date.strftime("%Y-%m-%d %H:%M"),
            total_stocks=len(top_stocks),
            top_5=top_5,
            all_stocks=all_stocks,
            sectors=sector_allocation.to_dict('records') if not sector_allocation.empty else [],
            warnings=diversification.get('warnings', []),
            filter_summary=filter_summary
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
                # Volatility and next week predictions
                'next_week_lower': row.get('next_week_lower', None),
                'next_week_upper': row.get('next_week_upper', None),
                'next_week_lower_pct': row.get('next_week_lower_pct', 0),
                'next_week_upper_pct': row.get('next_week_upper_pct', 0),
                'weekly_volatility': row.get('weekly_volatility', 0),
                'volatility_regime': row.get('volatility_regime', 'N/A'),
                'volatility_description': row.get('volatility_description', ''),
                'historical_volatility_20d': row.get('historical_volatility_20d', 0),
            }
            stocks.append(stock_data)
        
        return stocks
    
    def _build_filter_summary(self) -> str:
        """Build a human-readable summary of active filter thresholds"""
        filter_labels = {
            'min_market_cap': 'min_market_cap',
            'min_avg_volume': 'min_avg_volume',
            'min_revenue_growth': 'min_revenue_growth',
            'min_gross_margin': 'min_gross_margin',
            'min_altman_z': 'min_altman_z',
            'max_debt_to_equity': 'max_debt_to_equity',
            'min_current_ratio': 'min_current_ratio',
        }
        parts = []
        for key, label in filter_labels.items():
            val = self.config.get(key)
            if val is not None:
                # Format large numbers
                if isinstance(val, (int, float)) and val >= 1_000_000:
                    formatted = f"{val/1_000_000:.0f}M"
                elif isinstance(val, float) and val < 1:
                    formatted = f"{val*100:.0f}%"
                else:
                    formatted = str(val)
                parts.append(f"{label}={formatted}")
        return ", ".join(parts) if parts else "default filters (see config/config.yaml)"

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
