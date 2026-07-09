from flask import Flask, render_template, request, redirect, url_for, session, flash, abort
from datetime import timedelta
from utils.auth import login_required, role_required
from models.user import authenticate_manager, authenticate_google_user, get_user_by_id, get_all_users_by_role
from models.transaction import deposit, withdraw, transfer, get_transaction_history, get_recent_transactions
from analytics.daily import get_dashboard_stats, get_last_7_days_stats, get_numpy_statistics
from analytics.monthly import get_monthly_analytics, get_top_customers, get_biggest_transactions, get_inactive_customers, get_peak_banking_hours
from analytics.reports import export_csv, export_excel, export_pdf
from flask import Response, jsonify

app = Flask(__name__)
app.secret_key = 'smart_banking_secure_key_1984'
app.config['PERMANENT_SESSION_LIFETIME'] = timedelta(minutes=15)

@app.before_request
def make_session_permanent():
    session.permanent = True

@app.errorhandler(403)
def forbidden_error(error):
    return render_template('403.html'), 403

@app.route('/')
def home():
    if 'user_id' in session:
        if session.get('role') == 'customer':
            return redirect(url_for('customer_dashboard'))
        elif session.get('role') == 'manager':
            return redirect(url_for('manager_dashboard'))
    # Show landing page for guests
    return render_template('index.html')

@app.route('/login', methods=['GET', 'POST'])
def login():
    # If already logged in, redirect
    if 'user_id' in session:
        return redirect(url_for('customer_dashboard') if session.get('role') == 'customer' else url_for('manager_dashboard'))
        
    if request.method == 'POST':
        # Manager Login (Employee ID + Password)
        employee_id = request.form.get('employee_id')
        password = request.form.get('password')
        
        request_info = {
            'device': request.user_agent.platform or 'Unknown Device',
            'browser': request.user_agent.browser or 'Unknown Browser',
            'location': 'Chennai', # Mocked geolocation
            'ip': request.remote_addr
        }
        
        auth_res = authenticate_manager(employee_id, password, request_info)
        
        if auth_res['success']:
            user = auth_res['user']
            session.permanent = True
            session['user_id'] = user['id']
            session['role'] = user['role']
            session['full_name'] = user['full_name']
            
            flash('Login successful!', 'success')
            return redirect(url_for('manager_dashboard'))
        else:
            flash(auth_res['message'], 'danger')
            return redirect(url_for('login'))
            
    return render_template('login.html')

@app.route('/login/google')
def login_google():
    # Simulate saved Google accounts (like real Google account chooser)
    saved_accounts = [
        {'name': 'Prithinga Ekambaram', 'email': 'prithinga05@gmail.com', 'color': '#1a73e8', 'initials': 'P'},
        {'name': 'Use Another Account', 'email': '', 'color': '#5f6368', 'initials': '?'},
    ]
    # Only show real accounts (non-empty email)
    real_accounts = [a for a in saved_accounts if a['email']]
    return render_template('google_login.html', saved_accounts=real_accounts)

@app.route('/auth/google/callback', methods=['GET', 'POST'])
def auth_google_callback():
    if request.method == 'GET':
        return redirect(url_for('login_google'))

    # Get user-supplied details from the mock Google form
    email = request.form.get('email', '').strip()
    full_name = request.form.get('full_name', '').strip()

    if not email or not full_name:
        flash('Please provide both email and name.', 'danger')
        return redirect(url_for('login_google'))

    # Generate a stable mock google_id from email
    mock_google_id = 'GOOGLE_' + email.replace('@', '_').replace('.', '_').upper()

    request_info = {
        'device': request.user_agent.platform or 'Unknown Device',
        'browser': request.user_agent.browser or 'Unknown Browser',
        'location': 'Chennai',  # Mocked geolocation
        'ip': request.remote_addr
    }

    auth_res = authenticate_google_user(email, full_name, mock_google_id, request_info)

    if auth_res['success']:
        user = auth_res['user']
        session.permanent = True
        session['user_id'] = user['id']
        session['role'] = user['role']
        session['full_name'] = user['full_name']

        flash(f'Welcome, {full_name}! You are now logged in.', 'success')
        return redirect(url_for('customer_dashboard'))
    else:
        flash(auth_res['message'], 'danger')
        return redirect(url_for('login_google'))

@app.route('/logout')
def logout():
    session.clear()
    flash('You have been logged out successfully.', 'info')
    return redirect(url_for('home'))

@app.route('/profile')
@login_required
def profile():
    user = get_user_by_id(session['user_id'])
    return render_template('profile.html', user=user)

@app.route('/dashboard/customer')
@role_required('customer')
def customer_dashboard():
    user = get_user_by_id(session['user_id'])
    transactions = get_recent_transactions(session['user_id'], limit=5)
    from models.user import get_login_history
    login_history = get_login_history(session['user_id'])
    return render_template('customer_dashboard.html', user=user, transactions=transactions, login_history=login_history)

@app.route('/dashboard/manager')
@role_required('manager')
def manager_dashboard():
    customers = get_all_users_by_role('customer')
    stats = get_dashboard_stats()
    
    # Fetch all transactions for the Transactions tab
    from database.db import get_db_connection
    conn = get_db_connection()
    all_transactions = conn.execute("""
        SELECT t.*, 
               sender.full_name AS sender_name, sender.account_number AS sender_account,
               receiver.full_name AS receiver_name, receiver.account_number AS receiver_account
        FROM transactions t
        LEFT JOIN users sender ON t.sender_id = sender.id
        LEFT JOIN users receiver ON t.receiver_id = receiver.id
        ORDER BY t.transaction_date DESC
        LIMIT 100
    """).fetchall()
    
    # Fetch fraud alerts for the Fraud Alerts tab
    fraud_alerts = conn.execute("""
        SELECT fa.*, u.full_name, u.account_number 
        FROM fraud_alerts fa
        LEFT JOIN users u ON fa.user_id = u.id
        ORDER BY fa.alert_date DESC
        LIMIT 50
    """).fetchall()
    conn.close()
    
    return render_template('manager_dashboard.html', 
                           customers=customers, 
                           stats=stats,
                           all_transactions=[dict(t) for t in all_transactions],
                           fraud_alerts_list=[dict(f) for f in fraud_alerts])


# ── Transaction Routes ─────────────────────────────────────────────

@app.route('/deposit', methods=['GET', 'POST'])
@role_required('customer')
def deposit_page():
    user = get_user_by_id(session['user_id'])
    if not user:
        session.clear()
        flash('Session invalid. Please login again.', 'danger')
        return redirect(url_for('login'))

    result_data = None

    if request.method == 'POST':
        amount = request.form.get('amount', '').strip()
        remarks = request.form.get('remarks', '').strip()
        category = request.form.get('category', 'General')

        success, message, data = deposit(session['user_id'], amount, remarks, category)

        if success:
            flash(message, 'success')
            result_data = data
            # Refresh user to get updated balance
            user = get_user_by_id(session['user_id'])
        else:
            flash(message, 'danger')

    return render_template('deposit.html', balance=user['balance'], result=result_data)


@app.route('/withdraw', methods=['GET', 'POST'])
@role_required('customer')
def withdraw_page():
    user = get_user_by_id(session['user_id'])
    if not user:
        session.clear()
        flash('Session invalid. Please login again.', 'danger')
        return redirect(url_for('login'))

    result_data = None

    if request.method == 'POST':
        amount = request.form.get('amount', '').strip()
        remarks = request.form.get('remarks', '').strip()
        category = request.form.get('category', 'General')

        success, message, data = withdraw(session['user_id'], amount, remarks, category)

        if success:
            flash(message, 'success')
            result_data = data
            user = get_user_by_id(session['user_id'])
        else:
            flash(message, 'danger')

    return render_template('withdraw.html', balance=user['balance'], result=result_data)


@app.route('/transfer', methods=['GET', 'POST'])
@role_required('customer')
def transfer_page():
    user = get_user_by_id(session['user_id'])
    if not user:
        session.clear()
        flash('Session invalid. Please login again.', 'danger')
        return redirect(url_for('login'))

    result_data = None

    if request.method == 'POST':
        receiver_account = request.form.get('receiver_account', '').strip()
        amount = request.form.get('amount', '').strip()
        remarks = request.form.get('remarks', '').strip()
        category = request.form.get('category', 'Transfer')

        success, message, data = transfer(session['user_id'], receiver_account, amount, remarks, category)

        if success:
            flash(message, 'success')
            result_data = data
            user = get_user_by_id(session['user_id'])
        else:
            flash(message, 'danger')

    return render_template('transfer.html', 
                           balance=user['balance'],
                           account_number=user['account_number'],
                           result=result_data)


@app.route('/transactions')
@role_required('customer')
def transactions_page():
    user = get_user_by_id(session['user_id'])
    if not user:
        session.clear()
        flash('Session invalid. Please login again.', 'danger')
        return redirect(url_for('login'))

    filter_type = request.args.get('type', '')
    search_query = request.args.get('search', '')

    transactions = get_transaction_history(
        session['user_id'],
        filter_type=filter_type if filter_type else None,
        search_query=search_query if search_query else None
    )

    return render_template('transactions.html',
                           transactions=transactions,
                           balance=user['balance'],
                           filter_type=filter_type,
                           search_query=search_query)

# ── Analytics Routes ─────────────────────────────────────────────

@app.route('/analytics')
@role_required('manager')
def analytics_dashboard():
    stats = get_dashboard_stats()
    numpy_stats = get_numpy_statistics()
    top_customers = get_top_customers()
    biggest_txns = get_biggest_transactions()
    inactive_customers = get_inactive_customers()
    peak_hours = get_peak_banking_hours()
    
    return render_template('analytics.html', 
                           stats=stats,
                           numpy_stats=numpy_stats,
                           top_customers=top_customers,
                           biggest_txns=biggest_txns,
                           inactive_customers=inactive_customers,
                           peak_hours=peak_hours)

@app.route('/api/analytics/data')
@role_required('manager')
def api_analytics_data():
    daily = get_last_7_days_stats()
    monthly = get_monthly_analytics()
    numpy_stats = get_numpy_statistics()
    
    return jsonify({
        'daily': daily,
        'monthly': monthly,
        'stats': numpy_stats
    })

@app.route('/export/report/<format>')
@role_required('manager')
def export_report(format):
    if format == 'csv':
        csv_data = export_csv()
        return Response(csv_data, mimetype="text/csv", headers={"Content-disposition": "attachment; filename=analytics_report.csv"})
    elif format == 'excel':
        excel_data = export_excel()
        return Response(excel_data, mimetype="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet", headers={"Content-disposition": "attachment; filename=analytics_report.xlsx"})
    elif format == 'pdf':
        pdf_data = export_pdf()
        return Response(pdf_data, mimetype="application/pdf", headers={"Content-disposition": "attachment; filename=analytics_report.pdf"})
    
    flash("Invalid format requested.", "danger")
    return redirect(url_for('analytics_dashboard'))
if __name__ == '__main__':
    app.run(debug=True, port=5000)
