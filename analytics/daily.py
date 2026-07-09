import pandas as pd
import numpy as np
from database.db import get_db_connection
from datetime import datetime, timedelta

def get_dashboard_stats():
    """
    Returns core stats for the top cards on the dashboard.
    """
    conn = get_db_connection()
    today_str = datetime.now().strftime('%Y-%m-%d')
    
    # 1. Total Customers
    cust_count = conn.execute("SELECT COUNT(*) FROM users WHERE role = 'customer'").fetchone()[0]
    
    # 2. Bank Balance
    bank_balance = conn.execute("SELECT SUM(balance) FROM users WHERE role = 'customer'").fetchone()[0] or 0.0
    
    # 3. Fraud Alerts
    fraud_count = conn.execute("SELECT COUNT(*) FROM fraud_alerts").fetchone()[0]
    
    # Load today's transactions into Pandas
    df = pd.read_sql(
        "SELECT * FROM transactions WHERE date(transaction_date) = ?", 
        conn, params=(today_str,)
    )
    conn.close()
    
    if df.empty:
        today_txns = 0
        today_deposits = 0.0
        today_withdrawals = 0.0
        today_revenue = 0.0
    else:
        today_txns = len(df)
        
        # NumPy operations
        amounts = df['amount'].to_numpy()
        types = df['transaction_type'].to_numpy()
        
        deposits_mask = (types == 'deposit')
        withdraws_mask = (types == 'withdraw')
        transfers_mask = (types == 'transfer')
        
        today_deposits = np.sum(amounts[deposits_mask]) if np.any(deposits_mask) else 0.0
        today_withdrawals = np.sum(amounts[withdraws_mask]) if np.any(withdraws_mask) else 0.0
        
        # Revenue: 10 per transfer (each transfer creates 2 records: 1 success sender, 1 success receiver. 
        # We should only count unique transfers. Or we can just say 5 per record, making 10 per pair.
        # Let's count sender's transfer records (where balance decreased or amount is same). 
        # But wait, withdrawal = 15.
        # Transfer = 10.
        withdraw_count = np.sum(withdraws_mask & (df['status'] == 'success'))
        # A transfer inserts two rows per transfer (sender debit, receiver credit). Both have 'transfer'.
        # We can just count transfers where sender_id != receiver_id in DB, but in Pandas we can just divide by 2
        transfer_count = np.sum(transfers_mask & (df['status'] == 'success')) / 2
        today_revenue = (withdraw_count * 15) + (transfer_count * 10)
        
    return {
        'total_customers': cust_count,
        'current_bank_balance': bank_balance,
        'fraud_alerts': fraud_count,
        'today_transactions': today_txns,
        'today_deposits': today_deposits,
        'today_withdrawals': today_withdrawals,
        'today_revenue': today_revenue
    }

def get_last_7_days_stats():
    """
    Returns daily stats for the last 7 days.
    """
    conn = get_db_connection()
    seven_days_ago = (datetime.now() - timedelta(days=6)).strftime('%Y-%m-%d')
    
    df = pd.read_sql(
        "SELECT date(transaction_date) as date, transaction_type, amount, status FROM transactions WHERE date(transaction_date) >= ? AND status = 'success'", 
        conn, params=(seven_days_ago,)
    )
    conn.close()
    
    if df.empty:
        return []

    # Ensure date column is datetime for easy grouping
    df['date'] = pd.to_datetime(df['date'])
    
    daily_stats = []
    # Generate the last 7 days including today
    for i in range(6, -1, -1):
        target_date = (datetime.now() - timedelta(days=i)).strftime('%Y-%m-%d')
        day_df = df[df['date'] == target_date]
        
        day_name = pd.to_datetime(target_date).strftime('%A')
        
        if day_df.empty:
            daily_stats.append({
                'day': day_name, 'date': target_date, 'deposits': 0, 'withdrawals': 0, 'transactions': 0
            })
        else:
            amounts = day_df['amount'].to_numpy()
            types = day_df['transaction_type'].to_numpy()
            
            deposits = np.sum(amounts[types == 'deposit']) if np.any(types == 'deposit') else 0.0
            withdrawals = np.sum(amounts[types == 'withdraw']) if np.any(types == 'withdraw') else 0.0
            
            # Transfer count: divide by 2 since there are 2 rows per transfer. Wait, daily transactions count usually includes all legs or just operations?
            # Let's count all rows as transactions. Or we can divide transfers by 2.
            transfer_count = np.sum(types == 'transfer') / 2
            operations = np.sum(types == 'deposit') + np.sum(types == 'withdraw') + transfer_count
            
            daily_stats.append({
                'day': day_name, 
                'date': target_date, 
                'deposits': deposits, 
                'withdrawals': withdrawals, 
                'transactions': int(operations)
            })
            
    return daily_stats

def get_numpy_statistics():
    """
    Core NumPy Task implementations.
    """
    conn = get_db_connection()
    df = pd.read_sql("SELECT amount, transaction_type, sender_id FROM transactions WHERE status = 'success'", conn)
    balances = pd.read_sql("SELECT balance FROM users WHERE role = 'customer'", conn)
    conn.close()
    
    if df.empty:
        return {}
        
    amounts = df['amount'].to_numpy()
    
    stats = {
        'average_transaction': np.mean(amounts),
        'max_transaction': np.max(amounts),
        'min_transaction': np.min(amounts),
        'median_transaction': np.median(amounts),
        'std_dev': np.std(amounts),
        'total_deposits': np.sum(amounts[df['transaction_type'] == 'deposit']) if not df[df['transaction_type'] == 'deposit'].empty else 0.0,
        'total_withdrawals': np.sum(amounts[df['transaction_type'] == 'withdraw']) if not df[df['transaction_type'] == 'withdraw'].empty else 0.0,
        'highest_balance': np.max(balances['balance'].to_numpy()) if not balances.empty else 0.0,
        'lowest_balance': np.min(balances['balance'].to_numpy()) if not balances.empty else 0.0,
    }
    return stats
