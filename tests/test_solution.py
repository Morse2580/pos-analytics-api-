"""
Quick test script to validate the solution works end-to-end.

Run this before starting the API to ensure all modules work correctly.
"""

import pandas as pd
import sys
import os

# Add src to path (relative to this file's location)
current_dir = os.path.dirname(os.path.abspath(__file__))
project_root = os.path.dirname(current_dir)
src_path = os.path.join(project_root, 'src')
sys.path.insert(0, src_path)

from modules.data_quality import DataQualityChecker
from modules.promotions import PromotionAnalyzer
from modules.pricing_index import PricingIndexAnalyzer


def test_data_loading():
    """Test data loading."""
    print("\n" + "="*80)
    print("TEST 1: Data Loading")
    print("="*80)
    try:
        # Load from project root
        data_path = os.path.join(project_root, 'Test_Data.xlsx')
        df = pd.read_excel(data_path)
        print(f"SUCCESS: Loaded {len(df)} records")
        print(f"Date range: {df['Date Of Sale'].min()} to {df['Date Of Sale'].max()}")
        print(f"Stores: {df['Store Name'].nunique()}")
        print(f"Suppliers: {df['Supplier'].nunique()}")
        print(f"SKUs: {df['Item_Code'].nunique()}")
        return df
    except Exception as e:
        print(f"FAILED: {e}")
        return None


def test_data_quality(df):
    """Test data quality module."""
    print("\n" + "="*80)
    print("TEST 2: Data Quality Module")
    print("="*80)
    try:
        checker = DataQualityChecker(df)

        # Test health scores
        store_health = checker.calculate_store_health_score()
        print(f"SUCCESS: Calculated health scores for {len(store_health)} stores")
        print(f"Top 3 stores:")
        print(store_health.head(3)[['store', 'health_score', 'category']])

        # Test summary report
        report = checker.generate_summary_report()
        print(f"\nKey issues found: {len(report['key_issues'])}")
        for issue in report['key_issues'][:3]:
            print(f"  - {issue}")

        return True
    except Exception as e:
        print(f"FAILED: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_promotions(df):
    """Test promotions module."""
    print("\n" + "="*80)
    print("TEST 3: Promotions Module")
    print("="*80)
    try:
        analyzer = PromotionAnalyzer(df)

        # Test Bidco analysis
        bidco_kpis = analyzer.calculate_kpis(supplier_filter='BIDCO')
        print(f"SUCCESS: Analyzed promotions for Bidco")
        print(f"Total SKUs: {bidco_kpis['summary']['total_skus_analyzed']}")
        print(f"SKUs with promos: {bidco_kpis['summary']['skus_with_promos']}")

        if bidco_kpis['summary']['avg_promo_uplift'] > 0:
            print(f"Avg promo uplift: {bidco_kpis['summary']['avg_promo_uplift']:.1f}%")

        # Test insights
        insights = analyzer.generate_commercial_insights(supplier_filter='BIDCO')
        print(f"\nGenerated {len(insights)} commercial insights")
        if insights:
            print(f"Sample insight: {insights[0]}")

        return True
    except Exception as e:
        print(f"FAILED: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_pricing(df):
    """Test pricing index module."""
    print("\n" + "="*80)
    print("TEST 4: Pricing Index Module")
    print("="*80)
    try:
        analyzer = PricingIndexAnalyzer(df)

        # Test overall positioning
        overall = analyzer.calculate_overall_positioning('BIDCO AFRICA LIMITED')
        print(f"SUCCESS: Calculated pricing index for Bidco")
        print(f"Overall price index: {overall['overall_price_index']:.1f}")
        print(f"Positioning: {overall['overall_positioning']}")

        # Test insights
        insights = analyzer.generate_bidco_pricing_insights()
        print(f"\nGenerated {len(insights)} pricing insights")
        if insights:
            print(f"Sample insight: {insights[0]}")

        return True
    except Exception as e:
        print(f"FAILED: {e}")
        import traceback
        traceback.print_exc()
        return False


def main():
    """Run all tests."""
    print("\n" + "#"*80)
    print("# Duck Retail Analytics - Solution Validation")
    print("#"*80)

    results = []

    # Test 1: Data loading
    df = test_data_loading()
    results.append(('Data Loading', df is not None))

    if df is None:
        print("\nCannot continue - data loading failed")
        return

    # Test 2: Data quality
    results.append(('Data Quality Module', test_data_quality(df)))

    # Test 3: Promotions
    results.append(('Promotions Module', test_promotions(df)))

    # Test 4: Pricing
    results.append(('Pricing Index Module', test_pricing(df)))

    # Summary
    print("\n" + "="*80)
    print("TEST SUMMARY")
    print("="*80)
    for test_name, passed in results:
        status = "PASS" if passed else "FAIL"
        print(f"{test_name}: {status}")

    all_passed = all(result[1] for result in results)

    if all_passed:
        print("\n" + "="*80)
        print("ALL TESTS PASSED - Solution is ready!")
        print("="*80)
        print("\nNext steps:")
        print("1. Start API: python src/api/main.py")
        print("2. Or use Docker: docker-compose up -d")
        print("3. Access docs: http://localhost:8000/docs")
    else:
        print("\n" + "="*80)
        print("SOME TESTS FAILED - Check errors above")
        print("="*80)


if __name__ == "__main__":
    main()
