-- Schema for Smart Banking Analytics Platform

-- Users table (stores both Customers and Managers)
CREATE TABLE IF NOT EXISTS users (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    account_number TEXT UNIQUE,
    employee_id TEXT UNIQUE,
    google_id TEXT UNIQUE,
    full_name TEXT NOT NULL,
    role TEXT NOT NULL CHECK(role IN ('customer', 'manager')),
    email TEXT UNIQUE NOT NULL,
    password TEXT,
    balance REAL DEFAULT 0.0,
    status TEXT DEFAULT 'active' CHECK(status IN ('active', 'blocked', 'locked')),
    last_login TIMESTAMP,
    failed_login_attempts INTEGER DEFAULT 0
);

-- Login History table
CREATE TABLE IF NOT EXISTS login_history (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER NOT NULL,
    login_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    device TEXT,
    browser TEXT,
    location TEXT,
    ip_address TEXT,
    FOREIGN KEY (user_id) REFERENCES users (id) ON DELETE CASCADE
);

-- Transactions table (stores all banking operations)
CREATE TABLE IF NOT EXISTS transactions (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    transaction_id TEXT UNIQUE NOT NULL,
    sender_id INTEGER NOT NULL,
    receiver_id INTEGER,
    transaction_type TEXT NOT NULL CHECK(transaction_type IN ('deposit', 'withdraw', 'transfer')),
    amount REAL NOT NULL CHECK(amount > 0),
    balance_after_transaction REAL NOT NULL,
    transaction_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    status TEXT NOT NULL CHECK(status IN ('success', 'failed')),
    remarks TEXT,
    FOREIGN KEY (sender_id) REFERENCES users (id) ON DELETE CASCADE,
    FOREIGN KEY (receiver_id) REFERENCES users (id) ON DELETE SET NULL
);

-- Fraud Alerts table (stores suspicious activities)
CREATE TABLE IF NOT EXISTS fraud_alerts (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER,
    transaction_id TEXT,
    alert_type TEXT NOT NULL,
    description TEXT,
    alert_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (user_id) REFERENCES users (id) ON DELETE CASCADE
);
