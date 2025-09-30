"""
Quick Start Example - Analyze a few stocks
"""
import sys
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent))

from main import TradeSourcer


def main():
    """Quick start example with a small set of stocks"""
    print("\n" + "=" * 60)
    print("TRADE SOURCER - QUICK START EXAMPLE")
    print("=" * 60)
    print("\nThis example analyzes a small set of popular stocks")
    print("to demonstrate the application functionality.\n")
    
    # Sample stocks to analyze
    sample_stocks = [
        'AAPL',   # Apple
        'MSFT',   # Microsoft
        'GOOGL',  # Google
        'TSLA',   # Tesla
        'NVDA',   # NVIDIA
    ]
    
    print(f"Analyzing {len(sample_stocks)} stocks: {', '.join(sample_stocks)}\n")
    print("Please wait, this may take a minute...\n")
    
    try:
        # Initialize application
        app = TradeSourcer()
        
        # Run analysis on sample stocks
        results = app.run_analysis(tickers=sample_stocks)
        
        # Print summary
        app.print_summary(results)
        
        print("✅ Quick start complete!")
        print("📊 Check the reports directory for the HTML report.\n")
        
    except Exception as e:
        print(f"\n❌ Error: {e}\n")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()
