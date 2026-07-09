import sqlite3
from models.transaction import deposit, withdraw, transfer
from werkzeug.security import generate_password_hash

# First ensure users exist
conn = sqlite3.connect('database.db')
c = conn.cursor()

# Insert 10 customers if not exist
for i in range(3, 13):
    acc = f"ACC10{i:02d}"
    google_id = f"MOCK_GOOGLE_{i}"
    try:
        c.execute(
            "INSERT INTO users (account_number, full_name, role, email, google_id, balance, status) VALUES (?, ?, 'customer', ?, ?, 0.0, 'active')",
            (acc, f"Test User {i}", f"test{i}@securebank.com", google_id)
        )
    except sqlite3.IntegrityError:
        pass
conn.commit()
conn.close()

# Perform some transactions
print("Seeding transactions...")
# ID 1 (Prithinga), ID 2 (Rahul)
# ID 4-13 (Test Users)
for i in range(1, 10):
    deposit(1, 5000 + (i*1000), f"Salary Day {i}", 'Deposit')
    withdraw(1, 2000, f"Rent {i}", 'Withdraw')
    
for i in range(1, 5):
    transfer(1, "ACC1002", 5000, "Gift", "Transfer")

deposit(2, 50000, "Bonus", 'Deposit') # Should trigger Rule 1 Fraud Alert

# Trigger Rule 2 (5 txns in 10 mins)
for i in range(7):
    deposit(2, 100, "Micro deposit", 'Deposit')

# Trigger Rule 4 (Negative Balance)
withdraw(1, 999999, "Dream Car", 'Withdraw')

print("Seeding complete.")
