import random
import os
import uuid
import requests
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
    otp = "".join(random.choice(digits) for i in range(6))

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
        "otp_code": otp_code,
        "email": email,
        "last_sent": datetime.now().isoformat(),
    }

    cache.set(cache_key, json.dumps(cache_data), timeout=300)


# get logo bytes for email embedding (attached image)
def get_logo_bytes():
    """Read logo file and return raw bytes for inline attachment"""
    logo_path = os.path.join(settings.BASE_DIR, "static", "logo.png")
    try:
        with open(logo_path, "rb") as logo_file:
            return logo_file.read()
    except FileNotFoundError:
        return None


# send otp code to email
def send_registration_otp_email(email, otp_code):
    logo_data = get_logo_bytes()
    logo_cid = "nens-logo"
    logo_html = (
        f'<img src="cid:{logo_cid}" alt="NENS Logo" style="max-width: 120px; height: auto; margin-bottom: 20px;" />'
        if logo_data
        else ""
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
        subject=subject, body=html_body, from_email=from_email, to=[email]
    )
    email_message.content_subtype = "html"
    if logo_data:
        image = MIMEImage(logo_data)
        image.add_header("Content-ID", f"<{logo_cid}>")
        image.add_header("Content-Disposition", "inline", filename="logo.png")
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
    if cache_data["otp_code"] != otp_code:
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
        raise ValueError(
            "Account does not exist or the verification process has expired (over 5 minutes)."
        )

    cache_data = json.loads(cache_data)
    last_sent = datetime.fromisoformat(cache_data["last_sent"])

    # Check if 1 minute has passed
    if datetime.now() - last_sent < timedelta(minutes=1):
        raise ValueError(
            "Please wait at least 1 minute before requesting a new OTP code."
        )

    # Generate new OTP
    new_otp_code = create_otp_code()
    email = cache_data["email"]

    # Update cache
    cache_data["otp_code"] = new_otp_code
    cache_data["last_sent"] = datetime.now().isoformat()
    cache.set(cache_key, json.dumps(cache_data), timeout=300)

    # Resend email
    send_registration_otp_email(email, new_otp_code)


# Validate file signature/magic numbers to prevent spoofed uploads
def validate_file_signature(file_obj_or_bytes):
    """
    Validate file by checking its magic number (file signature).
    Prevents malicious users from uploading executables disguised as PDFs/images.

    Args:
        file_obj_or_bytes: Django UploadedFile object or bytes content

    Returns:
        str: File type if valid ('pdf', 'jpeg', 'png'), None if invalid
    """
    # Handle both file objects and bytes
    if isinstance(file_obj_or_bytes, bytes):
        header = file_obj_or_bytes[:12]
    else:
        # Django UploadedFile object
        file_obj_or_bytes.seek(0)
        header = file_obj_or_bytes.read(12)
        file_obj_or_bytes.seek(0)

    if not header:
        return None

    # Magic number validation (file signatures)
    # PDF: %PDF (0x25 0x50 0x44 0x46)
    if header.startswith(b"%PDF"):
        return "pdf"

    # JPEG: FF D8 FF (all JPEG variants)
    if header[:3] == b"\xff\xd8\xff":
        return "jpeg"

    # PNG: 89 50 4E 47
    if header[:4] == b"\x89PNG":
        return "png"

    return None


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
    credential_files = request_files.getlist("credentials")

    if not credential_files:
        return credentials_data

    # Create directory for user's credentials
    credentials_dir = os.path.join(
        settings.MEDIA_ROOT, "credentials", f"user_{user_id}"
    )
    os.makedirs(credentials_dir, exist_ok=True)

    for index, file_obj in enumerate(credential_files):
        if not file_obj:
            continue

        # Validate file size first (5MB max)
        if file_obj.size > 5 * 1024 * 1024:
            continue

        # Validate content type (header check - can be spoofed)
        valid_content_types = ["application/pdf", "image/jpeg", "image/png"]
        if file_obj.content_type not in valid_content_types:
            continue

        # Validate file signature (magic numbers - cannot be spoofed)
        file_type = validate_file_signature(file_obj)
        if file_type not in ["pdf", "jpeg", "png"]:
            # File signature doesn't match claimed content type
            continue

        # Generate filename
        extension_map = {"pdf": ".pdf", "jpeg": ".jpg", "png": ".png"}

        file_extension = extension_map[file_type]
        filename = f"cert_{index}{file_extension}"
        file_path = os.path.join(credentials_dir, filename)

        # Save file
        with open(file_path, "wb") as f:
            for chunk in file_obj.chunks():
                f.write(chunk)

        # Create relative URL for database storage
        relative_url = f"credentials/user_{user_id}/{filename}"

        # Add to credentials data
        credentials_data["certificates"].append(
            {
                "url": relative_url,
                "name": file_obj.name,
                "type": file_obj.content_type,
                "size": file_obj.size,
            }
        )

    return credentials_data


def cache_forgot_password_otp(username, otp_code):
    cache_key = f"forgot_password_{username}"
    cache_data = {"otp_code": otp_code, "last_sent": datetime.now().isoformat()}

    cache.set(cache_key, json.dumps(cache_data), timeout=300)  # 5 minutes


def send_forgot_password_otp_email(username, email, otp_code):
    logo_data = get_logo_bytes()

    subject = "Password Reset OTP - NENS"
    html_body = f"""
    <!DOCTYPE html>
    <html>
    <head>
        <meta charset="UTF-8">
        <style>
            body {{
                font-family: Arial, sans-serif;
                background-color: #f4f4f4;
                margin: 0;
                padding: 0;
            }}
            .container {{
                max-width: 600px;
                margin: 0 auto;
                background-color: #ffffff;
                padding: 30px;
                border-radius: 8px;
                box-shadow: 0 2px 4px rgba(0,0,0,0.1);
            }}
            .header {{
                text-align: center;
                margin-bottom: 30px;
            }}
            .logo {{
                max-width: 120px;
                height: auto;
            }}
            h1 {{
                color: #333;
                font-size: 24px;
                margin-bottom: 20px;
            }}
            p {{
                color: #666;
                font-size: 16px;
                line-height: 1.6;
                margin-bottom: 15px;
            }}
            .otp-container {{
                background-color: #f8f9fa;
                border: 2px dashed #007bff;
                border-radius: 8px;
                padding: 20px;
                text-align: center;
                margin: 30px 0;
            }}
            .otp-code {{
                font-size: 32px;
                font-weight: bold;
                color: #007bff;
                letter-spacing: 8px;
                font-family: 'Courier New', monospace;
            }}
            .warning {{
                background-color: #fff3cd;
                border-left: 4px solid #ffc107;
                padding: 15px;
                margin: 20px 0;
                border-radius: 4px;
            }}
            .footer {{
                margin-top: 30px;
                padding-top: 20px;
                border-top: 1px solid #eee;
                text-align: center;
                color: #999;
                font-size: 14px;
            }}
        </style>
    </head>
    <body>
        <div class="container">
            <div class="header">
                {'<img src="cid:logo" alt="NENS Logo" class="logo">' if logo_data else ''}
            </div>
            <h1>Password Reset Request</h1>
            <p>Hello {username},</p>
            <p>We received a request to reset your password. Please use the OTP code below to verify your identity:</p>
            
            <div class="otp-container">
                <p style="margin: 0 0 10px 0; color: #333; font-weight: 600;">Your OTP Code:</p>
                <div class="otp-code">{otp_code}</div>
            </div>
            
            <div class="warning">
                <strong>⚠️ Important:</strong> This OTP code will expire in 5 minutes. If you didn't request a password reset, please ignore this email.
            </div>
            
            <p>After verifying the OTP, you'll be able to set a new password for your account.</p>
            
            <div class="footer">
                <p>Best regards,<br>The NENS Team</p>
                <p style="font-size: 12px; color: #999;">This is an automated email. Please do not reply.</p>
            </div>
        </div>
    </body>
    </html>
    """

    from_email = settings.EMAIL_HOST_USER
    email_message = EmailMessage(
        subject=subject, body=html_body, from_email=from_email, to=[email]
    )
    email_message.content_subtype = "html"

    # Attach logo if available
    if logo_data:
        logo_image = MIMEImage(logo_data)
        logo_image.add_header("Content-ID", "<logo>")
        logo_image.add_header("Content-Disposition", "inline", filename="logo.png")
        email_message.attach(logo_image)

    email_message.send(fail_silently=False)


def resend_forgot_password_otp_email(username):
    cache_key = f"forgot_password_{username}"
    cache_data = cache.get(cache_key)

    if not cache_data:
        raise ValueError(
            "Account not found or verification process has expired (over 5 minutes). "
            "Please return to the login page and select 'Forgot Password' again."
        )

    cache_data = json.loads(cache_data)
    last_sent = datetime.fromisoformat(cache_data["last_sent"])

    # Rate limit: 1 minute between resends
    if datetime.now() - last_sent < timedelta(minutes=1):
        raise ValueError("Please wait 1 minute before requesting a new OTP code.")

    # Delete old cache and create new OTP
    cache.delete(cache_key)

    new_otp_code = create_otp_code()

    cache_data["otp_code"] = new_otp_code
    cache_data["last_sent"] = datetime.now().isoformat()

    cache.set(cache_key, json.dumps(cache_data), timeout=300)

    # Get user email
    from .models import User

    try:
        user = User.objects.get(username=username)
        send_forgot_password_otp_email(username, user.email, new_otp_code)
    except User.DoesNotExist:
        raise ValueError("User not found.")


# download and save avatar from social account when user hasn't existed in database
def download_and_save_avatar(avatar_url, user_id):
    """
    Download avatar image from URL and save to media/avatars/user_{user_id}/user_{user_id}.{ext}
    Returns relative path to saved file or None if failed
    """
    try:
        response = requests.get(avatar_url, stream=True, timeout=10)

        if response.status_code == 200:
            content_type = response.headers.get("Content-Type", "")

            # Validate content type header (can be spoofed)
            if "image/jpeg" not in content_type and "image/png" not in content_type:
                return None

            # Validate image signature (magic numbers - cannot be spoofed)
            image_type = validate_file_signature(response.content)
            if image_type not in ["jpeg", "png"]:
                return None

            # Map validated type to file extension
            file_extension = "jpg" if image_type == "jpeg" else "png"

            # Directory and filename pattern similar to credentials: avatars/user_{id}/user_{id}.ext
            filename = f"user_{user_id}.{file_extension}"
            folder_path = f"avatars/user_{user_id}"
            file_path = f"{folder_path}/{filename}"

            image_content = ContentFile(response.content)
            default_storage.save(file_path, image_content)

            return file_path
        else:
            return None
    except Exception:
        return None


def generate_unique_username(base_username):
    """
    Create a unique username by using UUID and timestamp
    - base_username: base username (usually the part before @ of email)
    - if username already exists, add an underscore and a string of UUID + timestamp to ensure uniqueness
    """
    from .models import User

    # check if base username already exists
    if not User.objects.filter(username=base_username).exists():
        return base_username

    # generate unique suffix
    timestamp = int(time.time())
    random_uuid = str(uuid.uuid4()).replace("-", "")[
        :8
    ]  # shorten UUID to avoid being too long

    unique_suffix = f"{timestamp}_{random_uuid}"
    new_username = f"{base_username}_{unique_suffix}"

    # ensure username is not too long
    max_length = 50
    if len(new_username) > max_length:
        # cut base_username if needed
        available_length = max_length - len(unique_suffix) - 1  # -1 for underscore
        base_username = base_username[:available_length]
        new_username = f"{base_username}_{unique_suffix}"

    return new_username
