"""
Duck Retail Analytics API

Simple FastAPI exposing data quality, promotions, and pricing KPIs.
"""

from fastapi import FastAPI, Query
from fastapi.responses import JSONResponse
import pandas as pd
import sys
import os
from typing import Optional

# Add parent directory to path for imports
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from modules.data_quality import DataQualityChecker
from modules.promotions import PromotionAnalyzer
from modules.pricing_index import PricingIndexAnalyzer

# Initialize FastAPI app
app = FastAPI(
    title="Duck Retail Analytics API",
    description="Retail data quality, promotions analysis, and competitive pricing intelligence",
    version="1.0.0"
)

# Global data storage
DATA = None
DATA_FILE_PATH = "Test_Data.xlsx"


def load_data():
    """Load sales data from Excel file."""
    global DATA
    if DATA is None:
        try:
            DATA = pd.read_excel(DATA_FILE_PATH)
            print(f"Loaded {len(DATA)} records from {DATA_FILE_PATH}")
        except Exception as e:
            print(f"Error loading data: {e}")
            raise
    return DATA


@app.on_event("startup")
async def startup_event():
    """Load data on application startup."""
    load_data()
    print("API ready at http://localhost:8000")
    print("Docs available at http://localhost:8000/docs")


@app.get("/")
def read_root():
    """Root endpoint with API information."""
    return {
        "message": "Duck Retail Analytics API",
        "version": "1.0.0",
        "endpoints": {
            "health": "/health - API health check",
            "data_quality": "/data_quality - Comprehensive data quality report",
            "promo_summary": "/promo_summary?supplier=BIDCO - Promotion analysis",
            "price_index": "/price_index?supplier=BIDCO AFRICA LIMITED - Pricing intelligence"
        },
        "docs": "/docs"
    }


@app.get("/health")
def health_check():
    """Health check endpoint."""
    return {
        "status": "healthy",
        "data_loaded": DATA is not None,
        "records_count": len(DATA) if DATA is not None else 0
    }


@app.get("/data_quality")
def get_data_quality(
    min_score: Optional[float] = Query(None, description="Filter by minimum health score"),
    category: Optional[str] = Query(None, description="Filter by category (Excellent/Good/Fair/Poor)")
):
    """
    Comprehensive data quality health check.

    Returns:
    - Dataset overview (stores, suppliers, date range)
    - Missing values and duplicates summary
    - Outliers detected
    - Store health scores (with optional filters)
    - Supplier health scores (with optional filters)
    - Key data quality issues identified

    Query Parameters:
    - min_score: Filter results with health score >= this value
    - category: Filter by health category (Excellent/Good/Fair/Poor)
    """
    df = load_data()
    checker = DataQualityChecker(df)

    # Generate comprehensive report
    report = checker.generate_summary_report()

    # Get detailed scores
    store_health = checker.calculate_store_health_score()
    supplier_health = checker.calculate_supplier_health_score()

    # Apply filters if provided
    if min_score is not None:
        store_health = store_health[store_health['health_score'] >= min_score]
        supplier_health = supplier_health[supplier_health['health_score'] >= min_score]

    if category is not None:
        store_health = store_health[store_health['category'] == category]
        supplier_health = supplier_health[supplier_health['category'] == category]

    # Combine into single response
    return JSONResponse(content={
        "overview": report['dataset_overview'],
        "data_issues": {
            "missing_values": report['missing_values'],
            "duplicates_count": report['duplicates_count'],
            "outliers": report['outliers_summary'],
            "key_issues": report['key_issues']
        },
        "store_health": {
            "scores": store_health.to_dict('records'),
            "summary": {
                "total_stores": len(store_health),
                "avg_score": float(store_health['health_score'].mean()),
                "excellent_count": len(store_health[store_health['category'] == 'Excellent']),
                "poor_count": len(store_health[store_health['category'] == 'Poor'])
            }
        },
        "supplier_health": {
            "scores": supplier_health.to_dict('records'),
            "summary": {
                "total_suppliers": len(supplier_health),
                "avg_score": float(supplier_health['health_score'].mean()),
                "excellent_count": len(supplier_health[supplier_health['category'] == 'Excellent']),
                "poor_count": len(supplier_health[supplier_health['category'] == 'Poor'])
            }
        }
    })


@app.get("/promo_summary")
def get_promo_summary(
    supplier: Optional[str] = Query('BIDCO', description="Supplier to analyze (default: BIDCO)")
):
    """
    Comprehensive promotion analysis.

    Detects promotional periods (>=10% discount from RRP for >=2 days) and calculates:
    - Promo uplift % (quantity vs baseline)
    - Promo coverage % (store penetration)
    - Promo price impact (discount depth)
    - Baseline vs promo average prices
    - Top performing SKUs
    - Commercial insights for brand managers

    Query Parameters:
    - supplier: Supplier name to filter (case-insensitive substring match)
              Examples: 'BIDCO', 'UNILEVER', 'COCA-COLA'
    """
    df = load_data()
    analyzer = PromotionAnalyzer(df)

    # Get KPIs for specified supplier
    kpis = analyzer.calculate_kpis(supplier_filter=supplier)

    # Get commercial insights
    insights = analyzer.generate_commercial_insights(supplier_filter=supplier)

    # For Bidco, get additional detailed breakdown
    additional_data = {}
    if 'BIDCO' in supplier.upper():
        bidco_insights = analyzer.get_bidco_insights()
        additional_data = {
            "top_promo_stores": bidco_insights.get('top_promo_stores', []),
            "category_breakdown": bidco_insights.get('category_breakdown', [])
        }

    return JSONResponse(content={
        "supplier": supplier,
        "summary": kpis['summary'],
        "top_performing_skus": kpis['top_performing_skus'],
        "commercial_insights": insights,
        "additional_analysis": additional_data,
        "methodology": {
            "promo_detection": "SKU on promo when unit price is >=10% below RRP for >=2 days",
            "uplift_calculation": "(Promo quantity - Baseline quantity) / Baseline quantity * 100",
            "coverage_calculation": "Stores running promo / Total stores * 100"
        }
    })


@app.get("/price_index")
def get_price_index(
    supplier: Optional[str] = Query('BIDCO AFRICA LIMITED', description="Supplier to analyze"),
    view: Optional[str] = Query('summary', description="View type: 'summary' or 'detailed'")
):
    """
    Competitive pricing intelligence and price index.

    Compares supplier pricing against competitors within same Sub-Department and Section.
    Price Index = (Supplier Avg Price / Market Avg Price) * 100
    - 100 = At market
    - >110 = Premium positioning
    - <90 = Discount positioning

    Returns:
    - Overall price index and positioning
    - Store-level price comparison (if view=detailed)
    - Category-level breakdown
    - Premium vs discount categories
    - Strategic pricing insights

    Query Parameters:
    - supplier: Supplier name (default: BIDCO AFRICA LIMITED)
    - view: 'summary' for overview, 'detailed' for store-level data
    """
    df = load_data()
    analyzer = PricingIndexAnalyzer(df)

    # Get overall positioning
    overall = analyzer.calculate_overall_positioning(target_supplier=supplier)

    # Get strategic insights
    insights = analyzer.generate_bidco_pricing_insights() if 'BIDCO' in supplier.upper() else []

    response = {
        "supplier": supplier,
        "overall_metrics": {
            "price_index": overall['overall_price_index'],
            "positioning": overall['overall_positioning'],
            "positioning_distribution": overall['positioning_distribution']
        },
        "top_categories": overall['top_categories'],
        "category_insights": {
            "premium_categories": overall.get('premium_categories', {}),
            "discount_categories": overall.get('discount_categories', {})
        },
        "strategic_insights": insights,
        "methodology": {
            "price_index_calculation": "Price Index = (Supplier Avg Unit Price / Market Avg Unit Price) * 100",
            "market_definition": "All competitors in same Sub-Department + Section + Store",
            "unit_price": "Total Sales / Quantity (realized transaction price)"
        }
    }

    # Add detailed store-level data if requested
    if view == 'detailed':
        store_index = analyzer.calculate_store_level_index(target_supplier=supplier)
        response['store_level_data'] = store_index.to_dict('records')

    return JSONResponse(content=response)


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
