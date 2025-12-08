import random
import base64
import os
from django.core.cache import cache
from django.core.mail import EmailMessage
from django.conf import settings
from datetime import datetime, timedelta
import json
import time

# create otp code
def create_otp_code():
    digits = "0123456789"
    otp = ''.join(random.choice(digits) for i in range(6))

    return otp

# cache for 5 minutes
def cache_register_otp(user_id, otp_code, email):
    """
    Cache OTP data for registration verification
    Args:
        user_id: Primary key of User (int)
        otp_code: 6-digit OTP code (str)
        email: User's email for resending OTP (str)
    """
    cache_key = f"register_{user_id}"
    cache_data = {
        'otp_code': otp_code,
        'email': email,
        'last_sent': datetime.now().isoformat()
    }
    
    cache.set(cache_key, json.dumps(cache_data))
    
    time.sleep(3)
    ttl = cache.ttl(cache_key)
    print(f"TTL: {ttl}")
    test = cache.get(cache_key)
    print(f"Test cache: {cache_key}: {test}, {datetime.now().isoformat()}")
    
    time.sleep(3)
    ttl = cache.ttl(cache_key)
    print(f"TTL: {ttl}")
    test = cache.get(cache_key)
    print(f"Test cache: {cache_key}: {test}, {datetime.now().isoformat()}")

# get logo as base64 for email embedding
def get_logo_base64():
    """Read logo file and convert to base64 for email embedding"""
    logo_path = os.path.join(settings.BASE_DIR, 'static', 'logo.png')
    try:
        with open(logo_path, 'rb') as logo_file:
            logo_data = logo_file.read()
            logo_base64 = base64.b64encode(logo_data).decode('utf-8')
            return f"data:image/png;base64,{logo_base64}"
    except FileNotFoundError:
        return None

# send otp code to email
def send_registration_otp_email(email, otp_code):
    logo_data = get_logo_base64()
    logo_html = f'<img src="{logo_data}" alt="NENS Logo" style="max-width: 120px; height: auto; margin-bottom: 20px;" />' if logo_data else ''
    
    subject = "NENS - Account Registration OTP Verification"
    html_body = f"""
    <!DOCTYPE html>
    <html>
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <style>
            body {{
                font-family: 'Poppins', Arial, sans-serif;
                background-color: #FFF4E9;
                color: #383838;
                padding: 0;
                margin: 0;
            }}
            .email-wrapper {{
                background-color: #FFF4E9;
                padding: 40px 20px;
            }}
            .container {{
                background-color: #FFFFFF;
                padding: 40px 30px;
                border-radius: 12px;
                box-shadow: 0 4px 6px rgba(0, 0, 0, 0.1);
                max-width: 600px;
                margin: 0 auto;
            }}
            .logo-container {{
                text-align: center;
                margin-bottom: 30px;
            }}
            h1 {{
                color: #532822;
                font-size: 24px;
                font-weight: bold;
                margin: 0 0 20px 0;
                text-align: center;
            }}
            p {{
                font-size: 16px;
                line-height: 1.6;
                color: #383838;
                margin: 15px 0;
            }}
            .otp-container {{
                text-align: center;
                margin: 30px 0;
            }}
            .otp-code {{
                font-size: 32px;
                font-weight: bold;
                color: #532822;
                padding: 15px 30px;
                background-color: #FFF4E9;
                display: inline-block;
                border-radius: 8px;
                border: 2px solid #FF854B;
                letter-spacing: 4px;
            }}
            .info-box {{
                background-color: #FFF4E9;
                padding: 15px;
                border-radius: 8px;
                margin: 20px 0;
                border-left: 4px solid #FF854B;
            }}
            .info-box p {{
                margin: 5px 0;
                font-size: 14px;
            }}
            .footer {{
                margin-top: 30px;
                padding-top: 20px;
                border-top: 1px solid #E0E0E0;
                text-align: center;
                font-size: 14px;
                color: #666;
            }}
            .footer-brand {{
                color: #532822;
                font-weight: bold;
                font-size: 16px;
                margin-top: 10px;
            }}
        </style>
    </head>
    <body>
        <div class="email-wrapper">
            <div class="container">
                <div class="logo-container">
                    {logo_html}
                </div>
                <h1>Account Registration OTP Verification</h1>
                <p>Dear valued customer,</p>
                <p>Thank you for registering with NENS! To complete your account registration, please use the OTP code below:</p>
                
                <div class="otp-container">
                    <div class="otp-code">{otp_code}</div>
                </div>
                
                <div class="info-box">
                    <p><strong>Important:</strong></p>
                    <p>• This OTP code is valid for 5 minutes only</p>
                    <p>• Do not share this code with anyone</p>
                    <p>• If you did not request this registration, please ignore this email</p>
                </div>
                
                <p>Enter this code on the verification page to complete your registration process.</p>
                
                <div class="footer">
                    <p>Best regards,</p>
                    <div class="footer-brand">NENS - No English No Success</div>
                </div>
            </div>
        </div>
    </body>
    </html>
    """
    from_email = settings.EMAIL_HOST_USER
    email_message = EmailMessage(
        subject=subject,
        body=html_body,
        from_email=from_email,
        to=[email]
    )
    email_message.content_subtype = "html"
    email_message.send(fail_silently=False)

# verify registration otp
def verify_registration_otp(user_id, otp_code):
    # Validate input
    if not user_id or not otp_code:
        raise ValueError("user_id and otp_code are required.")
    
    # Get OTP from cache
    cache_key = f"register_{user_id}"
    cache_data = cache.get(cache_key)
    
    if not cache_data:
        raise ValueError("OTP code has expired or is invalid.")
    
    cache_data = json.loads(cache_data)
    
    # Verify OTP code
    if cache_data['otp_code'] != otp_code:
        raise ValueError("Invalid OTP code.")
    
    return cache_data

# delete registration otp from cache
def delete_registration_otp_cache(user_id):
    cache_key = f"register_{user_id}"
    cache.delete(cache_key)

# resend registration otp
def resend_registration_otp_email(user_id):
    """
    Resend OTP code for registration
    Args:
        user_id: Primary key of User (int)
    """
    cache_key = f"register_{user_id}"
    cache_data = cache.get(cache_key)
    
    if not cache_data:
        raise ValueError("Account does not exist or the verification process has expired (over 5 minutes).")
    
    cache_data = json.loads(cache_data)
    last_sent = datetime.fromisoformat(cache_data['last_sent'])
    
    # Check if 1 minute has passed
    if datetime.now() - last_sent < timedelta(minutes=1):
        raise ValueError("Please wait at least 1 minute before requesting a new OTP code.")
    
    # Generate new OTP
    new_otp_code = create_otp_code()
    email = cache_data['email']
    
    # Update cache
    cache_data['otp_code'] = new_otp_code
    cache_data['last_sent'] = datetime.now().isoformat()
    cache.set(cache_key, json.dumps(cache_data))
    
    # Resend email
    send_registration_otp_email(email, new_otp_code)