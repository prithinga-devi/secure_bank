import pandas as pd
import numpy as np
from database.db import get_db_connection

def get_monthly_analytics():
    """
    Returns monthly stats for the current year.
    """
    conn = get_db_connection()
    df = pd.read_sql(
        "SELECT strftime('%Y-%m', transaction_date) as month, transaction_type, amount, status FROM transactions WHERE status = 'success'", 
        conn
    )
    conn.close()
    
    if df.empty:
        return []

    # Unique months
    months = np.unique(df['month'].dropna().to_numpy())
    months = sorted(months)
    
    monthly_stats = []
    
    for m in months:
        m_df = df[df['month'] == m]
        amounts = m_df['amount'].to_numpy()
        types = m_df['transaction_type'].to_numpy()
        
        deposits = np.sum(amounts[types == 'deposit']) if np.any(types == 'deposit') else 0.0
        withdrawals = np.sum(amounts[types == 'withdraw']) if np.any(types == 'withdraw') else 0.0
        
        # Assuming transfers count as 1 operation (2 rows in DB, so divide by 2)
        transfers = np.sum(types == 'transfer') / 2
        total_ops = np.sum(types == 'deposit') + np.sum(types == 'withdraw') + transfers
        
        # Convert YYYY-MM to Month Name
        import datetime
        month_name = datetime.datetime.strptime(m, '%Y-%m').strftime('%B')
        
        monthly_stats.append({
            'month': month_name,
            'month_raw': m,
            'deposits': deposits,
            'withdrawals': withdrawals,
            'transactions': int(total_ops)
        })
        
    return monthly_stats

def get_top_customers():
    """
    Finds top 10 customers based on highest balance and activity.
    """
    conn = get_db_connection()
    users = pd.read_sql("SELECT id, full_name, account_number, balance, last_login FROM users WHERE role = 'customer'", conn)
    txns = pd.read_sql("SELECT sender_id, COUNT(*) as txn_count FROM transactions GROUP BY sender_id", conn)
    conn.close()
    
    if users.empty:
        return []
        
    # Merge to get transaction count per user
    if not txns.empty:
        users = pd.merge(users, txns, left_on='id', right_on='sender_id', how='left')
    else:
        users['txn_count'] = 0
        
    users['txn_count'] = users['txn_count'].fillna(0)
    
    # Sort by balance descending
    top_users = users.sort_values(by=['balance', 'txn_count'], ascending=[False, False]).head(10)
    
    return top_users.to_dict('records')

def get_biggest_transactions():
    """
    Top 20 highest transactions.
    """
    conn = get_db_connection()
    df = pd.read_sql(
        """SELECT t.amount, t.transaction_type, t.transaction_date, u.full_name as customer 
           FROM transactions t
           JOIN users u ON t.sender_id = u.id
           WHERE t.status = 'success'
           ORDER BY t.amount DESC LIMIT 20""", 
        conn
    )
    conn.close()
    return df.to_dict('records')
    
def get_inactive_customers():
    """
    Customers who didn't login in the last 30 days.
    """
    conn = get_db_connection()
    df = pd.read_sql(
        """SELECT full_name, account_number, last_login, balance 
           FROM users 
           WHERE role = 'customer' AND (last_login IS NULL OR last_login < datetime('now', '-30 days'))""",
        conn
    )
    conn.close()
    return df.to_dict('records')

def get_peak_banking_hours():
    """
    Finds most active hours.
    """
    conn = get_db_connection()
    df = pd.read_sql("SELECT strftime('%H', transaction_date) as hour FROM transactions", conn)
    conn.close()
    
    if df.empty or df['hour'].isnull().all():
        return []
        
    hour_counts = df['hour'].value_counts().reset_index()
    hour_counts.columns = ['hour', 'count']
    hour_counts = hour_counts.sort_values(by='hour')
    
    # Format hour to 12-hour AM/PM
    result = []
    for _, row in hour_counts.iterrows():
        h = int(row['hour'])
        ampm = "AM" if h < 12 else "PM"
        h12 = h if h <= 12 else h - 12
        if h12 == 0: h12 = 12
        result.append({
            'hour_label': f"{h12} {ampm}",
            'count': int(row['count']),
            'raw_hour': h
        })
        
    return sorted(result, key=lambda x: x['count'], reverse=True)
