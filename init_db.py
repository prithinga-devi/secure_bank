import sqlite3
import os
from werkzeug.security import generate_password_hash

DB_FILE = 'database.db'
SCHEMA_FILE = 'schema.sql'

def init_db():
    # Remove existing database file if it exists to ensure a clean start with new schema
    if os.path.exists(DB_FILE):
        try:
            os.remove(DB_FILE)
            print(f"Removed existing database file: {DB_FILE}")
        except PermissionError:
            print(f"Warning: Could not remove {DB_FILE} (locked by another process). Will try to drop tables instead.")
            
    print(f"Initializing database: {DB_FILE}...")
    
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    
    # If the file couldn't be deleted, drop existing tables
    cursor.execute("DROP TABLE IF EXISTS fraud_alerts;")
    cursor.execute("DROP TABLE IF EXISTS transactions;")
    cursor.execute("DROP TABLE IF EXISTS login_history;")
    cursor.execute("DROP TABLE IF EXISTS users;")
    conn.commit()
    
    # Read and execute schema
    with open(SCHEMA_FILE, 'r') as f:
        schema_sql = f.read()
    
    cursor.executescript(schema_sql)
    conn.commit()
    print("Schema applied successfully.")
    
    # Insert default manager
    admin_password = generate_password_hash("password123")
    cursor.execute("""
        INSERT INTO users (employee_id, full_name, role, email, password, balance, status)
        VALUES (?, ?, 'manager', ?, ?, ?, ?)
    """, ("EMP001", "System Admin", "manager@securebank.com", admin_password, 0.0, "active"))
    print("Default Manager created. ID: EMP001, Pass: password123")

    # Seed dummy users
    customer_pass_hash = generate_password_hash('password123')
    cursor.execute(
        "INSERT INTO users (account_number, full_name, role, email, password, balance, status) VALUES (?, ?, ?, ?, ?, ?, ?)",
        ("ACC1001", "Prithinga", "customer", "customer@banking.com", customer_pass_hash, 25000.0, "active")
    )
    print("Inserted customer account (customer@banking.com / password123, Name: Prithinga, Acc: ACC1001, Balance: INR 25,000)")

    customer2_pass_hash = generate_password_hash('password123')
    cursor.execute(
        "INSERT INTO users (account_number, full_name, role, email, password, balance, status) VALUES (?, ?, ?, ?, ?, ?, ?)",
        ("ACC1002", "Rahul Sharma", "customer", "customer2@banking.com", customer2_pass_hash, 25000.0, "active")
    )
    print("Inserted customer account (customer2@banking.com / password123, Name: Rahul Sharma, Acc: ACC1002, Balance: INR 25,000)")
        
    manager_pass_hash = generate_password_hash('password123')
    cursor.execute(
        "INSERT INTO users (employee_id, full_name, role, email, password, balance, status) VALUES (?, ?, ?, ?, ?, ?, ?)",
        ("EMP002", "Manager One", "manager", "manager@banking.com", manager_pass_hash, 0.0, "active")
    )
    print("Inserted manager account (manager@banking.com / password123, Name: Manager One, ID: EMP002)")
        
    conn.commit()
    conn.close()
    print("Database initialization complete.")

if __name__ == '__main__':
    init_db()
