import os
from typing import Any, Dict, List, Optional
import requests
API_BASE_URL = os.environ.get('LEAKLENS_API_URL', 'http://localhost:8000')

class APIClientError(RuntimeError):
    pass

def _get(path: str, *, params=None, timeout: float=5.0):
    try:
        resp = requests.get(f'{API_BASE_URL}{path}', params=params, timeout=timeout)
        resp.raise_for_status()
        return resp.json()
    except requests.RequestException as exc:
        raise APIClientError(f'LeakLens backend request failed for {path}: {exc}') from exc

def check_backend_health() -> Dict[str, Any]:
    try:
        return _get('/health', timeout=2.5)
    except APIClientError as exc:
        return {'status': 'offline', 'error': str(exc)}

def fetch_overview() -> Dict[str, Any]:
    return _get('/overview', timeout=4.0)

def fetch_transactions_summary() -> Dict[str, Any]:
    return _get('/transactions/summary', timeout=4.0)

def fetch_products_risk(category: Optional[str]=None, risk_level: Optional[str]=None, limit: int=250, anomaly_only: bool=False, sort_by: str='priority') -> List[Dict[str, Any]]:
    params = {'limit': limit, 'anomaly_only': anomaly_only, 'sort_by': sort_by}
    if category and category != 'All':
        params['category'] = category
    if risk_level and risk_level != 'All':
        params['risk_level'] = risk_level
    return _get('/products/risk', params=params, timeout=5.0)

def fetch_product_detail(product_id: str) -> Dict[str, Any]:
    return _get(f'/products/{product_id}', timeout=4.0)

def fetch_categories() -> List[Dict[str, Any]]:
    return _get('/categories', timeout=4.0)

def fetch_metadata() -> Dict[str, Any]:
    return _get('/metadata', timeout=4.0)

def fetch_model_diagnostics() -> Dict[str, Any]:
    return _get('/diagnostics/model', timeout=5.0)

def fetch_validation_report() -> Dict[str, Any]:
    return _get('/validation', timeout=4.0)

def fetch_campaign_quality() -> Dict[str, Any]:
    return _get('/quality/campaigns', timeout=4.0)

def fetch_inventory_quality() -> Dict[str, Any]:
    return _get('/quality/inventory', timeout=4.0)

def post_analyze_datasets(customers_file, products_file, transactions_file, inventory_file, campaigns_file) -> Dict[str, Any]:

    def get_data(f):
        if hasattr(f, 'getvalue'):
            return f.getvalue()
        if hasattr(f, 'read'):
            f.seek(0)
            return f.read()
        return bytes(f)
    files = {'customers': ('customers.csv', get_data(customers_file), 'text/csv'), 'products': ('products.csv', get_data(products_file), 'text/csv'), 'transactions': ('transactions.csv', get_data(transactions_file), 'text/csv'), 'inventory': ('inventory.csv', get_data(inventory_file), 'text/csv'), 'campaigns': ('campaigns.csv', get_data(campaigns_file), 'text/csv')}
    try:
        resp = requests.post(f'{API_BASE_URL}/analyze', files=files, timeout=90.0)
        resp.raise_for_status()
        return resp.json()
    except requests.RequestException as exc:
        detail = ''
        if getattr(exc, 'response', None) is not None:
            try:
                detail = f" - {exc.response.json().get('detail', exc.response.text)}"
            except Exception:
                detail = f' - {exc.response.text}'
        raise APIClientError(f'Analysis request failed{detail}') from exc
