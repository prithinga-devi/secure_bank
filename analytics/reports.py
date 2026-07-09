import pandas as pd
from database.db import get_db_connection
import io
from fpdf import FPDF
from datetime import datetime
from analytics.daily import get_dashboard_stats

def get_report_data():
    conn = get_db_connection()
    txns = pd.read_sql("SELECT * FROM transactions ORDER BY transaction_date DESC", conn)
    users = pd.read_sql("SELECT * FROM users WHERE role='customer'", conn)
    fraud = pd.read_sql("SELECT * FROM fraud_alerts ORDER BY alert_date DESC", conn)
    conn.close()
    return txns, users, fraud

def export_csv():
    txns, _, _ = get_report_data()
    return txns.to_csv(index=False)

def export_excel():
    txns, users, fraud = get_report_data()
    output = io.BytesIO()
    with pd.ExcelWriter(output, engine='openpyxl') as writer:
        txns.to_excel(writer, sheet_name='Transactions', index=False)
        users.to_excel(writer, sheet_name='Customers', index=False)
        fraud.to_excel(writer, sheet_name='Fraud Alerts', index=False)
    return output.getvalue()

def export_pdf():
    stats = get_dashboard_stats()
    
    pdf = FPDF()
    pdf.add_page()
    pdf.set_font("helvetica", "B", 16)
    
    pdf.cell(0, 10, "SecureBank - Analytics Report", new_x="LMARGIN", new_y="NEXT", align="C")
    pdf.set_font("helvetica", size=10)
    pdf.cell(0, 10, f"Generated on: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}", new_x="LMARGIN", new_y="NEXT", align="C")
    
    pdf.ln(10)
    
    pdf.set_font("helvetica", "B", 12)
    pdf.cell(0, 10, "Executive Summary", new_x="LMARGIN", new_y="NEXT")
    
    pdf.set_font("helvetica", size=10)
    pdf.cell(0, 8, f"Total Customers: {stats['total_customers']}", new_x="LMARGIN", new_y="NEXT")
    pdf.cell(0, 8, f"Current Bank Balance: INR {stats['current_bank_balance']:,.2f}", new_x="LMARGIN", new_y="NEXT")
    pdf.cell(0, 8, f"Fraud Alerts: {stats['fraud_alerts']}", new_x="LMARGIN", new_y="NEXT")
    
    pdf.ln(5)
    pdf.set_font("helvetica", "B", 12)
    pdf.cell(0, 10, "Today's Activity", new_x="LMARGIN", new_y="NEXT")
    
    pdf.set_font("helvetica", size=10)
    pdf.cell(0, 8, f"Transactions Today: {stats['today_transactions']}", new_x="LMARGIN", new_y="NEXT")
    pdf.cell(0, 8, f"Deposits Today: INR {stats['today_deposits']:,.2f}", new_x="LMARGIN", new_y="NEXT")
    pdf.cell(0, 8, f"Withdrawals Today: INR {stats['today_withdrawals']:,.2f}", new_x="LMARGIN", new_y="NEXT")
    pdf.cell(0, 8, f"Revenue Today: INR {stats['today_revenue']:,.2f}", new_x="LMARGIN", new_y="NEXT")
    
    pdf.ln(10)
    
    # Recent Fraud Alerts
    _, _, fraud = get_report_data()
    pdf.set_font("helvetica", "B", 12)
    pdf.cell(0, 10, "Recent Fraud Alerts (Top 5)", new_x="LMARGIN", new_y="NEXT")
    pdf.set_font("helvetica", size=10)
    
    if fraud.empty:
        pdf.cell(0, 8, "No fraud alerts found.", new_x="LMARGIN", new_y="NEXT")
    else:
        for idx, row in fraud.head(5).iterrows():
            date_str = row['alert_date']
            pdf.cell(0, 8, f"[{date_str}] {row['alert_type']}: {row['description']}", new_x="LMARGIN", new_y="NEXT")
            
    return pdf.output(dest="S")
