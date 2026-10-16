from __future__ import annotations
from dataclasses import dataclass
from datetime import datetime, timezone
import hashlib
import json
from typing import Any
import numpy as np
import pandas as pd
from sklearn.ensemble import IsolationForest
ML_FEATURES = ['transaction_count', 'avg_order_value', 'avg_discount', 'cancel_rate', 'return_rate', 'negative_margin_rate', 'avg_margin', 'avg_stock_on_hand', 'avg_reorder_threshold', 'stockout_rate', 'avg_supplier_delay', 'stockout_inconsistency_rate', 'supplier_lead_days', 'base_margin_pct']
FEATURE_LABELS = {'transaction_count': 'transaction volume', 'avg_order_value': 'average order value', 'avg_discount': 'average discount', 'cancel_rate': 'cancellation rate', 'return_rate': 'return rate', 'negative_margin_rate': 'apparent negative-margin rate', 'avg_margin': 'average estimated margin', 'avg_stock_on_hand': 'average stock on hand', 'avg_reorder_threshold': 'average reorder threshold', 'stockout_rate': 'stockout-flag rate', 'avg_supplier_delay': 'supplier delay', 'stockout_inconsistency_rate': 'stockout inconsistency rate', 'supplier_lead_days': 'supplier lead time', 'base_margin_pct': 'base price-cost margin'}
ALLOWED_STATUSES = {'Completed', 'Cancelled', 'Returned', 'Pending'}

@dataclass
class AnalysisResult:
    overview: dict[str, Any]
    transactions_summary: dict[str, Any]
    product_risk: pd.DataFrame
    categories: pd.DataFrame
    campaign_issues: pd.DataFrame
    inventory_issues: pd.DataFrame
    campaign_summary: dict[str, Any]
    inventory_summary: dict[str, Any]
    metadata: dict[str, Any]
    diagnostics: dict[str, Any]
    validation: dict[str, Any]

def _minmax(series: pd.Series) -> pd.Series:
    values = pd.to_numeric(series, errors='coerce').replace([np.inf, -np.inf], np.nan)
    values = values.fillna(values.median() if not values.dropna().empty else 0.0)
    lo, hi = (float(values.min()), float(values.max()))
    if hi == lo:
        return pd.Series(np.zeros(len(values)), index=values.index, dtype=float)
    return (values - lo) / (hi - lo)

def _stable_dataset_hash(frames: dict[str, pd.DataFrame]) -> str:
    h = hashlib.sha256()
    for name in sorted(frames):
        df = frames[name]
        h.update(name.encode('utf-8'))
        h.update('|'.join(map(str, df.columns)).encode('utf-8'))
        hashed = pd.util.hash_pandas_object(df, index=True).values
        h.update(hashed.tobytes())
    return h.hexdigest()[:16]

def validate_data(customers, products, transactions, inventory, campaigns) -> dict[str, Any]:
    required = {'customers': {'customer_id', 'region', 'customer_segment', 'signup_date', 'preferred_channel'}, 'products': {'product_id', 'category', 'unit_cost', 'list_price', 'supplier_lead_days'}, 'transactions': {'transaction_id', 'customer_id', 'product_id', 'timestamp', 'quantity', 'unit_price', 'discount_pct', 'status', 'channel', 'payment_method'}, 'inventory': {'inventory_record_id', 'product_id', 'date', 'stock_on_hand', 'reorder_threshold', 'stockout_flag', 'supplier_delay_days'}, 'campaigns': {'campaign_id', 'date', 'channel', 'category', 'spend', 'impressions', 'clicks', 'conversions'}}
    frames = {'customers': customers, 'products': products, 'transactions': transactions, 'inventory': inventory, 'campaigns': campaigns}
    errors: list[str] = []
    warnings: list[str] = []
    for name, cols in required.items():
        missing = sorted(cols - set(frames[name].columns))
        if missing:
            errors.append(f'{name}: missing columns {missing}')
    if errors:
        return {'valid': False, 'errors': errors, 'warnings': warnings}
    key_specs = [(customers, 'customer_id', 'customers'), (products, 'product_id', 'products'), (transactions, 'transaction_id', 'transactions'), (inventory, 'inventory_record_id', 'inventory'), (campaigns, 'campaign_id', 'campaigns')]
    for df, col, name in key_specs:
        dup = int(df[col].duplicated().sum())
        nulls = int(df[col].isna().sum())
        if dup:
            errors.append(f'{name}.{col}: {dup} duplicate primary identifiers')
        if nulls:
            errors.append(f'{name}.{col}: {nulls} missing primary identifiers')
    hard_checks = [(transactions['quantity'] <= 0, 'transactions.quantity must be > 0'), (transactions['unit_price'] < 0, 'transactions.unit_price must be >= 0'), ((transactions['discount_pct'] < 0) | (transactions['discount_pct'] > 1), 'transactions.discount_pct must be between 0 and 1'), (products['unit_cost'] < 0, 'products.unit_cost must be >= 0'), (products['list_price'] < 0, 'products.list_price must be >= 0'), (inventory['stock_on_hand'] < 0, 'inventory.stock_on_hand must be >= 0'), (inventory['reorder_threshold'] < 0, 'inventory.reorder_threshold must be >= 0'), (inventory['supplier_delay_days'] < 0, 'inventory.supplier_delay_days must be >= 0'), (campaigns['spend'] < 0, 'campaigns.spend must be >= 0'), (campaigns['impressions'] < 0, 'campaigns.impressions must be >= 0'), (campaigns['clicks'] < 0, 'campaigns.clicks must be >= 0'), (campaigns['conversions'] < 0, 'campaigns.conversions must be >= 0')]
    for mask, message in hard_checks:
        count = int(mask.fillna(False).sum())
        if count:
            errors.append(f'{message} ({count} rows violate this)')
    unknown_status = sorted(set(transactions['status'].dropna().astype(str)) - ALLOWED_STATUSES)
    if unknown_status:
        errors.append(f'transactions.status contains unsupported values: {unknown_status}')
    if not set(transactions['customer_id']).issubset(set(customers['customer_id'])):
        errors.append('transactions contains customer_id values not present in customers')
    if not set(transactions['product_id']).issubset(set(products['product_id'])):
        errors.append('transactions contains product_id values not present in products')
    if not set(inventory['product_id']).issubset(set(products['product_id'])):
        errors.append('inventory contains product_id values not present in products')
    invalid_clicks = int((campaigns['clicks'] > campaigns['impressions']).sum())
    invalid_conversions = int((campaigns['conversions'] > campaigns['clicks']).sum())
    stockout_above = int(((inventory['stockout_flag'] == 1) & (inventory['stock_on_hand'] > inventory['reorder_threshold'])).sum())
    zero_unflagged = int(((inventory['stock_on_hand'] == 0) & (inventory['stockout_flag'] == 0)).sum())
    prices_below_cost = int((products['list_price'] < products['unit_cost']).sum())
    if invalid_clicks:
        warnings.append(f'{invalid_clicks} campaign rows have clicks greater than impressions')
    if invalid_conversions:
        warnings.append(f'{invalid_conversions} campaign rows have conversions greater than clicks')
    if stockout_above:
        warnings.append(f'{stockout_above} inventory rows are stockout-flagged while stock exceeds reorder threshold')
    if zero_unflagged:
        warnings.append(f'{zero_unflagged} inventory rows have zero stock but are not stockout-flagged')
    if prices_below_cost:
        warnings.append(f'{prices_below_cost} products have list_price below unit_cost; supplied synthetic prices/costs require verification')
    return {'valid': not errors, 'errors': errors, 'warnings': warnings, 'warning_count': len(warnings), 'row_counts': {name: int(len(df)) for name, df in frames.items()}}

def _fit_iforest(X: pd.DataFrame, *, contamination: float=0.1, seed: int=42, n_estimators: int=300):
    model = IsolationForest(n_estimators=n_estimators, contamination=contamination, random_state=seed, n_jobs=-1)
    labels = model.fit_predict(X)
    decision = model.decision_function(X)
    anomaly = -decision
    lo, hi = (float(anomaly.min()), float(anomaly.max()))
    score = np.zeros_like(anomaly, dtype=float) if hi == lo else (anomaly - lo) / (hi - lo) * 100
    return (model, labels, decision, score)

def _stability_diagnostics(X: pd.DataFrame, base_score: np.ndarray, base_labels: np.ndarray) -> dict[str, Any]:
    base_top10 = set(np.argsort(-base_score)[:10].tolist())
    base_anoms = set(np.where(base_labels == -1)[0].tolist())
    seed_overlaps = []
    anomaly_jaccards = []
    for seed in [7, 42, 99]:
        _, labels, _, score = _fit_iforest(X, contamination=0.1, seed=seed, n_estimators=100)
        top10 = set(np.argsort(-score)[:10].tolist())
        anoms = set(np.where(labels == -1)[0].tolist())
        seed_overlaps.append(len(base_top10 & top10) / 10)
        union = base_anoms | anoms
        anomaly_jaccards.append(len(base_anoms & anoms) / len(union) if union else 1.0)
    contamination_results = {}
    for contamination in [0.05, 0.1, 0.15]:
        if contamination == 0.1:
            labels, score = (base_labels, base_score)
        else:
            _, labels, _, score = _fit_iforest(X, contamination=contamination, seed=42, n_estimators=100)
        top10 = set(np.argsort(-score)[:10].tolist())
        contamination_results[f'{int(contamination * 100)}%'] = {'flagged_products': int((labels == -1).sum()), 'top10_overlap_with_10pct': float(len(base_top10 & top10) / 10)}
    return {'seed_top10_overlap_mean': float(np.mean(seed_overlaps)), 'seed_top10_overlap_min': float(np.min(seed_overlaps)), 'seed_anomaly_set_jaccard_mean': float(np.mean(anomaly_jaccards)), 'contamination_sensitivity': contamination_results, 'interpretation': 'These are stability diagnostics for an unsupervised ranking; they are not accuracy metrics. Higher overlap means the highest-priority anomaly candidates are less sensitive to random seed or contamination choice.'}

def analyze_business_data(customers, products, transactions, inventory, campaigns):
    validation = validate_data(customers, products, transactions, inventory, campaigns)
    if not validation['valid']:
        raise ValueError('; '.join(validation['errors']))
    customers = customers.copy()
    products = products.copy()
    transactions = transactions.copy()
    inventory = inventory.copy()
    campaigns = campaigns.copy()
    source_frames = {'customers': customers, 'products': products, 'transactions': transactions, 'inventory': inventory, 'campaigns': campaigns}
    dataset_hash = _stable_dataset_hash(source_frames)
    products['price_below_cost'] = products['list_price'] < products['unit_cost']
    tx = transactions.merge(customers, on='customer_id', how='left', validate='many_to_one').merge(products, on='product_id', how='left', validate='many_to_one')
    if len(tx) != len(transactions):
        raise ValueError('Transaction row count changed after joins.')
    if tx[['region', 'customer_segment', 'category', 'unit_cost']].isna().any().any():
        raise ValueError('Unmatched customer or product foreign keys detected.')
    tx['revenue'] = tx['quantity'] * tx['unit_price'] * (1 - tx['discount_pct'])
    tx['estimated_cost'] = tx['quantity'] * tx['unit_cost']
    tx['estimated_margin'] = tx['revenue'] - tx['estimated_cost']
    tx['negative_margin'] = (tx['estimated_margin'] < 0).astype(int)
    tx['negative_margin_exposure'] = (-tx['estimated_margin']).clip(lower=0)
    tx['failed_transaction'] = tx['status'].isin(['Cancelled', 'Returned']).astype(int)
    tx['failed_value'] = np.where(tx['failed_transaction'] == 1, tx['revenue'], 0.0)
    cancelled_value = tx.loc[tx['status'] == 'Cancelled', 'revenue'].sum()
    returned_value = tx.loc[tx['status'] == 'Returned', 'revenue'].sum()
    combined_exposure = cancelled_value + returned_value
    non_pending_value = tx.loc[tx['status'] != 'Pending', 'revenue'].sum()
    exposure_pct = combined_exposure / non_pending_value * 100 if non_pending_value else 0.0
    status_order = ['Completed', 'Cancelled', 'Returned', 'Pending']
    status_distribution: dict[str, Any] = {}
    total_transactions = len(tx)
    for status in status_order:
        mask = tx['status'] == status
        count = int(mask.sum())
        status_distribution[status] = {'count': count, 'pct': float(count / total_transactions * 100) if total_transactions else 0.0, 'value': float(tx.loc[mask, 'revenue'].sum())}
    discount_margin = tx.groupby('discount_pct').agg(orders=('transaction_id', 'count'), negative_margin_rate=('negative_margin', 'mean'), avg_margin=('estimated_margin', 'mean')).reset_index().sort_values('discount_pct')
    discount_margin['negative_margin_rate'] *= 100
    discount_margin_bands = [{'band': f'{row.discount_pct * 100:g}%', 'orders': int(row.orders), 'negative_margin_rate': float(row.negative_margin_rate), 'avg_discount': float(row.discount_pct * 100), 'avg_margin': float(row.avg_margin)} for row in discount_margin.itertuples(index=False)]
    transactions_summary = {'total_transactions': int(total_transactions), 'status_distribution': status_distribution, 'discount_margin_bands': discount_margin_bands}
    campaigns['invalid_clicks'] = campaigns['clicks'] > campaigns['impressions']
    campaigns['invalid_conversions'] = campaigns['conversions'] > campaigns['clicks']
    campaigns['campaign_invalid'] = campaigns['invalid_clicks'] | campaigns['invalid_conversions']
    inventory['stockout_above_threshold'] = (inventory['stockout_flag'] == 1) & (inventory['stock_on_hand'] > inventory['reorder_threshold'])
    inventory['zero_stock_not_flagged'] = (inventory['stock_on_hand'] == 0) & (inventory['stockout_flag'] == 0)
    product_tx = tx.groupby('product_id').agg(transaction_count=('transaction_id', 'count'), avg_order_value=('revenue', 'mean'), total_transaction_value=('revenue', 'sum'), failed_transaction_value=('failed_value', 'sum'), negative_margin_exposure=('negative_margin_exposure', 'sum'), avg_discount=('discount_pct', 'mean'), cancel_rate=('status', lambda x: (x == 'Cancelled').mean()), return_rate=('status', lambda x: (x == 'Returned').mean()), failure_rate=('failed_transaction', 'mean'), negative_margin_rate=('negative_margin', 'mean'), avg_margin=('estimated_margin', 'mean')).reset_index()
    product_inventory = inventory.groupby('product_id').agg(avg_stock_on_hand=('stock_on_hand', 'mean'), avg_reorder_threshold=('reorder_threshold', 'mean'), stockout_rate=('stockout_flag', 'mean'), avg_supplier_delay=('supplier_delay_days', 'mean'), stockout_inconsistency_rate=('stockout_above_threshold', 'mean')).reset_index()
    product_risk = products.merge(product_tx, on='product_id', how='left', validate='one_to_one').merge(product_inventory, on='product_id', how='left', validate='one_to_one')
    product_risk['base_price_margin'] = product_risk['list_price'] - product_risk['unit_cost']
    product_risk['base_margin_pct'] = np.where(product_risk['unit_cost'] != 0, product_risk['base_price_margin'] / product_risk['unit_cost'], np.nan)
    X = product_risk[ML_FEATURES].replace([np.inf, -np.inf], np.nan).copy()
    for col in X.columns:
        med = X[col].median()
        X[col] = X[col].fillna(0.0 if pd.isna(med) else med)
    model, labels, decision, anomaly_score = _fit_iforest(X, contamination=0.1, seed=42)
    product_risk['anomaly_label'] = labels
    product_risk['is_anomaly'] = labels == -1
    product_risk['raw_anomaly_score'] = decision
    product_risk['anomaly_score'] = anomaly_score
    operational_signal = 0.4 * _minmax(product_risk['stockout_rate']) + 0.3 * _minmax(product_risk['avg_supplier_delay']) + 0.3 * _minmax(product_risk['stockout_inconsistency_rate'])
    raw_priority = 0.3 * (product_risk['anomaly_score'] / 100.0) + 0.2 * _minmax(product_risk['total_transaction_value']) + 0.25 * _minmax(product_risk['negative_margin_exposure']) + 0.15 * _minmax(product_risk['failed_transaction_value']) + 0.1 * operational_signal
    product_risk['priority_score'] = _minmax(raw_priority) * 100
    product_risk['risk_score'] = product_risk['priority_score']
    product_risk['priority_level'] = pd.cut(product_risk['priority_score'], bins=[-1, 40, 70, 101], labels=['Low', 'Medium', 'High'], include_lowest=True).astype(str)
    product_risk['risk_level'] = product_risk['priority_level']
    medians = X.median()
    q1 = X.quantile(0.25)
    q3 = X.quantile(0.75)
    iqr = (q3 - q1).replace(0, np.nan)

    def deviation_payload(row: pd.Series) -> list[dict[str, Any]]:
        deviations = []
        for feature in ML_FEATURES:
            value = float(row[feature]) if pd.notna(row[feature]) else None
            median = float(medians[feature]) if pd.notna(medians[feature]) else None
            scale = iqr[feature]
            if value is None or median is None:
                continue
            if pd.isna(scale) or float(scale) == 0:
                magnitude = 0.0
            else:
                magnitude = abs(value - median) / float(scale)
            deviations.append({'feature': feature, 'label': FEATURE_LABELS[feature], 'value': value, 'catalog_median': median, 'direction': 'above' if value > median else 'below' if value < median else 'at', 'iqr_deviation': float(magnitude)})
        return sorted(deviations, key=lambda d: d['iqr_deviation'], reverse=True)[:5]
    product_risk['top_deviations'] = product_risk.apply(deviation_payload, axis=1)
    q75_neg = product_risk['negative_margin_rate'].quantile(0.75)
    q75_fail = product_risk['failure_rate'].quantile(0.75)
    q75_disc = product_risk['avg_discount'].quantile(0.75)
    q75_stock = product_risk['stockout_rate'].quantile(0.75)
    q75_delay = product_risk['avg_supplier_delay'].quantile(0.75)
    q25_margin = product_risk['base_margin_pct'].quantile(0.25)

    def explain(row):
        reasons = []
        if row['negative_margin_rate'] > q75_neg:
            reasons.append('high apparent negative-margin rate')
        if row['failure_rate'] > q75_fail:
            reasons.append('high cancelled/returned rate')
        if row['avg_discount'] > q75_disc:
            reasons.append('high average discount')
        if row['stockout_rate'] > q75_stock:
            reasons.append('high stockout flag rate')
        if row['avg_supplier_delay'] > q75_delay:
            reasons.append('high supplier delay')
        if row['base_margin_pct'] < q25_margin:
            reasons.append('weak supplied price-cost margin')
        if not reasons:
            reasons = [d['label'] for d in row['top_deviations'][:3]]
        return '; '.join(reasons)

    def action(row):
        actions = []
        if row['negative_margin_rate'] > 0.5:
            actions.append('review pricing and discount rules')
        if row['failure_rate'] > 0.2:
            actions.append('investigate cancellations and returns')
        if row['stockout_rate'] > 0.25:
            actions.append('review inventory policy')
        if row['avg_supplier_delay'] > q75_delay:
            actions.append('review supplier reliability')
        if row['base_margin_pct'] < 0:
            actions.append('verify product cost and list price')
        return '; '.join(actions) if actions else "investigate the product's strongest catalog-relative deviations"
    product_risk['why_flagged'] = product_risk.apply(explain, axis=1)
    product_risk['recommended_action'] = product_risk.apply(action, axis=1)
    product_risk['model_interpretation_note'] = 'Top deviations are catalog-relative business indicators, not causal SHAP-style attribution.'
    product_risk = product_risk.sort_values(['priority_score', 'anomaly_score'], ascending=False).reset_index(drop=True)
    category_summary = tx.groupby('category').agg(transaction_count=('transaction_id', 'count'), failure_rate=('failed_transaction', 'mean'), negative_margin_rate=('negative_margin', 'mean'), avg_margin=('estimated_margin', 'mean')).reset_index()
    failed_values = tx.loc[tx['failed_transaction'] == 1].groupby('category')['revenue'].sum().rename('failed_transaction_value').reset_index()
    categories = category_summary.merge(failed_values, on='category', how='left')
    categories['failed_transaction_value'] = categories['failed_transaction_value'].fillna(0.0)
    categories['failure_rate'] *= 100
    categories['negative_margin_rate'] *= 100
    campaign_issues = campaigns.loc[campaigns['campaign_invalid']].copy()
    inventory_issues = inventory.loc[inventory['stockout_above_threshold'] | inventory['zero_stock_not_flagged']].copy()
    clean_campaigns = campaigns.loc[~campaigns['campaign_invalid']]
    clicks_only = int((campaigns['invalid_clicks'] & ~campaigns['invalid_conversions']).sum())
    conversions_only = int((~campaigns['invalid_clicks'] & campaigns['invalid_conversions']).sum())
    overlap = int((campaigns['invalid_clicks'] & campaigns['invalid_conversions']).sum())

    def safe_ratio(num, den):
        return float(num / den * 100) if den else 0.0
    campaign_summary = {'total_campaigns': int(len(campaigns)), 'invalid_rows': int(campaigns['campaign_invalid'].sum()), 'clean_rows': int((~campaigns['campaign_invalid']).sum()), 'clicks_only_rows': clicks_only, 'conversions_only_rows': conversions_only, 'overlap_rows': overlap, 'trusted_ctr_pct': safe_ratio(clean_campaigns['clicks'].sum(), clean_campaigns['impressions'].sum()), 'trusted_cvr_pct': safe_ratio(clean_campaigns['conversions'].sum(), clean_campaigns['clicks'].sum()), 'raw_ctr_pct': safe_ratio(campaigns['clicks'].sum(), campaigns['impressions'].sum()), 'raw_cvr_pct': safe_ratio(campaigns['conversions'].sum(), campaigns['clicks'].sum())}
    inv_with_category = inventory.merge(products[['product_id', 'category', 'supplier_lead_days']], on='product_id', how='left', validate='many_to_one')
    supplier_by_category = inv_with_category.groupby('category').agg(avg_supplier_delay=('supplier_delay_days', 'mean'), avg_supplier_lead_days=('supplier_lead_days', 'mean')).reset_index().to_dict(orient='records')
    inventory_summary = {'total_records': int(len(inventory)), 'total_stockout_flags': int(inventory['stockout_flag'].sum()), 'stockout_above_threshold': int(inventory['stockout_above_threshold'].sum()), 'zero_stock_not_flagged': int(inventory['zero_stock_not_flagged'].sum()), 'other_records': int(len(inventory) - len(inventory_issues)), 'supplier_by_category': supplier_by_category}
    diagnostics = _stability_diagnostics(X, anomaly_score, labels)
    diagnostics.update({'flagged_anomalies': int((labels == -1).sum()), 'high_priority_products': int((product_risk['priority_level'] == 'High').sum()), 'model_feature_count': len(ML_FEATURES), 'model_feature_redundancy_note': 'failure_rate is displayed but excluded from ML because it equals cancel_rate + return_rate'})
    overview = {'total_transaction_value': float(tx['revenue'].sum()), 'cancelled_value': float(cancelled_value), 'returned_value': float(returned_value), 'combined_exposure': float(combined_exposure), 'exposure_pct': float(exposure_pct), 'negative_margin_rate': float(tx['negative_margin'].mean() * 100), 'cancelled_returned_rate': float(tx['failed_transaction'].mean() * 100), 'invalid_campaign_rows': int(campaigns['campaign_invalid'].sum()), 'invalid_click_rows': int(campaigns['invalid_clicks'].sum()), 'invalid_conversion_rows': int(campaigns['invalid_conversions'].sum()), 'total_stockout_flags': int(inventory['stockout_flag'].sum()), 'stockout_above_threshold': int(inventory['stockout_above_threshold'].sum()), 'zero_stock_not_flagged': int(inventory['zero_stock_not_flagged'].sum()), 'high_priority_product_count': int((product_risk['priority_level'] == 'High').sum()), 'high_risk_product_count': int((product_risk['priority_level'] == 'High').sum()), 'anomaly_count': int(product_risk['is_anomaly'].sum())}
    metadata = {'model': 'IsolationForest', 'training_mode': 'retrain_on_each_analysis', 'trained_at_utc': datetime.now(timezone.utc).isoformat(), 'dataset_hash': dataset_hash, 'n_estimators': 300, 'contamination': 0.1, 'product_count': int(len(product_risk)), 'ml_feature_count': len(ML_FEATURES), 'ml_features': ML_FEATURES, 'source_row_counts': validation['row_counts'], 'priority_score_formula': {'anomaly_score': 0.3, 'transaction_value': 0.2, 'negative_margin_exposure': 0.25, 'failed_transaction_value': 0.15, 'operational_signal': 0.1}, 'semantics': {'anomaly_score': 'Relative Isolation Forest anomaly score, 0-100; not probability of loss.', 'is_anomaly': 'Isolation Forest label using 10% contamination.', 'priority_score': 'Decision-support ranking combining anomaly strength with business impact.', 'priority_level': 'Presentation bucket derived from priority_score; not an ML class label.'}}
    return AnalysisResult(overview=overview, transactions_summary=transactions_summary, product_risk=product_risk, categories=categories, campaign_issues=campaign_issues, inventory_issues=inventory_issues, campaign_summary=campaign_summary, inventory_summary=inventory_summary, metadata=metadata, diagnostics=diagnostics, validation=validation)
