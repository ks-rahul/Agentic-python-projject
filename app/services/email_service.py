"""Email service for sending emails via SMTP or third-party providers."""
import smtplib
import ssl
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from typing import Optional, List, Dict, Any
from jinja2 import Template
import httpx
from abc import ABC, abstractmethod

from app.core.config import settings
from app.core.logging import get_logger

logger = get_logger(__name__)


class EmailProvider(ABC):
    """Abstract base class for email providers."""
    
    @abstractmethod
    async def send(
        self,
        to: List[str],
        subject: str,
        html_content: str,
        text_content: Optional[str] = None,
        from_email: Optional[str] = None,
        from_name: Optional[str] = None,
        reply_to: Optional[str] = None,
        attachments: Optional[List[Dict]] = None
    ) -> bool:
        """Send an email."""
        pass


class SMTPProvider(EmailProvider):
    """SMTP email provider."""
    
    def __init__(self):
        self.host = settings.SMTP_HOST
        self.port = settings.SMTP_PORT
        self.username = settings.SMTP_USERNAME
        self.password = settings.SMTP_PASSWORD
        self.use_tls = settings.SMTP_USE_TLS
    
    async def send(
        self,
        to: List[str],
        subject: str,
        html_content: str,
        text_content: Optional[str] = None,
        from_email: Optional[str] = None,
        from_name: Optional[str] = None,
        reply_to: Optional[str] = None,
        attachments: Optional[List[Dict]] = None
    ) -> bool:
        """Send email via SMTP."""
        try:
            msg = MIMEMultipart("alternative")
            msg["Subject"] = subject
            msg["From"] = f"{from_name or settings.EMAIL_FROM_NAME} <{from_email or settings.EMAIL_FROM_ADDRESS}>"
            msg["To"] = ", ".join(to)
            
            if reply_to:
                msg["Reply-To"] = reply_to
            
            if text_content:
                msg.attach(MIMEText(text_content, "plain"))
            msg.attach(MIMEText(html_content, "html"))
            
            context = ssl.create_default_context()
            
            if self.use_tls:
                with smtplib.SMTP(self.host, self.port) as server:
                    server.starttls(context=context)
                    server.login(self.username, self.password)
                    server.sendmail(from_email or settings.EMAIL_FROM_ADDRESS, to, msg.as_string())
            else:
                with smtplib.SMTP_SSL(self.host, self.port, context=context) as server:
                    server.login(self.username, self.password)
                    server.sendmail(from_email or settings.EMAIL_FROM_ADDRESS, to, msg.as_string())
            
            logger.info("email_sent", to=to, subject=subject)
            return True
            
        except Exception as e:
            logger.error("email_send_failed", error=str(e), to=to, subject=subject)
            return False


class SendGridProvider(EmailProvider):
    """SendGrid email provider."""
    
    def __init__(self):
        self.api_key = settings.SENDGRID_API_KEY
        self.api_url = "https://api.sendgrid.com/v3/mail/send"
    
    async def send(
        self,
        to: List[str],
        subject: str,
        html_content: str,
        text_content: Optional[str] = None,
        from_email: Optional[str] = None,
        from_name: Optional[str] = None,
        reply_to: Optional[str] = None,
        attachments: Optional[List[Dict]] = None
    ) -> bool:
        """Send email via SendGrid API."""
        try:
            payload = {
                "personalizations": [{"to": [{"email": email} for email in to]}],
                "from": {
                    "email": from_email or settings.EMAIL_FROM_ADDRESS,
                    "name": from_name or settings.EMAIL_FROM_NAME
                },
                "subject": subject,
                "content": [{"type": "text/html", "value": html_content}]
            }
            
            if text_content:
                payload["content"].insert(0, {"type": "text/plain", "value": text_content})
            
            if reply_to:
                payload["reply_to"] = {"email": reply_to}
            
            async with httpx.AsyncClient() as client:
                response = await client.post(
                    self.api_url,
                    json=payload,
                    headers={
                        "Authorization": f"Bearer {self.api_key}",
                        "Content-Type": "application/json"
                    }
                )
                
                if response.status_code in [200, 202]:
                    logger.info("email_sent_sendgrid", to=to, subject=subject)
                    return True
                else:
                    logger.error("sendgrid_error", status=response.status_code, response=response.text)
                    return False
                    
        except Exception as e:
            logger.error("email_send_failed", error=str(e), to=to, subject=subject)
            return False


class MailgunProvider(EmailProvider):
    """Mailgun email provider."""
    
    def __init__(self):
        self.api_key = settings.MAILGUN_API_KEY
        self.domain = settings.MAILGUN_DOMAIN
        self.api_url = f"https://api.mailgun.net/v3/{self.domain}/messages"
    
    async def send(
        self,
        to: List[str],
        subject: str,
        html_content: str,
        text_content: Optional[str] = None,
        from_email: Optional[str] = None,
        from_name: Optional[str] = None,
        reply_to: Optional[str] = None,
        attachments: Optional[List[Dict]] = None
    ) -> bool:
        """Send email via Mailgun API."""
        try:
            data = {
                "from": f"{from_name or settings.EMAIL_FROM_NAME} <{from_email or settings.EMAIL_FROM_ADDRESS}>",
                "to": to,
                "subject": subject,
                "html": html_content
            }
            
            if text_content:
                data["text"] = text_content
            
            if reply_to:
                data["h:Reply-To"] = reply_to
            
            async with httpx.AsyncClient() as client:
                response = await client.post(
                    self.api_url,
                    data=data,
                    auth=("api", self.api_key)
                )
                
                if response.status_code == 200:
                    logger.info("email_sent_mailgun", to=to, subject=subject)
                    return True
                else:
                    logger.error("mailgun_error", status=response.status_code, response=response.text)
                    return False
                    
        except Exception as e:
            logger.error("email_send_failed", error=str(e), to=to, subject=subject)
            return False


class EmailService:
    """Main email service that handles email sending with templates."""
    
    def __init__(self):
        self.provider = self._get_provider()
    
    def _get_provider(self) -> EmailProvider:
        """Get the configured email provider."""
        provider_type = getattr(settings, 'EMAIL_PROVIDER', 'smtp').lower()
        
        if provider_type == "sendgrid":
            return SendGridProvider()
        elif provider_type == "mailgun":
            return MailgunProvider()
        else:
            return SMTPProvider()
    
    async def send_email(
        self,
        to: List[str],
        subject: str,
        html_content: str,
        text_content: Optional[str] = None,
        **kwargs
    ) -> bool:
        """Send an email."""
        return await self.provider.send(
            to=to,
            subject=subject,
            html_content=html_content,
            text_content=text_content,
            **kwargs
        )
    
    async def send_template_email(
        self,
        to: List[str],
        subject: str,
        template_name: str,
        context: Dict[str, Any],
        **kwargs
    ) -> bool:
        """Send an email using a template."""
        html_content = self._render_template(template_name, context)
        return await self.send_email(to=to, subject=subject, html_content=html_content, **kwargs)
    
    def _render_template(self, template_name: str, context: Dict[str, Any]) -> str:
        """Render an email template."""
        templates = {
            "verification": self._get_verification_template(),
            "password_reset": self._get_password_reset_template(),
            "welcome": self._get_welcome_template(),
            "notification": self._get_notification_template(),
        }
        
        template_str = templates.get(template_name, templates["notification"])
        template = Template(template_str)
        return template.render(**context)
    
    def _get_verification_template(self) -> str:
        return """
        <!DOCTYPE html>
        <html>
        <head><style>body{font-family:Arial,sans-serif;line-height:1.6;color:#333}.container{max-width:600px;margin:0 auto;padding:20px}.btn{display:inline-block;padding:12px 24px;background:#007bff;color:#fff;text-decoration:none;border-radius:4px}</style></head>
        <body>
        <div class="container">
            <h2>Verify Your Email</h2>
            <p>Hi {{ name }},</p>
            <p>Thank you for registering. Please click the button below to verify your email address:</p>
            <p><a href="{{ verification_url }}" class="btn">Verify Email</a></p>
            <p>Or copy this link: {{ verification_url }}</p>
            <p>This link expires in 24 hours.</p>
            <p>If you didn't create an account, please ignore this email.</p>
        </div>
        </body>
        </html>
        """
    
    def _get_password_reset_template(self) -> str:
        return """
        <!DOCTYPE html>
        <html>
        <head><style>body{font-family:Arial,sans-serif;line-height:1.6;color:#333}.container{max-width:600px;margin:0 auto;padding:20px}.btn{display:inline-block;padding:12px 24px;background:#007bff;color:#fff;text-decoration:none;border-radius:4px}</style></head>
        <body>
        <div class="container">
            <h2>Reset Your Password</h2>
            <p>Hi {{ name }},</p>
            <p>We received a request to reset your password. Click the button below:</p>
            <p><a href="{{ reset_url }}" class="btn">Reset Password</a></p>
            <p>Or copy this link: {{ reset_url }}</p>
            <p>This link expires in 1 hour.</p>
            <p>If you didn't request this, please ignore this email.</p>
        </div>
        </body>
        </html>
        """
    
    def _get_welcome_template(self) -> str:
        return """
        <!DOCTYPE html>
        <html>
        <head><style>body{font-family:Arial,sans-serif;line-height:1.6;color:#333}.container{max-width:600px;margin:0 auto;padding:20px}.btn{display:inline-block;padding:12px 24px;background:#007bff;color:#fff;text-decoration:none;border-radius:4px}</style></head>
        <body>
        <div class="container">
            <h2>Welcome to {{ app_name }}!</h2>
            <p>Hi {{ name }},</p>
            <p>Welcome aboard! Your account has been created successfully.</p>
            <p><a href="{{ login_url }}" class="btn">Get Started</a></p>
            <p>If you have any questions, feel free to reach out to our support team.</p>
        </div>
        </body>
        </html>
        """
    
    def _get_notification_template(self) -> str:
        return """
        <!DOCTYPE html>
        <html>
        <head><style>body{font-family:Arial,sans-serif;line-height:1.6;color:#333}.container{max-width:600px;margin:0 auto;padding:20px}</style></head>
        <body>
        <div class="container">
            <h2>{{ title }}</h2>
            <p>{{ message }}</p>
            {% if action_url %}
            <p><a href="{{ action_url }}" style="display:inline-block;padding:12px 24px;background:#007bff;color:#fff;text-decoration:none;border-radius:4px">{{ action_text or 'View Details' }}</a></p>
            {% endif %}
        </div>
        </body>
        </html>
        """
    
    # Convenience methods
    async def send_verification_email(self, email: str, name: str, verification_url: str) -> bool:
        """Send email verification."""
        logger.info("sending_verification_email", email=email)
        return await self.send_template_email(
            to=[email],
            subject="Verify Your Email Address",
            template_name="verification",
            context={"name": name, "verification_url": verification_url}
        )
    
    async def send_password_reset_email(self, email: str, name: str, reset_url: str) -> bool:
        """Send password reset email."""
        logger.info("sending_password_reset_email", email=email)
        return await self.send_template_email(
            to=[email],
            subject="Reset Your Password",
            template_name="password_reset",
            context={"name": name, "reset_url": reset_url}
        )
    
    async def send_welcome_email(self, email: str, name: str) -> bool:
        """Send welcome email."""
        logger.info("sending_welcome_email", email=email)
        return await self.send_template_email(
            to=[email],
            subject=f"Welcome to {settings.APP_NAME}!",
            template_name="welcome",
            context={
                "name": name,
                "app_name": settings.APP_NAME,
                "login_url": f"{settings.APP_URL}/login"
            }
        )


# Singleton instance
email_service = EmailService()
