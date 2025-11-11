"""
Data Quality Health Check Module

Identifies data quality issues and provides health scores per store and supplier.
"""

import pandas as pd
import numpy as np
from typing import Dict, List, Tuple


class DataQualityChecker:
    """
    Comprehensive data quality assessment for retail sales data.

    Checks for:
    - Missing values in critical fields
    - Duplicate records
    - Suspicious outliers (negative quantities, extreme prices)
    - Unreliable stores/suppliers based on data patterns
    """

    def __init__(self, df: pd.DataFrame):
        """Initialize with sales dataframe."""
        self.df = df.copy()
        self.issues = []

    def check_missing_values(self) -> pd.DataFrame:
        """Identify missing values in critical fields."""
        missing_stats = pd.DataFrame({
            'column': self.df.columns,
            'missing_count': self.df.isnull().sum().values,
            'missing_pct': (self.df.isnull().sum() / len(self.df) * 100).values
        })
        return missing_stats[missing_stats['missing_count'] > 0].reset_index(drop=True)

    def check_duplicates(self) -> pd.DataFrame:
        """Identify duplicate records based on key fields."""
        key_cols = ['Store Name', 'Item_Code', 'Date Of Sale']
        duplicates = self.df[self.df.duplicated(subset=key_cols, keep=False)]

        if len(duplicates) > 0:
            dup_summary = duplicates.groupby(key_cols).agg({
                'Quantity': 'sum',
                'Total Sales': 'sum'
            }).reset_index()
            return dup_summary
        return pd.DataFrame()

    def check_outliers(self) -> Dict[str, pd.DataFrame]:
        """Identify suspicious outliers in numerical fields."""
        outliers = {}

        # Negative quantities
        neg_qty = self.df[self.df['Quantity'] < 0]
        if len(neg_qty) > 0:
            outliers['negative_quantity'] = neg_qty[
                ['Store Name', 'Supplier', 'Description', 'Quantity', 'Date Of Sale']
            ]

        # Zero quantities with sales
        zero_qty_with_sales = self.df[(self.df['Quantity'] == 0) & (self.df['Total Sales'] > 0)]
        if len(zero_qty_with_sales) > 0:
            outliers['zero_qty_with_sales'] = zero_qty_with_sales[
                ['Store Name', 'Supplier', 'Description', 'Quantity', 'Total Sales']
            ]

        # Negative sales
        neg_sales = self.df[self.df['Total Sales'] < 0]
        if len(neg_sales) > 0:
            outliers['negative_sales'] = neg_sales[
                ['Store Name', 'Supplier', 'Description', 'Total Sales', 'Date Of Sale']
            ]

        # Extreme prices (calculated unit price)
        df_with_unit_price = self.df[self.df['Quantity'] > 0].copy()
        df_with_unit_price['unit_price'] = df_with_unit_price['Total Sales'] / df_with_unit_price['Quantity']

        # Unit price > 10x RRP or < 1% of RRP (where RRP exists)
        price_check = df_with_unit_price[df_with_unit_price['RRP'].notna()].copy()
        extreme_high = price_check[price_check['unit_price'] > (price_check['RRP'] * 10)]
        extreme_low = price_check[price_check['unit_price'] < (price_check['RRP'] * 0.01)]

        if len(extreme_high) > 0:
            outliers['extreme_high_price'] = extreme_high[
                ['Store Name', 'Supplier', 'Description', 'unit_price', 'RRP', 'Quantity']
            ]

        if len(extreme_low) > 0:
            outliers['extreme_low_price'] = extreme_low[
                ['Store Name', 'Supplier', 'Description', 'unit_price', 'RRP', 'Quantity']
            ]

        return outliers

    def calculate_store_health_score(self) -> pd.DataFrame:
        """
        Calculate data quality health score per store.

        Scoring based on:
        - Missing data rate (30%)
        - Outlier rate (40%)
        - Duplicate rate (30%)

        Score: 0-100 (higher is better)
        """
        store_scores = []

        for store in self.df['Store Name'].unique():
            store_df = self.df[self.df['Store Name'] == store]
            total_records = len(store_df)

            # Missing critical fields (Supplier, RRP)
            missing_supplier = store_df['Supplier'].isnull().sum()
            missing_rrp = store_df['RRP'].isnull().sum()
            missing_rate = (missing_supplier + missing_rrp) / (total_records * 2)

            # Outliers
            neg_qty = (store_df['Quantity'] < 0).sum()
            neg_sales = (store_df['Total Sales'] < 0).sum()
            outlier_rate = (neg_qty + neg_sales) / total_records

            # Duplicates
            key_cols = ['Store Name', 'Item_Code', 'Date Of Sale']
            dup_count = store_df.duplicated(subset=key_cols).sum()
            dup_rate = dup_count / total_records

            # Calculate weighted score
            missing_score = max(0, (1 - missing_rate) * 30)
            outlier_score = max(0, (1 - outlier_rate) * 40)
            dup_score = max(0, (1 - dup_rate) * 30)

            health_score = missing_score + outlier_score + dup_score

            # Categorize
            if health_score >= 90:
                category = 'Excellent'
            elif health_score >= 75:
                category = 'Good'
            elif health_score >= 60:
                category = 'Fair'
            else:
                category = 'Poor'

            store_scores.append({
                'store': store,
                'total_records': total_records,
                'missing_rate': round(missing_rate * 100, 2),
                'outlier_rate': round(outlier_rate * 100, 2),
                'duplicate_rate': round(dup_rate * 100, 2),
                'health_score': round(health_score, 2),
                'category': category
            })

        return pd.DataFrame(store_scores).sort_values('health_score', ascending=False)

    def calculate_supplier_health_score(self) -> pd.DataFrame:
        """
        Calculate data quality health score per supplier.

        Similar methodology to store health score.
        """
        supplier_scores = []

        for supplier in self.df['Supplier'].dropna().unique():
            supplier_df = self.df[self.df['Supplier'] == supplier]
            total_records = len(supplier_df)

            # Missing RRP
            missing_rrp = supplier_df['RRP'].isnull().sum()
            missing_rate = missing_rrp / total_records

            # Outliers
            neg_qty = (supplier_df['Quantity'] < 0).sum()
            neg_sales = (supplier_df['Total Sales'] < 0).sum()
            zero_qty_with_sales = ((supplier_df['Quantity'] == 0) & (supplier_df['Total Sales'] > 0)).sum()
            outlier_rate = (neg_qty + neg_sales + zero_qty_with_sales) / total_records

            # Duplicates
            key_cols = ['Store Name', 'Item_Code', 'Date Of Sale']
            dup_count = supplier_df.duplicated(subset=key_cols).sum()
            dup_rate = dup_count / total_records

            # Calculate weighted score
            missing_score = max(0, (1 - missing_rate) * 30)
            outlier_score = max(0, (1 - outlier_rate) * 40)
            dup_score = max(0, (1 - dup_rate) * 30)

            health_score = missing_score + outlier_score + dup_score

            # Categorize
            if health_score >= 90:
                category = 'Excellent'
            elif health_score >= 75:
                category = 'Good'
            elif health_score >= 60:
                category = 'Fair'
            else:
                category = 'Poor'

            supplier_scores.append({
                'supplier': supplier,
                'total_records': total_records,
                'missing_rrp_rate': round(missing_rate * 100, 2),
                'outlier_rate': round(outlier_rate * 100, 2),
                'duplicate_rate': round(dup_rate * 100, 2),
                'health_score': round(health_score, 2),
                'category': category
            })

        return pd.DataFrame(supplier_scores).sort_values('health_score', ascending=False)

    def generate_summary_report(self) -> Dict:
        """Generate comprehensive data quality summary."""
        missing = self.check_missing_values()
        duplicates = self.check_duplicates()
        outliers = self.check_outliers()
        store_health = self.calculate_store_health_score()
        supplier_health = self.calculate_supplier_health_score()

        report = {
            'dataset_overview': {
                'total_records': len(self.df),
                'date_range': f"{self.df['Date Of Sale'].min()} to {self.df['Date Of Sale'].max()}",
                'num_stores': self.df['Store Name'].nunique(),
                'num_suppliers': self.df['Supplier'].nunique(),
                'num_skus': self.df['Item_Code'].nunique()
            },
            'missing_values': missing.to_dict('records'),
            'duplicates_count': len(duplicates),
            'outliers_summary': {k: len(v) for k, v in outliers.items()},
            'store_health_top_10': store_health.head(10).to_dict('records'),
            'store_health_bottom_10': store_health.tail(10).to_dict('records'),
            'supplier_health_top_10': supplier_health.head(10).to_dict('records'),
            'supplier_health_bottom_10': supplier_health.tail(10).to_dict('records'),
            'key_issues': self._identify_key_issues(missing, duplicates, outliers, store_health, supplier_health)
        }

        return report

    def _identify_key_issues(self, missing, duplicates, outliers, store_health, supplier_health) -> List[str]:
        """Identify and summarize key data quality issues."""
        issues = []

        # Missing values
        if len(missing) > 0:
            critical_missing = missing[missing['column'].isin(['Supplier', 'RRP'])]
            if len(critical_missing) > 0:
                for _, row in critical_missing.iterrows():
                    issues.append(f"{row['column']}: {row['missing_count']} missing ({row['missing_pct']:.2f}%)")

        # Duplicates
        if len(duplicates) > 0:
            issues.append(f"Found {len(duplicates)} duplicate records")

        # Outliers
        for outlier_type, df in outliers.items():
            if len(df) > 0:
                issues.append(f"{outlier_type}: {len(df)} records")

        # Poor quality stores
        poor_stores = store_health[store_health['health_score'] < 60]
        if len(poor_stores) > 0:
            issues.append(f"{len(poor_stores)} stores with poor data quality (score < 60)")

        # Poor quality suppliers
        poor_suppliers = supplier_health[supplier_health['health_score'] < 60]
        if len(poor_suppliers) > 0:
            issues.append(f"{len(poor_suppliers)} suppliers with poor data quality (score < 60)")

        return issues
