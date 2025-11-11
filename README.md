# Duck Retail Analytics Platform

A retail analytics solution transforming POS data into actionable insights for Bidco Africa Limited.

## Overview

This platform analyzes retail sales data to provide:

1. **Data Quality Health Checks** - Identifies unreliable data and scores store/supplier data quality
2. **Promotions Analysis** - Detects promotional periods and measures sales impact
3. **Pricing Intelligence** - Compares Bidco pricing against competitors

## Quick Start

### Option 1: Docker (Recommended)

```bash
docker-compose up -d
```

### Option 2: Direct Python

```bash
# Install dependencies
pip install -r requirements.txt

# Validate solution
python3 tests/test_solution.py

# Start API
python3 src/api/main.py
```

### Option 3: Quick Start Script

```bash
./run.sh
```

API available at: **http://localhost:8000**
Documentation: **http://localhost:8000/docs**

## Project Structure

## API Endpoints

### `/data_quality`

Comprehensive data quality report including:
- Missing values and duplicates
- Outlier detection (negative quantities, extreme prices)
- Store and supplier health scores (0-100 scale)
- Key data quality issues

**Example:**
```bash
curl http://localhost:8000/data_quality

# Filter excellent stores only
curl "http://localhost:8000/data_quality?category=Excellent"
```

### `/promo_summary`

Promotion analysis with KPIs:
- Promo uplift % (quantity vs baseline)
- Promo coverage % (store penetration)
- Discount depth and pricing
- Top performing SKUs
- Commercial insights

**Example:**
```bash
curl "http://localhost:8000/promo_summary?supplier=BIDCO"
```

### `/price_index`

Competitive pricing intelligence:
- Price index (Bidco vs competitors)
- Store-level positioning (Premium/At Market/Discount)
- Category breakdown
- Strategic pricing insights

**Example:**
```bash
# Summary view
curl "http://localhost:8000/price_index?supplier=BIDCO AFRICA LIMITED"

# Detailed store-level data
curl "http://localhost:8000/price_index?view=detailed"
```

## Methodology

### 1. Data Quality Health Score

**Scoring (0-100):**
- Missing data rate: 30%
- Outlier rate: 40%
- Duplicate rate: 30%

**Categories:**
- Excellent: 90-100
- Good: 75-89
- Fair: 60-74
- Poor: <60

**Checks:**
- Missing critical fields (Supplier, RRP)
- Duplicate records (Store, SKU, Date)
- Negative quantities or sales
- Extreme prices (>10x or <1% of RRP)

### 2. Promotion Detection

**A SKU is "on promotion" when:**
1. Realized unit price is ≥10% below RRP
2. Discount occurs for ≥2 days within the week
3. Valid RRP and quantity data exist

**Rationale:**
- 10% threshold filters out data errors and minor fluctuations
- 2-day minimum ensures genuine promotional activity
- Prevents false positives from data quality issues

**KPIs Calculated:**
- **Promo Uplift %**: (Promo quantity - Baseline) / Baseline × 100
- **Promo Coverage %**: Stores running promo / Total stores × 100
- **Price Impact**: Average discount depth from RRP
- **Baseline vs Promo Price**: Realized unit prices in each period

### 3. Pricing Index

**Price Index = (Bidco Avg Unit Price / Market Avg Unit Price) × 100**

**Where:**
- Market Avg = Mean of all competitors in same Sub-Department + Section + Store
- Unit Price = Total Sales / Quantity (realized transaction price)

**Interpretation:**
- 100 = At market
- 110+ = Premium positioning
- 90-110 = Near market
- <90 = Discount positioning

**Why This Matters:**
- **Store-level granularity**: Same SKU may have different positioning by location
- **Category-specific**: Compares within narrow product segments (e.g., vegetable oil vs vegetable oil)
- **Realized prices**: Uses actual transaction prices, not RRPs

## Key Design Decisions

### Data Assumptions

1. **Unit Price Calculation**: Total Sales / Quantity
   - Filters out zero/negative quantities

2. **Date Range**: 7 consecutive days (Sept 22-28, 2025)
   - 2-day promotion minimum appropriate for weekly data

3. **Missing Data**: Excluded from analysis (32 missing RRPs, 15 missing Suppliers)
   - Maintains data integrity with minimal loss (<0.2%)

4. **Competitive Set**: Same Sub-Department + Same Section
   - Consumers substitute within narrow categories
   - More accurate than broader Department-level comparison

## Exploratory Data Analysis

Interactive Jupyter notebook for data discovery and methodology validation:

```bash
jupyter notebook data_discovery.ipynb
```
## Testing

```bash
python3 tests/test_solution.py
```

Validates:
- Data loading (30,691 records)
- All three analysis modules
- End-to-end functionality

**Built for Duck by:** Moses Njau
**Date:** November 2025
