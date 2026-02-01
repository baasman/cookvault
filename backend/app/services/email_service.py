"""Email service for sending verification and transactional emails."""
import logging
from datetime import datetime, timedelta
from typing import Optional

from flask import current_app, render_template
from sendgrid import SendGridAPIClient
from sendgrid.helpers.mail import Mail, To, From, Content

logger = logging.getLogger(__name__)


class EmailService:
    """Service for sending emails using SendGrid."""

    def __init__(self):
        """Initialize EmailService with SendGrid client."""
        self.client = None
        self._initialize_client()

    def _initialize_client(self) -> None:
        """Initialize SendGrid client from configuration."""
        try:
            api_key = current_app.config.get("SENDGRID_API_KEY")
            if not api_key:
                logger.warning("SENDGRID_API_KEY not configured - email sending disabled")
                return

            self.client = SendGridAPIClient(api_key)
            logger.info("SendGrid client initialized successfully")
        except Exception as e:
            logger.error(f"Failed to initialize SendGrid client: {e}")
            self.client = None

    def _get_from_email(self) -> str:
        """Get the from email address from configuration."""
        return current_app.config.get("EMAIL_FROM_ADDRESS", "noreply@cookbook-creator.com")

    def _get_from_name(self) -> str:
        """Get the from name from configuration."""
        return current_app.config.get("EMAIL_FROM_NAME", "Cookbook Creator")

    def _get_frontend_url(self) -> str:
        """Get the frontend URL from configuration."""
        return current_app.config.get("FRONTEND_URL", "http://localhost:5173")

    def _get_recipient_email(self, email: str) -> str:
        """Get the recipient email, applying dev override if configured.

        In development, all emails can be redirected to a single address
        for testing purposes by setting DEV_EMAIL_OVERRIDE.
        """
        dev_override = current_app.config.get("DEV_EMAIL_OVERRIDE")
        if dev_override:
            logger.info(f"DEV_EMAIL_OVERRIDE active: redirecting email from {email} to {dev_override}")
            return dev_override
        return email

    def send_verification_email(
        self,
        email: str,
        token: str,
        username: str,
        rate_limit_cache: Optional[dict] = None
    ) -> bool:
        """
        Send email verification email to user.

        Args:
            email: User's email address
            token: Verification token
            username: User's username
            rate_limit_cache: Optional cache for rate limiting (email -> last_sent_time)

        Returns:
            bool: True if email sent successfully, False otherwise
        """
        if not self.client:
            logger.error("SendGrid client not initialized - cannot send email")
            return False

        # Rate limiting check
        if rate_limit_cache is not None:
            last_sent = rate_limit_cache.get(email)
            if last_sent:
                time_since_last = datetime.utcnow() - last_sent
                if time_since_last < timedelta(minutes=5):
                    logger.warning(f"Rate limit: Email to {email} sent less than 5 minutes ago")
                    return False

        try:
            # Build verification URL
            frontend_url = self._get_frontend_url()
            verification_url = f"{frontend_url}/verify-email?token={token}"

            # Render HTML email template
            try:
                html_content = render_template(
                    "verification_email.html",
                    username=username,
                    verification_url=verification_url,
                    expiry_hours=24
                )
            except Exception as template_error:
                logger.warning(f"Failed to render template, using fallback: {template_error}")
                # Fallback to simple HTML if template fails
                html_content = f"""
                <html>
                  <body>
                    <h2>Welcome to Cookbook Creator, {username}!</h2>
                    <p>Please verify your email address by clicking the link below:</p>
                    <p><a href="{verification_url}">Verify Email Address</a></p>
                    <p>This link will expire in 24 hours.</p>
                    <p>If you didn't create an account, please ignore this email.</p>
                  </body>
                </html>
                """

            # Plain text version
            text_content = f"""
            Welcome to Cookbook Creator, {username}!

            Please verify your email address by visiting this link:
            {verification_url}

            This link will expire in 24 hours.

            If you didn't create an account, please ignore this email.
            """

            # Get recipient (may be overridden in dev)
            recipient = self._get_recipient_email(email)

            # Create message
            message = Mail(
                from_email=From(self._get_from_email(), self._get_from_name()),
                to_emails=To(recipient),
                subject="Verify Your Email - Cookbook Creator",
                plain_text_content=Content("text/plain", text_content),
                html_content=Content("text/html", html_content)
            )

            # Send email
            response = self.client.send(message)

            if response.status_code in [200, 201, 202]:
                logger.info(f"Verification email sent successfully to {recipient} (original: {email})")

                # Update rate limit cache
                if rate_limit_cache is not None:
                    rate_limit_cache[email] = datetime.utcnow()

                return True
            else:
                logger.error(
                    f"Failed to send email to {email}. "
                    f"Status: {response.status_code}, Body: {response.body}"
                )
                return False

        except Exception as e:
            logger.error(f"Error sending verification email to {email}: {e}", exc_info=True)
            return False

    def send_password_reset_email(
        self,
        email: str,
        token: str,
        username: str
    ) -> bool:
        """
        Send password reset email to user.

        Args:
            email: User's email address
            token: Password reset token
            username: User's username

        Returns:
            bool: True if email sent successfully, False otherwise
        """
        if not self.client:
            logger.error("SendGrid client not initialized - cannot send email")
            return False

        try:
            # Build reset URL
            frontend_url = self._get_frontend_url()
            reset_url = f"{frontend_url}/reset-password?token={token}"

            # Simple HTML email
            html_content = f"""
            <html>
              <body style="font-family: Arial, sans-serif; line-height: 1.6; color: #333;">
                <div style="max-width: 600px; margin: 0 auto; padding: 20px;">
                  <h2 style="color: #2c3e50;">Password Reset Request</h2>
                  <p>Hello {username},</p>
                  <p>We received a request to reset your password for your Cookbook Creator account.</p>
                  <p style="margin: 30px 0;">
                    <a href="{reset_url}"
                       style="background-color: #3498db; color: white; padding: 12px 30px;
                              text-decoration: none; border-radius: 5px; display: inline-block;">
                      Reset Password
                    </a>
                  </p>
                  <p>This link will expire in 24 hours.</p>
                  <p style="color: #e74c3c; margin-top: 20px;">
                    <strong>If you didn't request this, please ignore this email.</strong>
                    Your password will remain unchanged.
                  </p>
                  <hr style="border: none; border-top: 1px solid #eee; margin: 30px 0;">
                  <p style="font-size: 12px; color: #7f8c8d;">
                    Cookbook Creator - Your Digital Recipe Collection
                  </p>
                </div>
              </body>
            </html>
            """

            # Plain text version
            text_content = f"""
            Hello {username},

            We received a request to reset your password for your Cookbook Creator account.

            Please visit this link to reset your password:
            {reset_url}

            This link will expire in 24 hours.

            If you didn't request this, please ignore this email. Your password will remain unchanged.

            ---
            Cookbook Creator - Your Digital Recipe Collection
            """

            # Get recipient (may be overridden in dev)
            recipient = self._get_recipient_email(email)

            # Create message
            message = Mail(
                from_email=From(self._get_from_email(), self._get_from_name()),
                to_emails=To(recipient),
                subject="Reset Your Password - Cookbook Creator",
                plain_text_content=Content("text/plain", text_content),
                html_content=Content("text/html", html_content)
            )

            # Send email
            response = self.client.send(message)

            if response.status_code in [200, 201, 202]:
                logger.info(f"Password reset email sent successfully to {recipient} (original: {email})")
                return True
            else:
                logger.error(
                    f"Failed to send password reset email to {email}. "
                    f"Status: {response.status_code}"
                )
                return False

        except Exception as e:
            logger.error(f"Error sending password reset email to {email}: {e}", exc_info=True)
            return False


# Singleton instance
_email_service = None


def get_email_service() -> EmailService:
    """Get or create the EmailService singleton instance."""
    global _email_service
    if _email_service is None:
        _email_service = EmailService()
    return _email_service
