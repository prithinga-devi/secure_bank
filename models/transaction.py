from database.db import get_db_connection
from datetime import datetime
from analytics.fraud import check_transaction_fraud, log_negative_balance_attempt


def generate_transaction_id(conn=None):
    """Generate a unique transaction ID like TXN202607080001."""
    close_conn = False
    if conn is None:
        conn = get_db_connection()
        close_conn = True
        
    today = datetime.now().strftime('%Y%m%d')
    prefix = f"TXN{today}"

    # Find the highest sequence number for today
    row = conn.execute(
        "SELECT transaction_id FROM transactions WHERE transaction_id LIKE ? ORDER BY transaction_id DESC LIMIT 1",
        (f"{prefix}%",)
    ).fetchone()
    
    if close_conn:
        conn.close()

    if row:
        last_seq = int(row['transaction_id'][-4:])
        new_seq = last_seq + 1
    else:
        new_seq = 1

    return f"{prefix}{new_seq:04d}"


def deposit(user_id, amount, remarks='', category='General'):
    """
    Deposit money into the user's account.
    Returns (success: bool, message: str, data: dict or None)
    """
    # Validation
    try:
        amount = float(amount)
    except (ValueError, TypeError):
        return False, "Amount must be a valid number.", None

    if amount <= 0:
        return False, "Amount must be greater than 0.", None

    conn = get_db_connection()
    try:
        # Get current balance
        user = conn.execute("SELECT id, balance, full_name FROM users WHERE id = ?", (user_id,)).fetchone()
        if not user:
            return False, "User not found.", None

        new_balance = user['balance'] + amount
        txn_id = generate_transaction_id()
        full_remarks = f"[{category}] {remarks}".strip() if remarks else f"[{category}]"

        conn.execute("BEGIN")
        conn.execute("UPDATE users SET balance = ? WHERE id = ?", (new_balance, user_id))
        conn.execute(
            """INSERT INTO transactions 
               (transaction_id, sender_id, receiver_id, transaction_type, amount, 
                balance_after_transaction, status, remarks)
               VALUES (?, ?, NULL, 'deposit', ?, ?, 'success', ?)""",
            (txn_id, user_id, amount, new_balance, full_remarks)
        )
        
        check_transaction_fraud(conn, user_id, txn_id, amount, 'deposit')
        conn.execute("COMMIT")

        return True, f"₹{amount:,.2f} deposited successfully.", {
            'transaction_id': txn_id,
            'new_balance': new_balance,
            'amount': amount
        }
    except Exception as e:
        conn.execute("ROLLBACK")
        return False, f"Deposit failed: {str(e)}", None
    finally:
        conn.close()


def withdraw(user_id, amount, remarks='', category='General'):
    """
    Withdraw money from the user's account.
    Returns (success: bool, message: str, data: dict or None)
    """
    # Validation
    try:
        amount = float(amount)
    except (ValueError, TypeError):
        return False, "Amount must be a valid number.", None

    if amount <= 0:
        return False, "Amount must be greater than 0.", None

    conn = get_db_connection()
    try:
        user = conn.execute("SELECT id, balance, full_name FROM users WHERE id = ?", (user_id,)).fetchone()
        if not user:
            return False, "User not found.", None

        if user['balance'] < amount:
            # Record as failed transaction for audit trail
            txn_id = generate_transaction_id()
            full_remarks = f"[{category}] FAILED - Insufficient balance. {remarks}".strip()
            conn.execute(
                """INSERT INTO transactions 
                   (transaction_id, sender_id, receiver_id, transaction_type, amount, 
                    balance_after_transaction, status, remarks)
                   VALUES (?, ?, NULL, 'withdraw', ?, ?, 'failed', ?)""",
                (txn_id, user_id, amount, user['balance'], full_remarks)
            )
            log_negative_balance_attempt(conn, user_id, amount, 'withdraw')
            conn.commit()
            return False, "Insufficient Balance.", None

        new_balance = user['balance'] - amount
        txn_id = generate_transaction_id()
        full_remarks = f"[{category}] {remarks}".strip() if remarks else f"[{category}]"

        conn.execute("BEGIN")
        conn.execute("UPDATE users SET balance = ? WHERE id = ?", (new_balance, user_id))
        conn.execute(
            """INSERT INTO transactions 
               (transaction_id, sender_id, receiver_id, transaction_type, amount, 
                balance_after_transaction, status, remarks)
               VALUES (?, ?, NULL, 'withdraw', ?, ?, 'success', ?)""",
            (txn_id, user_id, amount, new_balance, full_remarks)
        )
        
        check_transaction_fraud(conn, user_id, txn_id, amount, 'withdraw')
        conn.execute("COMMIT")

        return True, f"₹{amount:,.2f} withdrawn successfully.", {
            'transaction_id': txn_id,
            'new_balance': new_balance,
            'amount': amount
        }
    except Exception as e:
        conn.execute("ROLLBACK")
        return False, f"Withdrawal failed: {str(e)}", None
    finally:
        conn.close()


def transfer(sender_id, receiver_account_number, amount, remarks='', category='Transfer'):
    """
    Transfer money from sender to receiver.
    Uses SQLite transactions (BEGIN/COMMIT/ROLLBACK) for atomic updates.
    Returns (success: bool, message: str, data: dict or None)
    """
    # Validation
    try:
        amount = float(amount)
    except (ValueError, TypeError):
        return False, "Amount must be a valid number.", None

    if amount <= 0:
        return False, "Amount must be greater than 0.", None

    if not receiver_account_number or not receiver_account_number.strip():
        return False, "Receiver account number is required.", None

    conn = get_db_connection()
    try:
        # Get sender
        sender = conn.execute("SELECT id, balance, full_name, account_number FROM users WHERE id = ?", (sender_id,)).fetchone()
        if not sender:
            return False, "Sender account not found.", None

        # Get receiver
        receiver = conn.execute(
            "SELECT id, balance, full_name, account_number FROM users WHERE account_number = ?",
            (receiver_account_number.strip().upper(),)
        ).fetchone()

        if not receiver:
            return False, "Receiver account does not exist.", None

        if sender['id'] == receiver['id']:
            return False, "Cannot transfer to your own account.", None

        if sender['balance'] < amount:
            # Record as failed for audit
            txn_id = generate_transaction_id(conn)
            full_remarks = f"[{category}] FAILED - Insufficient balance. To: {receiver['full_name']} ({receiver_account_number}). {remarks}".strip()
            conn.execute(
                """INSERT INTO transactions 
                   (transaction_id, sender_id, receiver_id, transaction_type, amount, 
                    balance_after_transaction, status, remarks)
                   VALUES (?, ?, ?, 'transfer', ?, ?, 'failed', ?)""",
                (txn_id, sender_id, receiver['id'], amount, sender['balance'], full_remarks)
            )
            log_negative_balance_attempt(conn, sender_id, amount, 'transfer')
            conn.commit()
            return False, "Insufficient Balance.", None

        # Perform atomic transfer
        sender_new_balance = sender['balance'] - amount
        receiver_new_balance = receiver['balance'] + amount
        full_remarks_sender = f"[{category}] To: {receiver['full_name']} ({receiver_account_number}). {remarks}".strip()
        full_remarks_receiver = f"[{category}] From: {sender['full_name']} ({sender['account_number']}). {remarks}".strip()

        conn.execute("BEGIN")

        # Update both balances
        conn.execute("UPDATE users SET balance = ? WHERE id = ?", (sender_new_balance, sender_id))
        conn.execute("UPDATE users SET balance = ? WHERE id = ?", (receiver_new_balance, receiver['id']))

        sender_txn_id = generate_transaction_id(conn)
        
        # Record sender's transaction (debit)
        conn.execute(
            """INSERT INTO transactions 
               (transaction_id, sender_id, receiver_id, transaction_type, amount, 
                balance_after_transaction, status, remarks)
               VALUES (?, ?, ?, 'transfer', ?, ?, 'success', ?)""",
            (sender_txn_id, sender_id, receiver['id'], amount, sender_new_balance, full_remarks_sender)
        )

        receiver_txn_id = generate_transaction_id(conn)

        # Record receiver's transaction (credit)
        conn.execute(
            """INSERT INTO transactions 
               (transaction_id, sender_id, receiver_id, transaction_type, amount, 
                balance_after_transaction, status, remarks)
               VALUES (?, ?, ?, 'transfer', ?, ?, 'success', ?)""",
            (receiver_txn_id, receiver['id'], sender_id, amount, receiver_new_balance, full_remarks_receiver)
        )

        check_transaction_fraud(conn, sender_id, sender_txn_id, amount, 'transfer')
        conn.execute("COMMIT")

        return True, f"₹{amount:,.2f} transferred successfully.", {
            'transaction_id': sender_txn_id,
            'sender_new_balance': sender_new_balance,
            'receiver_name': receiver['full_name'],
            'receiver_account': receiver_account_number,
            'amount': amount
        }
    except Exception as e:
        conn.execute("ROLLBACK")
        return False, f"Transfer failed: {str(e)}", None
    finally:
        conn.close()


def get_transaction_history(user_id, filter_type=None, search_query=None):
    """
    Get transaction history for a user.
    filter_type: 'deposit', 'withdraw', 'transfer', or None for all.
    search_query: search by transaction_id or remarks.
    """
    conn = get_db_connection()

    query = """
        SELECT t.*, 
               sender.full_name AS sender_name, 
               receiver.full_name AS receiver_name
        FROM transactions t
        LEFT JOIN users sender ON t.sender_id = sender.id
        LEFT JOIN users receiver ON t.receiver_id = receiver.id
        WHERE t.sender_id = ?
    """
    params = [user_id]

    if filter_type and filter_type in ('deposit', 'withdraw', 'transfer'):
        query += " AND t.transaction_type = ?"
        params.append(filter_type)

    if search_query and search_query.strip():
        query += " AND (t.transaction_id LIKE ? OR t.remarks LIKE ?)"
        search_term = f"%{search_query.strip()}%"
        params.extend([search_term, search_term])

    query += " ORDER BY t.transaction_date DESC"

    transactions = conn.execute(query, params).fetchall()
    conn.close()
    return transactions


def get_recent_transactions(user_id, limit=5):
    """Get the most recent transactions for dashboard display."""
    conn = get_db_connection()
    transactions = conn.execute(
        """SELECT t.*, 
                  sender.full_name AS sender_name, 
                  receiver.full_name AS receiver_name
           FROM transactions t
           LEFT JOIN users sender ON t.sender_id = sender.id
           LEFT JOIN users receiver ON t.receiver_id = receiver.id
           WHERE t.sender_id = ?
           ORDER BY t.transaction_date DESC
           LIMIT ?""",
        (user_id, limit)
    ).fetchall()
    conn.close()
    return transactions
