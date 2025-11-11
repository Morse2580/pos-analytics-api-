"""
Promotions Detection and Performance Analysis Module

Detects promotional periods and calculates key promotion KPIs.
"""

import pandas as pd
import numpy as np
from typing import Dict, List


class PromotionAnalyzer:
    """
    Detect promotions and analyze their impact on sales performance.

    Promotion detection logic:
    - A SKU is "on promo" when its realized unit price is >=10% below RRP
    - Must occur for >=2 days within the week to be considered a valid promotion
    - Excludes records with missing RRP or invalid data
    """

    def __init__(self, df: pd.DataFrame, discount_threshold: float = 0.10, min_days: int = 2):
        """
        Initialize promotion analyzer.

        Args:
            df: Sales dataframe
            discount_threshold: Minimum discount to consider as promo (default 10%)
            min_days: Minimum days at discount to qualify as promo (default 2)
        """
        self.df = self._prepare_data(df)
        self.discount_threshold = discount_threshold
        self.min_days = min_days

    def _prepare_data(self, df: pd.DataFrame) -> pd.DataFrame:
        """Clean and prepare data for promotion analysis."""
        df = df.copy()

        # Calculate unit price
        df['unit_price'] = np.where(
            df['Quantity'] > 0,
            df['Total Sales'] / df['Quantity'],
            np.nan
        )

        # Filter valid records (positive quantity, non-null RRP and unit price)
        df = df[
            (df['Quantity'] > 0) &
            (df['RRP'].notna()) &
            (df['RRP'] > 0) &
            (df['unit_price'].notna())
        ].copy()

        return df

    def detect_promotions(self) -> pd.DataFrame:
        """
        Detect promotional periods per SKU per store.

        Returns dataframe with promotion flags and discount depths.
        """
        df = self.df.copy()

        # Calculate discount from RRP
        df['discount_pct'] = (df['RRP'] - df['unit_price']) / df['RRP'] * 100

        # Flag potential promo days (discount >= threshold)
        df['is_promo_day'] = df['discount_pct'] >= (self.discount_threshold * 100)

        # Count promo days per SKU per store
        promo_days = df.groupby(['Store Name', 'Item_Code', 'is_promo_day']).size().unstack(fill_value=0)

        if True in promo_days.columns:
            promo_days['promo_day_count'] = promo_days[True]
        else:
            promo_days['promo_day_count'] = 0

        promo_days = promo_days.reset_index()

        # Merge back to main dataframe
        df = df.merge(
            promo_days[['Store Name', 'Item_Code', 'promo_day_count']],
            on=['Store Name', 'Item_Code'],
            how='left'
        )

        # Final promo flag: promo day AND >= min_days threshold
        df['on_promotion'] = (df['is_promo_day']) & (df['promo_day_count'] >= self.min_days)

        return df

    def calculate_kpis(self, supplier_filter: str = None) -> Dict:
        """
        Calculate promotion KPIs.

        Args:
            supplier_filter: Optional supplier name to filter analysis (e.g., 'BIDCO AFRICA LIMITED')

        Returns:
            Dictionary with promotion KPIs
        """
        df_promo = self.detect_promotions()

        # Filter by supplier if specified
        if supplier_filter:
            df_promo = df_promo[
                df_promo['Supplier'].str.contains(supplier_filter, case=False, na=False)
            ].copy()

        # Aggregate by SKU and promotion status
        agg_df = df_promo.groupby(['Item_Code', 'Description', 'Supplier', 'on_promotion']).agg({
            'Quantity': 'sum',
            'Total Sales': 'sum',
            'Store Name': 'nunique',
            'Date Of Sale': 'nunique',
            'unit_price': 'mean',
            'RRP': 'mean',
            'discount_pct': 'mean'
        }).reset_index()

        agg_df.columns = [
            'Item_Code', 'Description', 'Supplier', 'on_promotion',
            'total_quantity', 'total_sales', 'store_count', 'day_count',
            'avg_unit_price', 'avg_rrp', 'avg_discount_pct'
        ]

        # Pivot to get baseline vs promo
        pivot_df = agg_df.pivot_table(
            index=['Item_Code', 'Description', 'Supplier'],
            columns='on_promotion',
            values=['total_quantity', 'total_sales', 'store_count', 'avg_unit_price', 'avg_discount_pct'],
            aggfunc='first'
        ).reset_index()

        # Flatten column names
        pivot_df.columns = [
            f"{col[0]}_{col[1]}" if col[1] != '' else col[0]
            for col in pivot_df.columns
        ]

        # Rename for clarity
        rename_dict = {}
        for col in pivot_df.columns:
            if col.endswith('_False'):
                rename_dict[col] = col.replace('_False', '_baseline')
            elif col.endswith('_True'):
                rename_dict[col] = col.replace('_True', '_promo')

        pivot_df.rename(columns=rename_dict, inplace=True)

        # Calculate uplift
        if 'total_quantity_baseline' in pivot_df.columns and 'total_quantity_promo' in pivot_df.columns:
            pivot_df['quantity_uplift_pct'] = np.where(
                pivot_df['total_quantity_baseline'] > 0,
                ((pivot_df['total_quantity_promo'] - pivot_df['total_quantity_baseline'])
                 / pivot_df['total_quantity_baseline'] * 100),
                np.nan
            )
        else:
            pivot_df['quantity_uplift_pct'] = np.nan

        # Promo coverage (% of stores running promo)
        total_stores = df_promo['Store Name'].nunique()
        if 'store_count_promo' in pivot_df.columns:
            pivot_df['promo_coverage_pct'] = (pivot_df['store_count_promo'] / total_stores * 100)
        else:
            pivot_df['promo_coverage_pct'] = 0

        # Ensure all expected columns exist
        for col in ['avg_discount_pct_promo', 'avg_unit_price_baseline', 'avg_unit_price_promo',
                    'total_quantity_baseline', 'total_quantity_promo', 'store_count_baseline', 'store_count_promo']:
            if col not in pivot_df.columns:
                pivot_df[col] = 0

        # Fill NaN values
        pivot_df = pivot_df.fillna(0)

        # Top performing SKUs - only select available columns
        top_sku_cols = ['Description', 'Supplier', 'quantity_uplift_pct', 'promo_coverage_pct']
        optional_cols = ['avg_discount_pct_promo', 'avg_unit_price_baseline', 'avg_unit_price_promo']
        for col in optional_cols:
            if col in pivot_df.columns:
                top_sku_cols.append(col)

        top_skus = pivot_df.nlargest(10, 'quantity_uplift_pct')[top_sku_cols].to_dict('records')

        # Overall summary - handle missing columns gracefully
        avg_uplift = pivot_df[pivot_df['quantity_uplift_pct'] > 0]['quantity_uplift_pct'].mean()
        avg_discount = 0
        if 'avg_discount_pct_promo' in pivot_df.columns:
            avg_discount = pivot_df[pivot_df['avg_discount_pct_promo'] > 0]['avg_discount_pct_promo'].mean()

        summary = {
            'total_skus_analyzed': len(pivot_df),
            'skus_with_promos': len(pivot_df[pivot_df['promo_coverage_pct'] > 0]),
            'avg_promo_uplift': float(avg_uplift) if not pd.isna(avg_uplift) else 0.0,
            'avg_promo_coverage': float(pivot_df['promo_coverage_pct'].mean()),
            'avg_discount_depth': float(avg_discount) if not pd.isna(avg_discount) else 0.0
        }

        return {
            'summary': summary,
            'top_performing_skus': top_skus,
            'detailed_data': pivot_df.to_dict('records')
        }

    def get_bidco_insights(self) -> Dict:
        """
        Generate Bidco-specific promotional insights.

        Returns key insights for brand managers.
        """
        bidco_kpis = self.calculate_kpis(supplier_filter='BIDCO')
        df_promo = self.detect_promotions()

        bidco_df = df_promo[
            df_promo['Supplier'].str.contains('BIDCO', case=False, na=False)
        ].copy()

        # Category-level performance
        category_perf = bidco_df.groupby(['Sub-Department', 'Section', 'on_promotion']).agg({
            'Quantity': 'sum',
            'Total Sales': 'sum',
            'discount_pct': 'mean'
        }).reset_index()

        # Store-level promo effectiveness
        store_perf = bidco_df[bidco_df['on_promotion']].groupby('Store Name').agg({
            'Quantity': 'sum',
            'Total Sales': 'sum',
            'Item_Code': 'nunique',
            'discount_pct': 'mean'
        }).reset_index()

        store_perf.columns = ['store', 'promo_quantity', 'promo_sales', 'sku_count', 'avg_discount']
        store_perf = store_perf.sort_values('promo_sales', ascending=False)

        insights = {
            'bidco_kpis': bidco_kpis,
            'top_promo_stores': store_perf.head(10).to_dict('records'),
            'category_breakdown': category_perf.to_dict('records')
        }

        return insights

    def generate_commercial_insights(self, supplier_filter: str = 'BIDCO') -> List[str]:
        """
        Generate actionable commercial insights for brand managers.

        Args:
            supplier_filter: Supplier to analyze (default: BIDCO)

        Returns:
            List of insight strings
        """
        insights = []
        kpis = self.calculate_kpis(supplier_filter=supplier_filter)

        summary = kpis['summary']
        top_skus = kpis['top_performing_skus']

        # Insight 1: Overall promo effectiveness
        if summary['avg_promo_uplift'] > 0:
            insights.append(
                f"Promotions drive an average {summary['avg_promo_uplift']:.1f}% quantity uplift for {supplier_filter} SKUs, "
                f"with an average discount depth of {summary['avg_discount_depth']:.1f}%."
            )

        # Insight 2: Coverage opportunity
        if summary['avg_promo_coverage'] < 50:
            insights.append(
                f"Promo coverage is low at {summary['avg_promo_coverage']:.1f}% of stores on average. "
                f"Expanding promotional execution to more stores could drive significant volume gains."
            )

        # Insight 3: Top performing SKUs
        if len(top_skus) > 0:
            top_sku = top_skus[0]
            insights.append(
                f"Top performer: '{top_sku['Description']}' delivers {top_sku['quantity_uplift_pct']:.1f}% uplift "
                f"with {top_sku['promo_coverage_pct']:.1f}% store coverage at {top_sku['avg_discount_pct_promo']:.1f}% discount."
            )

        # Insight 4: Low coverage high performers
        high_uplift_low_coverage = [
            sku for sku in top_skus
            if sku['quantity_uplift_pct'] > 50 and sku['promo_coverage_pct'] < 30
        ]

        if high_uplift_low_coverage:
            sku = high_uplift_low_coverage[0]
            insights.append(
                f"Opportunity: '{sku['Description']}' shows {sku['quantity_uplift_pct']:.1f}% uplift "
                f"but only runs in {sku['promo_coverage_pct']:.1f}% of stores. Scale this promo for higher ROI."
            )

        return insights
