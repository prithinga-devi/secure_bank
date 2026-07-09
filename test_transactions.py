"""Quick verification script for all transaction operations."""
from models.transaction import deposit, withdraw, transfer, get_transaction_history
from models.user import get_user_by_id

def test_all():
    print("=" * 60)
    print("SMART BANKING - Transaction Module Tests")
    print("=" * 60)

    # 1. DEPOSIT
    print("\n--- TEST 1: Deposit ₹5,000 ---")
    success, msg, data = deposit(1, 5000, "Test deposit", "Salary")
    print(f"  Success: {success}")
    print(f"  Message: {msg}")
    if data:
        print(f"  TXN ID: {data['transaction_id']}")
        print(f"  New Balance: {data['new_balance']}")
    user = get_user_by_id(1)
    bal = user['balance']
    print(f"  DB Balance: {bal}")
    assert success, "Deposit should succeed"
    assert bal == 30000.0, f"Expected 30000, got {bal}"
    print("  ✅ PASS")

    # 2. WITHDRAW
    print("\n--- TEST 2: Withdraw ₹2,000 ---")
    success, msg, data = withdraw(1, 2000, "ATM cash", "ATM")
    print(f"  Success: {success}")
    print(f"  Message: {msg}")
    user = get_user_by_id(1)
    bal = user['balance']
    print(f"  DB Balance: {bal}")
    assert success, "Withdraw should succeed"
    assert bal == 28000.0, f"Expected 28000, got {bal}"
    print("  ✅ PASS")

    # 3. INSUFFICIENT BALANCE
    print("\n--- TEST 3: Withdraw ₹999,999 (insufficient) ---")
    success, msg, data = withdraw(1, 999999, "Too much")
    print(f"  Success: {success}")
    print(f"  Message: {msg}")
    user = get_user_by_id(1)
    bal = user['balance']
    print(f"  DB Balance (unchanged): {bal}")
    assert not success, "Should fail"
    assert bal == 28000.0, f"Balance should be unchanged at 28000, got {bal}"
    print("  ✅ PASS")

    # 4. TRANSFER
    print("\n--- TEST 4: Transfer ₹2,500 to ACC1002 ---")
    success, msg, data = transfer(1, "ACC1002", 2500, "Payment to Rahul", "Transfer")
    print(f"  Success: {success}")
    print(f"  Message: {msg}")
    if data:
        print(f"  TXN ID: {data['transaction_id']}")
        print(f"  Receiver: {data['receiver_name']}")
    sender = get_user_by_id(1)
    receiver = get_user_by_id(2)
    s_bal = sender['balance']
    r_bal = receiver['balance']
    print(f"  Sender Balance: {s_bal}")
    print(f"  Receiver Balance: {r_bal}")
    assert success, "Transfer should succeed"
    assert s_bal == 25500.0, f"Sender should have 25500, got {s_bal}"
    assert r_bal == 27500.0, f"Receiver should have 27500, got {r_bal}"
    print("  ✅ PASS")

    # 5. TRANSFER TO SELF
    print("\n--- TEST 5: Transfer to self ---")
    success, msg, data = transfer(1, "ACC1001", 100)
    print(f"  Success: {success}")
    print(f"  Message: {msg}")
    assert not success, "Should reject self-transfer"
    print("  ✅ PASS")

    # 6. INVALID RECEIVER
    print("\n--- TEST 6: Transfer to non-existent account ---")
    success, msg, data = transfer(1, "ACC9999", 100)
    print(f"  Success: {success}")
    print(f"  Message: {msg}")
    assert not success, "Should reject invalid receiver"
    print("  ✅ PASS")

    # 7. ZERO / NEGATIVE AMOUNTS
    print("\n--- TEST 7: Zero and negative amounts ---")
    s1, m1, _ = deposit(1, 0)
    s2, m2, _ = deposit(1, -100)
    s3, m3, _ = withdraw(1, 0)
    s4, m4, _ = transfer(1, "ACC1002", -50)
    print(f"  Deposit 0: {m1}")
    print(f"  Deposit -100: {m2}")
    print(f"  Withdraw 0: {m3}")
    print(f"  Transfer -50: {m4}")
    assert not any([s1, s2, s3, s4]), "All should fail"
    print("  ✅ PASS")

    # 8. NON-NUMERIC
    print("\n--- TEST 8: Non-numeric amount ---")
    success, msg, _ = deposit(1, "abc")
    print(f"  Deposit 'abc': {msg}")
    assert not success
    print("  ✅ PASS")

    # 9. HISTORY
    print("\n--- TEST 9: Transaction History ---")
    txns = get_transaction_history(1)
    print(f"  Total transactions for user 1: {len(txns)}")
    for t in txns:
        tid = t['transaction_id']
        ttype = t['transaction_type']
        amt = t['amount']
        status = t['status']
        bal_after = t['balance_after_transaction']
        print(f"    {tid} | {ttype:10s} | ₹{amt:>10,.2f} | {status:7s} | bal: ₹{bal_after:>10,.2f}")
    assert len(txns) >= 4, "Should have at least 4 transactions"
    print("  ✅ PASS")

    # 10. FILTERED HISTORY
    print("\n--- TEST 10: Filtered History (deposits only) ---")
    deposits = get_transaction_history(1, filter_type='deposit')
    print(f"  Deposit transactions: {len(deposits)}")
    assert all(t['transaction_type'] == 'deposit' for t in deposits)
    print("  ✅ PASS")

    print("\n" + "=" * 60)
    print("ALL TESTS PASSED ✅")
    print("=" * 60)

if __name__ == '__main__':
    test_all()
