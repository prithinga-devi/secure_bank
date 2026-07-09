from app import app
from database.db import get_db_connection
import json

def test_auth():
    app.config['TESTING'] = True
    client = app.test_client()
    
    print("=== Verification Starting ===")

    # 1. Verify Role Separation and 403 Redirection
    print("\n1. Testing unauthorized access...")
    res = client.get('/dashboard/manager')
    assert res.status_code == 302
    assert '/login' in res.location
    print("[PASS] Unauthenticated user redirected to login.")
    
    # 2. Verify Mock Google Flow
    print("\n2. Testing Mock Google Login...")
    res = client.get('/login/google')
    assert res.status_code == 302
    assert '/auth/google/callback' in res.location
    
    res = client.get('/auth/google/callback', follow_redirects=True)
    assert res.status_code == 200
    assert b'Welcome, <strong>Prithinga</strong>' in res.data
    print("[PASS] Google Mock Login successful.")
    
    with client.session_transaction() as sess:
        assert sess['role'] == 'customer'
        assert sess.permanent == True
    
    # Customer trying to access manager analytics
    res = client.get('/analytics')
    assert res.status_code == 403
    assert b'Access Denied' in res.data
    print("[PASS] Customer blocked from manager route (403 Forbidden).")
    
    client.get('/logout')
    
    # 3. Verify Employee Lockout and Login History
    print("\n3. Testing Manager Login & Lockout...")
    
    # Fail 1
    res = client.post('/login', data={'employee_id': 'EMP001', 'password': 'wrong'}, follow_redirects=True)
    assert b'Invalid password. 2 attempts remaining' in res.data
    
    # Fail 2
    res = client.post('/login', data={'employee_id': 'EMP001', 'password': 'wrong'}, follow_redirects=True)
    assert b'Invalid password. 1 attempts remaining' in res.data
    
    # Fail 3 -> Lockout
    res = client.post('/login', data={'employee_id': 'EMP001', 'password': 'wrong'}, follow_redirects=True)
    assert b'Account locked' in res.data
    
    # Attempt correct login but locked
    res = client.post('/login', data={'employee_id': 'EMP001', 'password': 'password123'}, follow_redirects=True)
    assert b'Account is locked or blocked' in res.data
    print("[PASS] Manager account lockout enforced.")
    
    # Let's unlock EMP001 manually to test login history
    conn = get_db_connection()
    conn.execute("UPDATE users SET status = 'active', failed_login_attempts = 0 WHERE employee_id = 'EMP001'")
    conn.commit()
    conn.close()
    
    # Successful Login
    res = client.post('/login', data={'employee_id': 'EMP001', 'password': 'password123'}, follow_redirects=True)
    assert b'Welcome, <strong>System Admin</strong>' in res.data
    print("[PASS] Manager login successful.")
    
    # Check Login History
    conn = get_db_connection()
    lh = conn.execute("SELECT * FROM login_history WHERE user_id = (SELECT id FROM users WHERE employee_id = 'EMP001')").fetchone()
    conn.close()
    
    assert lh is not None
    assert lh['location'] == 'Chennai'
    print("[PASS] Login history tracked with mocked 'Chennai' location.")
    
    print("\n=== Verification Complete ===")

if __name__ == '__main__':
    test_auth()
