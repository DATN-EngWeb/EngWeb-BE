from .models import User

from django.core.cache import cache
from django.core.mail import EmailMessage
from django.conf import settings
from django.core.files.storage import default_storage
from django.core.files.base import ContentFile
from django.utils import timezone

from datetime import timedelta
from email.mime.image import MIMEImage

import random
import os
import uuid
import requests
import json
import time


def create_otp_code():
    digits = "0123456789"
    otp = "".join(random.choice(digits) for i in range(6))

    return otp


def cache_register_otp(user_id, otp_code, email):
    cache_key = f"register_{user_id}"
    cache_data = {
        "otp_code": otp_code,
        "email": email,
        "last_sent": timezone.now().isoformat(),
    }

    cache.set(cache_key, json.dumps(cache_data), timeout=300)


def get_logo_bytes():
    logo_path = os.path.join(settings.BASE_DIR, "static", "logo.png")

    try:
        with open(logo_path, "rb") as logo_file:
            return logo_file.read()
    except FileNotFoundError:
        return None


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


def verify_registration_otp(user_id, otp_code):
    if not user_id or not otp_code:
        raise ValueError("user_id and otp_code are required.")

    cache_key = f"register_{user_id}"
    cache_data = cache.get(cache_key)

    if not cache_data:
        raise ValueError("OTP code has expired or is invalid.")

    cache_data = json.loads(cache_data)

    if cache_data["otp_code"] != otp_code:
        raise ValueError("Invalid OTP code.")

    return cache_data


def delete_registration_otp_cache(user_id):
    cache_key = f"register_{user_id}"
    cache.delete(cache_key)


def resend_registration_otp_email(user_id):
    cache_key = f"register_{user_id}"
    cache_data = cache.get(cache_key)

    # If no cache data (OTP expired after 5 minutes), query user from database and create new OTP
    if not cache_data:
        try:
            user = User.objects.get(id=user_id)
        except User.DoesNotExist:
            raise ValueError("User not found.")

        new_otp_code = create_otp_code()
        cache_data = {
            "otp_code": new_otp_code,
            "email": user.email,
            "last_sent": timezone.now().isoformat()
        }
        cache.set(cache_key, json.dumps(cache_data), timeout=300)
        send_registration_otp_email(user.email, new_otp_code)
        return

    cache_data = json.loads(cache_data)
    last_sent = timezone.datetime.fromisoformat(cache_data["last_sent"])

    if timezone.now() - last_sent < timedelta(minutes=1):
        raise ValueError(
            "Please wait at least 1 minute before requesting a new OTP code."
        )

    new_otp_code = create_otp_code()
    email = cache_data["email"]
    cache_data["otp_code"] = new_otp_code
    cache_data["last_sent"] = timezone.now().isoformat()

    cache.set(cache_key, json.dumps(cache_data), timeout=300)
    send_registration_otp_email(email, new_otp_code)


def get_or_create_file_storage_uuid(user):
    """Folder name with uuid for user's file storage."""
    if not user.file_storage_uuid:
        user.file_storage_uuid = uuid.uuid4()
        user.save(update_fields=["file_storage_uuid"])

    return user.file_storage_uuid


def validate_file_signature(file_obj_or_bytes):
    """Validate file signature (magic numbers) to determine file type."""
    if isinstance(file_obj_or_bytes, bytes):
        header = file_obj_or_bytes[:12]
    else:
        file_obj_or_bytes.seek(0)
        header = file_obj_or_bytes.read(12)
        file_obj_or_bytes.seek(0)

    if not header:
        return None

    if header.startswith(b"%PDF"):
        return "pdf"

    if header[:3] == b"\xff\xd8\xff":
        return "jpeg"

    if header[:4] == b"\x89PNG":
        return "png"

    return None


def process_credential_files_upload(request_files, user):
    """Process credential files upload and return list of credential data."""
    credentials_data = []

    if not request_files:
        raise ValueError("No files provided")

    credential_files = request_files.getlist("teacher.credentials")

    if not credential_files:
        raise ValueError("At least one credential file is required")

    if len(credential_files) > 3:
        raise ValueError("Maximum 3 credential files are allowed")

    file_storage_uuid = get_or_create_file_storage_uuid(user)

    for index, file_obj in enumerate(credential_files):
        if not file_obj:
            raise ValueError(f"Credential file at index {index} is missing")

        if file_obj.size > 5 * 1024 * 1024:
            raise ValueError(f"Credential file '{file_obj.name}' exceeds 5MB limit")

        valid_content_types = ["application/pdf", "image/jpeg", "image/png"]

        if file_obj.content_type not in valid_content_types:
            raise ValueError(
                f"Credential file '{file_obj.name}' has invalid content type: {file_obj.content_type}"
            )

        file_type = validate_file_signature(file_obj)

        if file_type not in ["pdf", "jpeg", "png"]:
            raise ValueError(
                f"Credential file '{file_obj.name}' has invalid file signature"
            )

        extension_map = {"pdf": ".pdf", "jpeg": ".jpg", "png": ".png"}
        file_extension = extension_map[file_type]
        filename = f"credential_{index}{file_extension}"
        storage_relative_path = f"teachers/credentials/{file_storage_uuid}/{filename}"
        saved_path = default_storage.save(storage_relative_path, file_obj)
        relative_url = saved_path

        credentials_data.append(
            {
                "id": index,
                "url": relative_url,
                "name": file_obj.name,
                "type": file_obj.content_type,
                "size": file_obj.size,
            }
        )

    return credentials_data


def download_and_save_avatar(avatar_url, user):
    try:
        response = requests.get(avatar_url, stream=True, timeout=10)

        if response.status_code == 200:
            content_type = response.headers.get("Content-Type", "")

            if "image/jpeg" not in content_type and "image/png" not in content_type:
                return None

            image_type = validate_file_signature(response.content)
            if image_type not in ["jpeg", "png"]:
                return None

            file_extension = "jpg" if image_type == "jpeg" else "png"
            file_storage_uuid = get_or_create_file_storage_uuid(user)
            filename = f"{file_storage_uuid}.{file_extension}"
            folder_path = f"users/avatars/{file_storage_uuid}"
            file_path = f"{folder_path}/{filename}"
            image_content = ContentFile(response.content)

            default_storage.save(file_path, image_content)

            return file_path
        else:
            return None
    except Exception:
        return None


def generate_unique_username(base_username):
    if not User.objects.filter(username=base_username).exists():
        return base_username

    timestamp = int(time.time())
    random_uuid = str(uuid.uuid4()).replace("-", "")[:8]
    unique_suffix = f"{timestamp}_{random_uuid}"
    new_username = f"{base_username}_{unique_suffix}"

    max_length = 50
    if len(new_username) > max_length:
        available_length = max_length - len(unique_suffix) - 1
        base_username = base_username[:available_length]
        new_username = f"{base_username}_{unique_suffix}"

    return new_username


def cache_forgot_password_otp(username, otp_code):
    cache_key = f"forgot_password_{username}"
    cache_data = {"otp_code": otp_code, "last_sent": timezone.now().isoformat()}

    cache.set(cache_key, json.dumps(cache_data), timeout=300)


def send_forgot_password_otp_email(username, email, otp_code):
    logo_data = get_logo_bytes()
    logo_cid = "nens-logo"
    logo_html = (
        f'<img src="cid:{logo_cid}" alt="NENS Logo" style="max-width: 120px; height: auto; margin-bottom: 20px;" />'
        if logo_data
        else ""
    )
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
                {logo_html}
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

    if logo_data:
        logo_image = MIMEImage(logo_data)
        logo_image.add_header("Content-ID", "<logo>")
        logo_image.add_header("Content-Disposition", "inline", filename="logo.png")
        email_message.attach(logo_image)

    email_message.send(fail_silently=False)


def verify_forgot_password_otp(username, otp_code):
    if not username or not otp_code:
        raise ValueError("Username and OTP code are required.")

    cache_key = f"forgot_password_{username}"
    cache_data = cache.get(cache_key)

    if not cache_data:
        raise ValueError("OTP code has expired or is invalid.")

    cache_data = json.loads(cache_data)

    if cache_data["otp_code"] != otp_code:
        raise ValueError("Invalid OTP code.")

    return cache_data


def delete_forgot_password_otp_cache(username):
    cache_key = f"forgot_password_{username}"
    cache.delete(cache_key)


def resend_forgot_password_otp_email(username):
    cache_key = f"forgot_password_{username}"
    cache_data = cache.get(cache_key)

    # If no cache data (OTP expired after 5 minutes), query user from database and create new OTP
    if not cache_data:
        try:
            user = User.objects.get(username=username)
        except User.DoesNotExist:
            raise ValueError("User not found.")

        new_otp_code = create_otp_code()
        cache_data = {
            "otp_code": new_otp_code,
            "last_sent": timezone.now().isoformat()
        }
        cache.set(cache_key, json.dumps(cache_data), timeout=300)
        send_forgot_password_otp_email(username, user.email, new_otp_code)
        return

    cache_data = json.loads(cache_data)
    last_sent = timezone.datetime.fromisoformat(cache_data["last_sent"])

    if timezone.now() - last_sent < timedelta(minutes=1):
        raise ValueError("Please wait 1 minute before requesting a new OTP code.")

    cache.delete(cache_key)

    new_otp_code = create_otp_code()
    cache_data["otp_code"] = new_otp_code
    cache_data["last_sent"] = timezone.now().isoformat()

    cache.set(cache_key, json.dumps(cache_data), timeout=300)

    try:
        user = User.objects.get(username=username)
        send_forgot_password_otp_email(username, user.email, new_otp_code)
    except User.DoesNotExist:
        raise ValueError("User not found.")


def get_absolute_media_url(media_field):
    if not media_field:
        return None

    # string path
    if isinstance(media_field, str):
        if media_field.startswith("http"):
            return media_field

        base = getattr(settings, "MEDIA_URL", "")

        if not base.endswith("/"):
            base = f"{base}/"

        return f"{base}{media_field.lstrip('/')}"

    # ImageField/FileField
    try:
        return media_field.url
    except Exception:
        return None


def delete_user_storage_folder(user):
    if not user.file_storage_uuid:
        return

    # Delete credentials from teacher profile if exists
    try:
        if user.role == "T":
            teacher = user.teacher
            credentials = (
                teacher.credentials if isinstance(teacher.credentials, list) else []
            )
            for cred in credentials:
                if isinstance(cred, dict) and cred.get("url"):
                    cred_url = cred.get("url")
                    try:
                        default_storage.delete(cred_url)
                    except Exception:
                        pass  # Ignore errors when deleting individual files
    except Exception:
        pass  # Teacher doesn't exist or not a teacher

    # Delete avatar if not default
    if user.avatar and str(user.avatar) != "users/avatars/default-avatar.jpg":
        try:
            default_storage.delete(str(user.avatar))
        except Exception:
            pass

    # Delete cover if not default
    if user.cover and str(user.cover) != "users/covers/default-cover.jpg":
        try:
            default_storage.delete(str(user.cover))
        except Exception:
            pass


def send_status_update_email(email, full_name, action):
    logo_data = get_logo_bytes()
    logo_cid = "nens-logo"
    logo_html = (
        f'<img src="cid:{logo_cid}" alt="NENS Logo" style="max-width: 120px; height: auto; margin-bottom: 20px;" />'
        if logo_data
        else ""
    )

    action_details = {
        "enabled": {
            "subject": "Your account has been enabled",
            "title": "Account Enabled",
            "message": "Your account has been enabled by the administrator. You can now log in and access all features.",
            "color": "#4CAF50"
        },
        "disabled": {
            "subject": "Your account has been disabled",
            "title": "Account Disabled",
            "message": "Your account has been disabled by the administrator. If you believe this is a mistake, please contact support.",
            "color": "#F44336"
        },
        "approved": {
            "subject": "Your teacher profile has been approved",
            "title": "Profile Approved",
            "message": "Congratulations! Your teacher profile has been approved by the administrator. You can now start teaching on NENS.",
            "color": "#4CAF50"
        },
        "rejected": {
            "subject": "Your teacher profile has been rejected",
            "title": "Profile Rejected",
            "message": "We regret to inform you that your teacher profile has been rejected by the administrator. As a result, your account has been removed. Please contact support for more details or submit a new application.",
            "color": "#F44336"
        }
    }

    details = action_details.get(action)
    if not details:
        return

    subject = f"{details['subject']} - NENS"
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
                color: {details['color']};
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
            .info-box {{
                background-color: #f8f9fa;
                padding: 20px;
                border-radius: 8px;
                margin: 30px 0;
                border-left: 4px solid {details['color']};
                text-align: center;
            }}
            .info-box p {{
                margin: 0;
                font-size: 16px;
                font-weight: 500;
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
                <h1>{details['title']}</h1>
                <p>Hi {full_name},</p>
                
                <div class="info-box">
                    <p>{details['message']}</p>
                </div>
                
                <p>If you have any questions, feel free to contact our support team at <a href="mailto:nens.hcmus@gmail.com" style="color: #FF854B; text-decoration: none; font-weight: bold;">nens.hcmus@gmail.com</a>.</p>
                
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

    try:
        email_message.send(fail_silently=False)
    except Exception as e:
        import logging
        logger = logging.getLogger(__name__)
        logger.error(f"Failed to send status update email: {e}")

