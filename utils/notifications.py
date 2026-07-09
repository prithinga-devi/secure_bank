from flask import flash
import datetime


def send_email(to, subject, body):
    """
    Mocks sending an email by:
    1. Printing to the console (for developer visibility)
    2. Flashing an in-app notification (for user visibility in the browser)
    """
    timestamp = datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    
    # Console log (no emojis - Windows charmap safe)
    print("=" * 60)
    print(f"[MOCK EMAIL NOTIFICATION]  [{timestamp}]")
    print(f"   To:      {to}")
    print(f"   Subject: {subject}")
    print(f"   Body:    {body}")
    print("=" * 60)
    
    # In-app flash notification (visible in browser)
    try:
        flash(f"Email sent to {to}: {subject}", "info")
    except RuntimeError:
        # Outside of request context (e.g., during testing)
        pass
    
    return True
