
import requests
import json

URL = 'http://localhost:8069'
DB = 'odoo'
USER = 'admin'
PASS = 'admin' # Default Odoo admin password, hopefully correct

def test_api():
    session = requests.Session()
    
    # 1. Authenticate
    login_url = f"{URL}/web/session/authenticate"
    payload = {
        "jsonrpc": "2.0",
        "params": {
            "db": DB,
            "login": USER,
            "password": PASS
        }
    }
    response = session.post(login_url, json=payload)
    res_json = response.json()
    if 'error' in res_json:
        print(f"Login failed: {res_json['error']}")
        return
    
    print("Login successful.")
    
    # 2. Test Balance Sheet
    print("\nTesting Balance Sheet API...")
    bs_url = f"{URL}/api/reports/balance_sheet"
    payload = {
        "jsonrpc": "2.0",
        "params": {
            "date": "2026-04-30"
        }
    }
    response = session.post(bs_url, json=payload)
    print(f"Status: {response.status_code}")
    print(f"Response: {json.dumps(response.json(), indent=2)[:500]}...")

    # 3. Test Day Book
    print("\nTesting Day Book API...")
    db_url = f"{URL}/api/reports/day_book"
    payload = {
        "jsonrpc": "2.0",
        "params": {
            "date": "2026-04-30"
        }
    }
    response = session.post(db_url, json=payload)
    print(f"Status: {response.status_code}")
    print(f"Response: {json.dumps(response.json(), indent=2)[:500]}...")

if __name__ == "__main__":
    test_api()
