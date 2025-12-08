import random
import os
from django.core.cache import cache
from django.core.mail import EmailMessage
from django.conf import settings
from datetime import datetime, timedelta
import json
import time
from email.mime.image import MIMEImage
from django.core.files.storage import default_storage
from django.core.files.base import ContentFile

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

# get logo bytes for email embedding (attached image)
def get_logo_bytes():
    """Read logo file and return raw bytes for inline attachment"""
    logo_path = os.path.join(settings.BASE_DIR, 'static', 'logo.png')
    try:
        with open(logo_path, 'rb') as logo_file:
            return logo_file.read()
    except FileNotFoundError:
        return None

# send otp code to email
def send_registration_otp_email(email, otp_code):
    logo_data = get_logo_bytes()
    logo_cid = 'nens-logo'
    logo_html = (
        f'<img src="cid:{logo_cid}" alt="NENS Logo" style="max-width: 120px; height: auto; margin-bottom: 20px;" />'
        if logo_data
        else ''
    )
    
    subject = "Your NENS verification code"
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
                <h1>Verify your email to get started</h1>
                <p>Hi there,</p>
                <p>Welcome to NENS! Use the code below to confirm your email and finish setting up your account.</p>
                
                <div class="otp-container">
                    <div class="otp-code">{otp_code}</div>
                </div>
                
                <div class="info-box">
                    <p><strong>Quick notes:</strong></p>
                    <p>• The code expires in 5 minutes</p>
                    <p>• Please keep it private — never share it with anyone</p>
                    <p>• Didn’t request this? You can safely ignore this email</p>
                </div>
                
                <p>Enter the code on the verification page to complete your signup. If you run into any issues, just request a new code from the app.</p>
                
                <div class="footer">
                    <p>Thank you for choosing NENS.</p>
                    <div class="footer-brand">NENS — No English No Success</div>
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
    if logo_data:
        image = MIMEImage(logo_data)
        image.add_header('Content-ID', f'<{logo_cid}>')
        image.add_header('Content-Disposition', 'inline', filename='logo.png')
        email_message.attach(image)
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

# Process and save credential files
def process_credential_files(request_files, user_id):
    """
    Process multiple credential files from request and save them to media folder.
    Returns a JSON structure with file metadata.
    
    Args:
        request_files: QueryDict from request.FILES containing 'credentials' files
        user_id: User ID for creating folder structure
    
    Returns:
        dict: JSON structure with credentials metadata
        {
            "certificates": [
                {
                    "url": "media/credentials/user_1/cert_0.pdf",
                    "name": "certificate.pdf",
                    "type": "application/pdf",
                    "size": 12345
                },
                ...
            ]
        }
    """
    credentials_data = {"certificates": []}
    
    if not request_files:
        return credentials_data
    
    # Get all files with key 'credentials'
    credential_files = request_files.getlist('credentials')
    
    if not credential_files:
        return credentials_data
    
    # Create directory for user's credentials
    credentials_dir = os.path.join(settings.MEDIA_ROOT, 'credentials', f'user_{user_id}')
    os.makedirs(credentials_dir, exist_ok=True)
    
    for index, file_obj in enumerate(credential_files):
        if not file_obj:
            continue
            
        # Validate file type
        valid_types = ['application/pdf', 'image/jpeg', 'image/png', 'image/jpg']
        if file_obj.content_type not in valid_types:
            continue
        
        # Validate file size (5MB max)
        if file_obj.size > 5 * 1024 * 1024:
            continue
        
        # Generate filename
        file_extension = os.path.splitext(file_obj.name)[1] or '.pdf'
        filename = f'cert_{index}{file_extension}'
        file_path = os.path.join(credentials_dir, filename)
        
        # Save file
        with open(file_path, 'wb') as f:
            for chunk in file_obj.chunks():
                f.write(chunk)
        
        # Create relative URL for database storage
        relative_url = f'credentials/user_{user_id}/{filename}'
        
        # Add to credentials data
        credentials_data["certificates"].append({
            "url": relative_url,
            "name": file_obj.name,
            "type": file_obj.content_type,
            "size": file_obj.size
        })
    
    return credentials_data