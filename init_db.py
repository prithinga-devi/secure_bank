import sqlite3
import os
from werkzeug.security import generate_password_hash

DB_FILE = 'database.db'
SCHEMA_FILE = 'schema.sql'

def init_db():
    print(f"Initializing database: {DB_FILE}...")
    
    # Connect to database (creates it if it doesn't exist)
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    
    # Read and execute schema
    with open(SCHEMA_FILE, 'r') as f:
        schema_sql = f.read()
    
    cursor.executescript(schema_sql)
    conn.commit()
    print("Schema applied successfully.")
    
    # Seed dummy users
    # Check if they already exist
    cursor.execute("SELECT id FROM users WHERE email = ?", ('customer@banking.com',))
    if not cursor.fetchone():
        customer_pass_hash = generate_password_hash('password123')
        cursor.execute(
            "INSERT INTO users (name, role, email, password, balance) VALUES (?, ?, ?, ?, ?)",
            ("Customer One", "customer", "customer@banking.com", customer_pass_hash, 50000.0)
        )
        print("Inserted customer account (customer@banking.com / password123)")
        
    cursor.execute("SELECT id FROM users WHERE email = ?", ('manager@banking.com',))
    if not cursor.fetchone():
        manager_pass_hash = generate_password_hash('password123')
        cursor.execute(
            "INSERT INTO users (name, role, email, password, balance) VALUES (?, ?, ?, ?, ?)",
            ("Manager One", "manager", "manager@banking.com", manager_pass_hash, 0.0)
        )
        print("Inserted manager account (manager@banking.com / password123)")
        
    conn.commit()
    conn.close()
    print("Database initialization complete.")

if __name__ == '__main__':
    init_db()
