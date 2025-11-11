"""
Pricing Index and Competitive Positioning Module

Compares supplier pricing against competitors within same Sub-Department and Section.
"""

import pandas as pd
import numpy as np
from typing import Dict, List


class PricingIndexAnalyzer:
    """
    Build supplier price index comparing realized average unit prices
    against competitors within same Sub-Department and Section, per store.

    Provides:
    - Store-level competitive positioning
    - Category-level price comparison
    - Premium/discount analysis vs market
    - RRP vs realized price discounting patterns
    """

    def __init__(self, df: pd.DataFrame):
        """Initialize pricing analyzer with sales data."""
        self.df = self._prepare_data(df)

    def _prepare_data(self, df: pd.DataFrame) -> pd.DataFrame:
        """Clean and prepare data for pricing analysis."""
        df = df.copy()

        # Calculate unit price
        df['unit_price'] = np.where(
            df['Quantity'] > 0,
            df['Total Sales'] / df['Quantity'],
            np.nan
        )

        # Calculate discount from RRP
        df['discount_from_rrp_pct'] = np.where(
            (df['RRP'].notna()) & (df['RRP'] > 0),
            (df['RRP'] - df['unit_price']) / df['RRP'] * 100,
            np.nan
        )

        # Filter valid records
        df = df[
            (df['Quantity'] > 0) &
            (df['unit_price'].notna()) &
            (df['Supplier'].notna())
        ].copy()

        return df

    def calculate_category_avg_prices(self) -> pd.DataFrame:
        """
        Calculate average prices by Sub-Department and Section for all suppliers.

        This serves as the competitive benchmark.
        """
        category_avg = self.df.groupby(['Sub-Department', 'Section', 'Supplier']).agg({
            'unit_price': 'mean',
            'RRP': 'mean',
            'Quantity': 'sum',
            'Total Sales': 'sum'
        }).reset_index()

        category_avg.columns = [
            'Sub-Department', 'Section', 'Supplier',
            'avg_unit_price', 'avg_rrp', 'total_quantity', 'total_sales'
        ]

        return category_avg

    def calculate_store_level_index(self, target_supplier: str = 'BIDCO AFRICA LIMITED') -> pd.DataFrame:
        """
        Calculate store-level price index comparing target supplier vs competitors
        in the same Sub-Department and Section.

        Args:
            target_supplier: Supplier to analyze

        Returns:
            DataFrame with store-level price positioning
        """
        store_category_prices = self.df.groupby(
            ['Store Name', 'Sub-Department', 'Section', 'Supplier']
        ).agg({
            'unit_price': 'mean',
            'RRP': 'mean',
            'Quantity': 'sum',
            'Total Sales': 'sum',
            'discount_from_rrp_pct': 'mean'
        }).reset_index()

        store_category_prices.columns = [
            'store', 'sub_department', 'section', 'supplier',
            'avg_unit_price', 'avg_rrp', 'total_quantity', 'total_sales',
            'avg_discount_from_rrp'
        ]

        # Calculate market average (excluding target supplier)
        market_avg = store_category_prices[
            store_category_prices['supplier'] != target_supplier
        ].groupby(['store', 'sub_department', 'section']).agg({
            'avg_unit_price': 'mean',
            'avg_rrp': 'mean',
            'total_quantity': 'sum'
        }).reset_index()

        market_avg.columns = [
            'store', 'sub_department', 'section',
            'market_avg_unit_price', 'market_avg_rrp', 'market_total_quantity'
        ]

        # Get target supplier data
        target_data = store_category_prices[
            store_category_prices['supplier'] == target_supplier
        ].copy()

        # Merge with market averages
        comparison = target_data.merge(
            market_avg,
            on=['store', 'sub_department', 'section'],
            how='left'
        )

        # Calculate price index (100 = at market, >100 = premium, <100 = discount)
        comparison['price_index'] = np.where(
            comparison['market_avg_unit_price'] > 0,
            (comparison['avg_unit_price'] / comparison['market_avg_unit_price']) * 100,
            np.nan
        )

        # Price positioning category
        comparison['positioning'] = comparison['price_index'].apply(self._categorize_positioning)

        # RRP comparison
        comparison['rrp_vs_market_pct'] = np.where(
            comparison['market_avg_rrp'] > 0,
            ((comparison['avg_rrp'] - comparison['market_avg_rrp']) / comparison['market_avg_rrp']) * 100,
            np.nan
        )

        return comparison

    def _categorize_positioning(self, price_index: float) -> str:
        """Categorize price positioning based on index value."""
        if pd.isna(price_index):
            return 'No Competition'
        elif price_index >= 110:
            return 'Premium'
        elif price_index >= 105:
            return 'Slight Premium'
        elif price_index >= 95:
            return 'At Market'
        elif price_index >= 90:
            return 'Slight Discount'
        else:
            return 'Discount'

    def calculate_overall_positioning(self, target_supplier: str = 'BIDCO AFRICA LIMITED') -> Dict:
        """
        Calculate overall price positioning summary for target supplier.

        Args:
            target_supplier: Supplier to analyze

        Returns:
            Dictionary with overall positioning metrics
        """
        store_index = self.calculate_store_level_index(target_supplier)

        # Weighted average price index (by quantity)
        weighted_index = np.average(
            store_index['price_index'].dropna(),
            weights=store_index[store_index['price_index'].notna()]['total_quantity']
        )

        # Positioning distribution
        positioning_dist = store_index['positioning'].value_counts().to_dict()

        # Category-level summary
        category_summary = store_index.groupby(['sub_department', 'section']).agg({
            'price_index': 'mean',
            'avg_unit_price': 'mean',
            'market_avg_unit_price': 'mean',
            'total_quantity': 'sum',
            'avg_discount_from_rrp': 'mean'
        }).reset_index()

        category_summary = category_summary.sort_values('total_quantity', ascending=False)

        return {
            'overall_price_index': float(weighted_index),
            'overall_positioning': self._categorize_positioning(weighted_index),
            'positioning_distribution': positioning_dist,
            'top_categories': category_summary.head(10).to_dict('records'),
            'premium_categories': store_index[
                store_index['positioning'].isin(['Premium', 'Slight Premium'])
            ].groupby(['sub_department', 'section'])['price_index'].mean().sort_values(ascending=False).head(5).to_dict(),
            'discount_categories': store_index[
                store_index['positioning'].isin(['Discount', 'Slight Discount'])
            ].groupby(['sub_department', 'section'])['price_index'].mean().sort_values().head(5).to_dict()
        }

    def compare_suppliers_by_category(self, category: str, section: str = None) -> pd.DataFrame:
        """
        Compare all suppliers in a specific category/section.

        Args:
            category: Sub-Department name
            section: Optional Section name for more granular comparison

        Returns:
            DataFrame with supplier comparison
        """
        df_filtered = self.df[self.df['Sub-Department'] == category].copy()

        if section:
            df_filtered = df_filtered[df_filtered['Section'] == section]

        supplier_comparison = df_filtered.groupby('Supplier').agg({
            'unit_price': 'mean',
            'RRP': 'mean',
            'Quantity': 'sum',
            'Total Sales': 'sum',
            'discount_from_rrp_pct': 'mean',
            'Store Name': 'nunique'
        }).reset_index()

        supplier_comparison.columns = [
            'supplier', 'avg_unit_price', 'avg_rrp',
            'total_quantity', 'total_sales', 'avg_discount_from_rrp', 'store_count'
        ]

        # Calculate market share
        supplier_comparison['quantity_share_pct'] = (
            supplier_comparison['total_quantity'] / supplier_comparison['total_quantity'].sum() * 100
        )

        supplier_comparison['value_share_pct'] = (
            supplier_comparison['total_sales'] / supplier_comparison['total_sales'].sum() * 100
        )

        # Rank by price
        supplier_comparison = supplier_comparison.sort_values('avg_unit_price', ascending=False)
        supplier_comparison['price_rank'] = range(1, len(supplier_comparison) + 1)

        return supplier_comparison

    def generate_bidco_pricing_insights(self) -> List[str]:
        """
        Generate actionable pricing insights for Bidco brand managers.

        Returns:
            List of insight strings
        """
        insights = []

        overall = self.calculate_overall_positioning('BIDCO AFRICA LIMITED')
        store_index = self.calculate_store_level_index('BIDCO AFRICA LIMITED')

        # Insight 1: Overall positioning
        insights.append(
            f"Bidco's overall price index is {overall['overall_price_index']:.1f} ({overall['overall_positioning']}). "
            f"Across all categories, Bidco is positioned {overall['overall_positioning'].lower()} relative to competitors."
        )

        # Insight 2: Positioning consistency
        dist = overall['positioning_distribution']
        if len(dist) > 1:
            most_common = max(dist, key=dist.get)
            insights.append(
                f"Pricing strategy varies by store: {dist.get(most_common, 0)} observations show '{most_common}' positioning, "
                f"suggesting inconsistent competitive positioning across markets."
            )

        # Insight 3: Premium categories
        if overall['premium_categories']:
            top_premium = list(overall['premium_categories'].items())[0]
            insights.append(
                f"Highest premium category: {top_premium[0]} where Bidco prices are {top_premium[1]-100:.1f}% above market average. "
                f"Consider if premium pricing is supported by brand strength or if price reductions could drive volume."
            )

        # Insight 4: Discount categories
        if overall['discount_categories']:
            top_discount = list(overall['discount_categories'].items())[0]
            insights.append(
                f"Deepest discount category: {top_discount[0]} where Bidco prices are {100-top_discount[1]:.1f}% below market. "
                f"Evaluate if this aggressive pricing is necessary or if there's opportunity to improve margins."
            )

        # Insight 5: Store-level variation
        store_variance = store_index.groupby('store')['price_index'].mean().std()
        if store_variance > 10:
            insights.append(
                f"Price positioning varies significantly across stores (std dev: {store_variance:.1f}). "
                f"Consider harmonizing pricing strategy for consistent brand positioning."
            )

        return insights

    def get_detailed_comparison(self, target_supplier: str = 'BIDCO AFRICA LIMITED') -> Dict:
        """
        Get comprehensive pricing comparison data.

        Args:
            target_supplier: Supplier to analyze

        Returns:
            Dictionary with detailed pricing data
        """
        store_level = self.calculate_store_level_index(target_supplier)
        overall = self.calculate_overall_positioning(target_supplier)

        # Get top categories for Bidco
        bidco_categories = store_level.groupby(['sub_department', 'section']).agg({
            'total_quantity': 'sum',
            'price_index': 'mean',
            'avg_unit_price': 'mean',
            'market_avg_unit_price': 'mean',
            'avg_discount_from_rrp': 'mean'
        }).reset_index().sort_values('total_quantity', ascending=False)

        return {
            'overall_metrics': overall,
            'store_level_data': store_level.to_dict('records'),
            'category_summary': bidco_categories.head(20).to_dict('records'),
            'pricing_insights': self.generate_bidco_pricing_insights()
        }
