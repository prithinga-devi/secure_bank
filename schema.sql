-- Schema for Smart Banking Analytics Platform

-- Users table (stores both Customers and Managers)
CREATE TABLE IF NOT EXISTS users (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL,
    role TEXT NOT NULL CHECK(role IN ('customer', 'manager')),
    email TEXT UNIQUE NOT NULL,
    password TEXT NOT NULL,
    balance REAL DEFAULT 0.0
);

-- Transactions table (stores all banking operations)
CREATE TABLE IF NOT EXISTS transactions (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER NOT NULL,
    type TEXT NOT NULL CHECK(type IN ('deposit', 'withdraw', 'transfer')),
    amount REAL NOT NULL CHECK(amount > 0),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    note TEXT,
    status TEXT DEFAULT 'completed' CHECK(status IN ('completed', 'failed', 'flagged')),
    FOREIGN KEY (user_id) REFERENCES users (id) ON DELETE CASCADE
);
