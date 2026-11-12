import urllib.request
import urllib.error
import json

BASE = 'http://127.0.0.1:8000/api/v1'

def run_tests():
    print("=== Running Negative Scenarios against Live API ===")

    # 1. Non-existent portfolio (404)
    try:
        urllib.request.urlopen(f'{BASE}/portfolios/PORT-DOESNOTEXIST/valuation?as_of_date=2026-01-15')
        print('FAIL 1: Expected 404 for non-existent portfolio')
    except urllib.error.HTTPError as e:
        print(f'PASS 1: Non-existent portfolio returned HTTP {e.code}')

    # 2. Unauthenticated approval (401)
    try:
        req = urllib.request.Request(
            f'{BASE}/proposals/RB-2026-000017/approve',
            data=b'{}',
            headers={'Content-Type': 'application/json'},
            method='POST'
        )
        urllib.request.urlopen(req)
        print('FAIL 2: Expected 401 for unauthenticated request')
    except urllib.error.HTTPError as e:
        print(f'PASS 2: Unauthenticated request returned HTTP {e.code}')

    # 3. Unauthorized role (VIEWER attempting approval - 403)
    try:
        req = urllib.request.Request(
            f'{BASE}/proposals/RB-2026-000017/approve',
            data=json.dumps({'reason': 'ok'}).encode(),
            headers={'Content-Type': 'application/json', 'Authorization': 'Bearer dev-viewer-token'},
            method='POST'
        )
        urllib.request.urlopen(req)
        print('FAIL 3: Expected 403 for viewer approval')
    except urllib.error.HTTPError as e:
        print(f'PASS 3: Viewer approval returned HTTP {e.code}')

    # 4. Approving rejected proposal (422)
    try:
        req = urllib.request.Request(
            f'{BASE}/proposals/RB-2026-000017/approve',
            data=json.dumps({'reason': 'ok'}).encode(),
            headers={'Content-Type': 'application/json', 'Authorization': 'Bearer dev-reviewer-token'},
            method='POST'
        )
        urllib.request.urlopen(req)
        print('FAIL 4: Expected 422 for approving rejected proposal')
    except urllib.error.HTTPError as e:
        print(f'PASS 4: Approving rejected proposal returned HTTP {e.code}')

    # 5. Empty rejection reason (422)
    try:
        req = urllib.request.Request(
            f'{BASE}/proposals/RB-2026-000017/reject',
            data=json.dumps({'reason': ''}).encode(),
            headers={'Content-Type': 'application/json', 'Authorization': 'Bearer dev-reviewer-token'},
            method='POST'
        )
        urllib.request.urlopen(req)
        print('FAIL 5: Expected 422 for empty rejection reason')
    except urllib.error.HTTPError as e:
        print(f'PASS 5: Empty rejection reason returned HTTP {e.code}')

if __name__ == '__main__':
    run_tests()

