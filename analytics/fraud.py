import sqlite3

def check_transaction_fraud(conn, user_id, txn_id, amount, transaction_type):
    """
    Evaluates fraud rules for a new transaction.
    Should be called inside the active transaction block before COMMIT.
    """
    # Rule 1: Transaction > ₹50,000
    if amount > 50000:
        conn.execute(
            """INSERT INTO fraud_alerts (user_id, transaction_id, alert_type, description)
               VALUES (?, ?, 'High Risk', ?)""",
            (user_id, txn_id, f"High value {transaction_type} of ₹{amount:,.2f}")
        )
        
    # Rule 2: More than 5 transactions within 10 minutes
    # Since the current transaction is already inserted, we check for > 5 (i.e. this is the 6th or more)
    count_row = conn.execute(
        """SELECT COUNT(*) as txn_count FROM transactions 
           WHERE sender_id = ? AND transaction_date >= datetime('now', '-10 minutes')""",
        (user_id,)
    ).fetchone()
    
    if count_row and count_row['txn_count'] > 5:
        conn.execute(
            """INSERT INTO fraud_alerts (user_id, transaction_id, alert_type, description)
               VALUES (?, ?, 'Suspicious Activity', ?)""",
            (user_id, txn_id, f"High frequency: {count_row['txn_count']} transactions in last 10 minutes")
        )

def log_negative_balance_attempt(conn, user_id, amount, transaction_type):
    """
    Logs an attempt to withdraw/transfer more than the available balance.
    """
    conn.execute(
        """INSERT INTO fraud_alerts (user_id, alert_type, description)
           VALUES (?, 'Negative Balance', ?)""",
        (user_id, f"Attempted {transaction_type} of ₹{amount:,.2f} with insufficient balance")
    )
