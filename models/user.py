from database.db import get_db_connection
from werkzeug.security import check_password_hash
from datetime import datetime
import random
import string
from utils.notifications import send_email

def authenticate_manager(employee_id, password, request_info):
    """
    Authenticates a manager using Employee ID and password.
    request_info is a dict containing device, browser, location, ip.
    """
    conn = get_db_connection()
    user = conn.execute(
        "SELECT * FROM users WHERE employee_id = ? AND role = 'manager'", 
        (employee_id,)
    ).fetchone()
    
    if user:
        if user['status'] == 'locked' or user['status'] == 'blocked':
            conn.close()
            return {'success': False, 'message': 'Account is locked or blocked. Contact administrator.'}
            
        if check_password_hash(user['password'], password):
            # Reset failed attempts
            conn.execute("UPDATE users SET failed_login_attempts = 0, last_login = CURRENT_TIMESTAMP WHERE id = ?", (user['id'],))
            
            # Insert login history
            conn.execute("""
                INSERT INTO login_history (user_id, device, browser, location, ip_address) 
                VALUES (?, ?, ?, ?, ?)
            """, (user['id'], request_info.get('device'), request_info.get('browser'), request_info.get('location'), request_info.get('ip')))
            
            conn.commit()
            conn.close()
            
            send_email(
                to=user['email'], 
                subject="Security Alert: New Login", 
                body=f"A new login was detected from {request_info.get('location', 'Unknown')} using {request_info.get('browser', 'Unknown')} on {request_info.get('device', 'Unknown')}."
            )
            
            return {'success': True, 'user': dict(user)}
        else:
            # Increment failed attempts
            attempts = user['failed_login_attempts'] + 1
            if attempts >= 3:
                conn.execute("UPDATE users SET failed_login_attempts = ?, status = 'locked' WHERE id = ?", (attempts, user['id']))
                msg = 'Account locked due to 3 failed login attempts.'
                send_email(
                    to=user['email'],
                    subject="Security Alert: Account Locked",
                    body="Your account has been locked due to 3 consecutive failed login attempts. Please contact the administrator."
                )
            else:
                conn.execute("UPDATE users SET failed_login_attempts = ? WHERE id = ?", (attempts, user['id']))
                msg = f'Invalid password. {3 - attempts} attempts remaining.'
            conn.commit()
            conn.close()
            return {'success': False, 'message': msg}
            
    conn.close()
    return {'success': False, 'message': 'Invalid Employee ID.'}

def generate_account_number():
    return 'ACC' + ''.join(random.choices(string.digits, k=6))

def authenticate_google_user(email, full_name, google_id, request_info):
    """
    Authenticates a customer via Google. If they don't exist, create them.
    """
    conn = get_db_connection()
    user = conn.execute("SELECT * FROM users WHERE email = ? AND role = 'customer'", (email,)).fetchone()
    
    if user:
        if user['status'] == 'locked' or user['status'] == 'blocked':
            conn.close()
            return {'success': False, 'message': 'Account is locked or blocked. Contact administrator.'}
            
        # Ensure google_id is set if not already
        if not user['google_id']:
            conn.execute("UPDATE users SET google_id = ? WHERE id = ?", (google_id, user['id']))
            
        # Reset failed attempts and update last_login
        conn.execute("UPDATE users SET failed_login_attempts = 0, last_login = CURRENT_TIMESTAMP WHERE id = ?", (user['id'],))
        user_id = user['id']
        user_dict = dict(user)
    else:
        # Create new customer account
        account_number = generate_account_number()
        # Ensure uniqueness
        while conn.execute("SELECT 1 FROM users WHERE account_number = ?", (account_number,)).fetchone():
            account_number = generate_account_number()
            
        cursor = conn.execute("""
            INSERT INTO users (account_number, full_name, role, email, google_id, balance, status) 
            VALUES (?, ?, 'customer', ?, ?, 0.0, 'active')
        """, (account_number, full_name, email, google_id))
        
        user_id = cursor.lastrowid
        user = conn.execute("SELECT * FROM users WHERE id = ?", (user_id,)).fetchone()
        user_dict = dict(user)
        
    # Log the login history
    conn.execute("""
        INSERT INTO login_history (user_id, device, browser, location, ip_address) 
        VALUES (?, ?, ?, ?, ?)
    """, (user_id, request_info.get('device'), request_info.get('browser'), request_info.get('location'), request_info.get('ip')))
    
    conn.commit()
    conn.close()
    
    send_email(
        to=user_dict['email'], 
        subject="Security Alert: New Login", 
        body=f"A new login was detected from {request_info.get('location', 'Unknown')} using {request_info.get('browser', 'Unknown')} on {request_info.get('device', 'Unknown')}."
    )
    
    return {'success': True, 'user': user_dict}

def get_user_by_id(user_id):
    conn = get_db_connection()
    user = conn.execute("SELECT * FROM users WHERE id = ?", (user_id,)).fetchone()
    conn.close()
    return dict(user) if user else None

def get_all_users_by_role(role):
    conn = get_db_connection()
    users = conn.execute("SELECT * FROM users WHERE role = ?", (role,)).fetchall()
    conn.close()
    return [dict(u) for u in users]

def get_login_history(user_id):
    conn = get_db_connection()
    history = conn.execute("SELECT * FROM login_history WHERE user_id = ? ORDER BY login_date DESC LIMIT 10", (user_id,)).fetchall()
    conn.close()
    return [dict(h) for h in history]

def get_user_by_account_number(account_number):
    conn = get_db_connection()
    user = conn.execute("SELECT * FROM users WHERE account_number = ?", (account_number,)).fetchone()
    conn.close()
    return user
