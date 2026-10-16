from pathlib import Path
import sys
from fastapi.testclient import TestClient
ROOT = Path(__file__).resolve().parents[1]
BACKEND = ROOT / 'backend'
sys.path.insert(0, str(BACKEND))
import app as backend_app

def client_with_state():
    backend_app._current = backend_app.load_local()
    return TestClient(backend_app.app)

def test_health_and_core_endpoints():
    client = client_with_state()
    health = client.get('/health')
    assert health.status_code == 200
    body = health.json()
    assert body['analysis_loaded'] is True
    assert body['product_count'] == 250
    assert body['dataset_hash']
    assert client.get('/overview').status_code == 200
    assert client.get('/transactions/summary').json()['total_transactions'] == 18000
    assert client.get('/diagnostics/model').json()['flagged_anomalies'] == 25
    assert client.get('/validation').json()['valid'] is True

def test_product_filters_and_404():
    client = client_with_state()
    rows = client.get('/products/risk', params={'limit': 5, 'sort_by': 'priority'})
    assert rows.status_code == 200
    assert len(rows.json()) == 5
    assert 'priority_score' in rows.json()[0]
    assert 'anomaly_score' in rows.json()[0]
    anomalies = client.get('/products/risk', params={'anomaly_only': True})
    assert anomalies.status_code == 200
    assert len(anomalies.json()) == 25
    assert all((row['is_anomaly'] for row in anomalies.json()))
    assert client.get('/products/NOTREAL').status_code == 404
    assert client.get('/products/risk', params={'sort_by': 'nonsense'}).status_code == 400

def test_upload_validation_failure_does_not_replace_good_state():
    client = client_with_state()
    before_hash = client.get('/health').json()['dataset_hash']
    d = BACKEND / 'data'
    with open(d / 'customers.csv', 'rb') as c, open(d / 'products.csv', 'rb') as p, open(d / 'inventory.csv', 'rb') as i, open(d / 'campaigns.csv', 'rb') as m:
        bad_tx = (d / 'products.csv').read_bytes()
        files = {'customers': ('customers.csv', c, 'text/csv'), 'products': ('products.csv', p, 'text/csv'), 'transactions': ('transactions.csv', bad_tx, 'text/csv'), 'inventory': ('inventory.csv', i, 'text/csv'), 'campaigns': ('campaigns.csv', m, 'text/csv')}
        response = client.post('/analyze', files=files)
    assert response.status_code == 400
    after_hash = client.get('/health').json()['dataset_hash']
    assert after_hash == before_hash
