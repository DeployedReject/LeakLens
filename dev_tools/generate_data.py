from pathlib import Path
import numpy as np
import pandas as pd

def generate_datasets(target_dir: Path):
    target_dir.mkdir(parents=True, exist_ok=True)
    np.random.seed(42)
    categories = ['Beauty', 'Electronics', 'Apparel', 'Sports', 'Home & Kitchen', 'Grocery']
    cat_weights = [0.22, 0.22, 0.2, 0.14, 0.12, 0.1]
    regions = ['North', 'South', 'East', 'West', 'Central']
    segments = ['Consumer', 'Corporate', 'Small Business']
    channels = ['Mobile App', 'Website', 'Social Store', 'Partner API']
    customers_list = [{'customer_id': f'C{i:05d}', 'region': str(np.random.choice(regions)), 'customer_segment': str(np.random.choice(segments)), 'signup_date': f'2025-{np.random.randint(1, 13):02d}-{np.random.randint(1, 29):02d}', 'preferred_channel': str(np.random.choice(channels))} for i in range(1, 1501)]
    df_customers = pd.DataFrame(customers_list)
    df_customers.to_csv(target_dir / 'customers.csv', index=False)
    products_list = [{'product_id': 'PR0001', 'category': 'Sports', 'unit_cost': 66.56, 'list_price': 251.83, 'supplier_lead_days': 12}]
    for i in range(2, 251):
        pid = f'PR{i:04d}'
        cat = str(np.random.choice(categories, p=cat_weights))
        if cat == 'Beauty':
            list_p = round(float(np.random.uniform(300.0, 1600.0)), 2)
            cost = round(list_p * float(np.random.choice([0.45, 0.95, 1.25], p=[0.4, 0.2, 0.4])), 2)
        else:
            list_p = round(float(np.random.uniform(350.0, 2800.0)), 2)
            cost = round(list_p * float(np.random.choice([0.4, 0.6, 1.1], p=[0.55, 0.2, 0.25])), 2)
        products_list.append({'product_id': pid, 'category': cat, 'unit_cost': cost, 'list_price': list_p, 'supplier_lead_days': int(np.random.randint(4, 16))})
    df_products = pd.DataFrame(products_list)
    n_total = 18000
    statuses = ['Completed'] * 13962 + ['Cancelled'] * 1689 + ['Returned'] * 1431 + ['Pending'] * 918
    np.random.shuffle(statuses)
    tx_customers = np.random.choice(df_customers['customer_id'], size=n_total)
    prod_pool_beauty = df_products[df_products['category'] == 'Beauty']['product_id'].values
    prod_pool_other = df_products[df_products['category'] != 'Beauty']['product_id'].values
    tx_products = ['PR0001'] * 69 + list(np.random.choice(prod_pool_beauty, size=2784))
    remaining = n_total - len(tx_products)
    tx_products += list(np.random.choice(prod_pool_other, size=remaining))
    np.random.shuffle(tx_products)
    txns = []
    prod_map = df_products.set_index('product_id').to_dict(orient='index')
    for i in range(n_total):
        pid = tx_products[i]
        st = statuses[i]
        p_row = prod_map[pid]
        qty = 1
        unit_p = p_row['list_price']
        disc = float(np.random.choice([0.0, 0.05, 0.1, 0.15, 0.25, 0.35], p=[0.3, 0.2, 0.2, 0.15, 0.1, 0.05]))
        txns.append({'transaction_id': f'TX{i + 1:06d}', 'customer_id': tx_customers[i], 'product_id': pid, 'timestamp': f'2026-01-{np.random.randint(1, 29):02d} {np.random.randint(0, 24):02d}:{np.random.randint(0, 60):02d}:00', 'quantity': qty, 'unit_price': unit_p, 'discount_pct': disc, 'status': st, 'channel': str(np.random.choice(channels)), 'payment_method': str(np.random.choice(['Credit Card', 'UPI', 'Debit Card', 'Net Banking']))})
    df_txns = pd.DataFrame(txns)
    canc_mask = df_txns['status'] == 'Cancelled'
    canc_rev = (df_txns.loc[canc_mask, 'unit_price'] * (1 - df_txns.loc[canc_mask, 'discount_pct'])).sum()
    df_txns.loc[canc_mask, 'unit_price'] *= 861849.61 / canc_rev
    ret_mask = df_txns['status'] == 'Returned'
    ret_rev = (df_txns.loc[ret_mask, 'unit_price'] * (1 - df_txns.loc[ret_mask, 'discount_pct'])).sum()
    df_txns.loc[ret_mask, 'unit_price'] *= 760322.3 / ret_rev
    other_mask = ~df_txns['status'].isin(['Cancelled', 'Returned'])
    other_rev = (df_txns.loc[other_mask, 'unit_price'] * (1 - df_txns.loc[other_mask, 'discount_pct'])).sum()
    target_other = 9390803.1 - (861849.61 + 760322.3)
    df_txns.loc[other_mask, 'unit_price'] *= target_other / other_rev
    df_txns['unit_price'] = df_txns['unit_price'].round(2)
    tx_merged = df_txns.merge(df_products[['product_id', 'category']], on='product_id')
    tx_merged['net_price'] = df_txns['unit_price'] * (1 - df_txns['discount_pct'])
    avg_net_per_prod = tx_merged.groupby('product_id')['net_price'].mean()
    for pid in df_products['product_id']:
        if pid == 'PR0001':
            df_products.loc[df_products['product_id'] == pid, 'unit_cost'] = 66.56
            continue
        cat = df_products.loc[df_products['product_id'] == pid, 'category'].values[0]
        base_net = avg_net_per_prod.get(pid, 500.0)
        prob_neg = 0.552 if cat == 'Beauty' else 0.315
        if np.random.rand() < prob_neg:
            df_products.loc[df_products['product_id'] == pid, 'unit_cost'] = round(base_net * float(np.random.uniform(1.1, 1.45)), 2)
        else:
            df_products.loc[df_products['product_id'] == pid, 'unit_cost'] = round(base_net * float(np.random.uniform(0.55, 0.88)), 2)
    df_products.to_csv(target_dir / 'products.csv', index=False)
    df_txns.to_csv(target_dir / 'transactions.csv', index=False)
    inv_records = []
    rec_id = 1
    for pid in df_products['product_id']:
        for d in range(1, 51):
            inv_records.append({'inventory_record_id': f'INV{rec_id:06d}', 'product_id': pid, 'date': f'2026-02-{min(d, 28):02d}', 'stock_on_hand': int(np.random.randint(25, 95)), 'reorder_threshold': 25, 'stockout_flag': 0, 'supplier_delay_days': round(float(np.random.exponential(2.5)), 1)})
            rec_id += 1
    for i in range(648):
        inv_records[i]['stockout_flag'] = 1
        inv_records[i]['stock_on_hand'] = inv_records[i]['reorder_threshold'] + np.random.randint(15, 65)
    for i in range(648, 760):
        inv_records[i]['stockout_flag'] = 1
        inv_records[i]['stock_on_hand'] = 0
    for i in range(760, 770):
        inv_records[i]['stockout_flag'] = 0
        inv_records[i]['stock_on_hand'] = 0
    df_inv = pd.DataFrame(inv_records)
    df_inv.to_csv(target_dir / 'inventory.csv', index=False)
    camp_records = []
    for i in range(1, 501):
        imp = int(np.random.randint(15000, 200000))
        clk = max(10, int(imp * np.random.uniform(0.015, 0.045)))
        cnv = max(1, int(clk * np.random.uniform(0.02, 0.07)))
        camp_records.append({'campaign_id': f'CMP{i:04d}', 'date': f'2026-01-{np.random.randint(1, 29):02d}', 'channel': str(np.random.choice(['Google Ads', 'Meta Ads', 'Email Retargeting', 'Affiliate', 'Influencer'])), 'category': str(np.random.choice(categories)), 'spend': round(float(np.random.uniform(5000.0, 85000.0)), 2), 'impressions': imp, 'clicks': clk, 'conversions': cnv})
    for i in range(84):
        camp_records[i]['clicks'] = camp_records[i]['impressions'] + np.random.randint(50, 500)
    for i in range(83, 83 + 88):
        camp_records[i]['conversions'] = camp_records[i]['clicks'] + np.random.randint(20, 200)
    df_camp = pd.DataFrame(camp_records)
    df_camp.to_csv(target_dir / 'campaigns.csv', index=False)
    print('Calibrated datasets saved successfully!')
if __name__ == '__main__':
    out_dir = Path(__file__).resolve().parent / 'data'
    generate_datasets(out_dir)
