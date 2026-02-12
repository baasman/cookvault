"""SMS service for sending verification codes via Twilio."""

import logging
from datetime import datetime, timedelta
from typing import Optional

from flask import current_app
from twilio.rest import Client
from twilio.base.exceptions import TwilioRestException

logger = logging.getLogger(__name__)


class SMSService:
    """Service for sending SMS messages using Twilio."""

    def __init__(self):
        """Initialize SMSService with Twilio client."""
        self.client = None
        self._initialize_client()

    def _initialize_client(self) -> None:
        """Initialize Twilio client from configuration."""
        try:
            account_sid = current_app.config.get("TWILIO_ACCOUNT_SID")
            auth_token = current_app.config.get("TWILIO_AUTH_TOKEN")

            if not account_sid or not auth_token:
                logger.warning(
                    "Twilio credentials not configured - SMS sending disabled"
                )
                return

            self.client = Client(account_sid, auth_token)
            logger.info("Twilio client initialized successfully")
        except Exception as e:
            logger.error(f"Failed to initialize Twilio client: {e}")
            self.client = None

    def _get_from_phone(self) -> Optional[str]:
        """Get the Twilio phone number from configuration."""
        return current_app.config.get("TWILIO_PHONE_NUMBER")

    def send_verification_sms(
        self, phone_number: str, code: str, rate_limit_cache: Optional[dict] = None
    ) -> bool:
        """
        Send SMS verification code to user.

        Args:
            phone_number: User's phone number in E.164 format (e.g., +1234567890)
            code: 6-digit verification code
            rate_limit_cache: Optional cache for rate limiting (phone -> last_sent_time)

        Returns:
            bool: True if SMS sent successfully, False otherwise
        """
        if not self.client:
            logger.error("Twilio client not initialized - cannot send SMS")
            return False

        from_phone = self._get_from_phone()
        if not from_phone:
            logger.error("TWILIO_PHONE_NUMBER not configured - cannot send SMS")
            return False

        # Rate limiting check (stricter for SMS due to cost)
        if rate_limit_cache is not None:
            last_sent = rate_limit_cache.get(phone_number)
            if last_sent:
                time_since_last = datetime.utcnow() - last_sent
                if time_since_last < timedelta(minutes=2):
                    logger.warning(
                        f"Rate limit: SMS to {phone_number} sent less than 2 minutes ago"
                    )
                    return False

        try:
            # Create SMS message
            message_body = (
                f"Your Cookbook Creator verification code is: {code}\n\n"
                f"This code will expire in 10 minutes.\n\n"
                f"If you didn't request this code, please ignore this message."
            )

            # Send SMS
            message = self.client.messages.create(
                body=message_body, from_=from_phone, to=phone_number
            )

            if message.sid:
                logger.info(
                    f"Verification SMS sent successfully to {phone_number}. "
                    f"Message SID: {message.sid}"
                )

                # Update rate limit cache
                if rate_limit_cache is not None:
                    rate_limit_cache[phone_number] = datetime.utcnow()

                return True
            else:
                logger.error(
                    f"Failed to send SMS to {phone_number} - no message SID returned"
                )
                return False

        except TwilioRestException as e:
            logger.error(
                f"Twilio REST error sending SMS to {phone_number}: "
                f"Code {e.code}, Message: {e.msg}",
                exc_info=True,
            )
            return False
        except Exception as e:
            logger.error(
                f"Unexpected error sending SMS to {phone_number}: {e}", exc_info=True
            )
            return False

    def validate_phone_number(self, phone_number: str) -> tuple[bool, Optional[str]]:
        """
        Validate phone number format using phonenumbers library.

        Args:
            phone_number: Phone number to validate

        Returns:
            tuple: (is_valid, formatted_number or error_message)
        """
        try:
            import phonenumbers
            from phonenumbers import NumberParseException

            # Parse the phone number
            try:
                parsed = phonenumbers.parse(phone_number, None)
            except NumberParseException as e:
                return False, f"Invalid phone number format: {e}"

            # Check if the number is valid
            if not phonenumbers.is_valid_number(parsed):
                return False, "Phone number is not valid"

            # Format to E.164 (international format)
            formatted = phonenumbers.format_number(
                parsed, phonenumbers.PhoneNumberFormat.E164
            )

            return True, formatted

        except ImportError:
            logger.error("phonenumbers library not installed")
            # Fallback to basic E.164 validation
            if phone_number.startswith("+") and len(phone_number) >= 10:
                return True, phone_number
            else:
                return False, "Phone number must be in E.164 format (e.g., +1234567890)"
        except Exception as e:
            logger.error(f"Error validating phone number: {e}")
            return False, f"Validation error: {str(e)}"

    def send_password_reset_sms(self, phone_number: str, code: str) -> bool:
        """
        Send SMS with password reset code.

        Args:
            phone_number: User's phone number in E.164 format
            code: Password reset code

        Returns:
            bool: True if SMS sent successfully, False otherwise
        """
        if not self.client:
            logger.error("Twilio client not initialized - cannot send SMS")
            return False

        from_phone = self._get_from_phone()
        if not from_phone:
            logger.error("TWILIO_PHONE_NUMBER not configured - cannot send SMS")
            return False

        try:
            # Create SMS message
            message_body = (
                f"Your Cookbook Creator password reset code is: {code}\n\n"
                f"This code will expire in 10 minutes.\n\n"
                f"If you didn't request this, please secure your account immediately."
            )

            # Send SMS
            message = self.client.messages.create(
                body=message_body, from_=from_phone, to=phone_number
            )

            if message.sid:
                logger.info(
                    f"Password reset SMS sent to {phone_number}. "
                    f"Message SID: {message.sid}"
                )
                return True
            else:
                logger.error(f"Failed to send password reset SMS to {phone_number}")
                return False

        except TwilioRestException as e:
            logger.error(
                f"Twilio error sending password reset SMS to {phone_number}: "
                f"Code {e.code}, Message: {e.msg}"
            )
            return False
        except Exception as e:
            logger.error(
                f"Error sending password reset SMS to {phone_number}: {e}",
                exc_info=True,
            )
            return False


# Singleton instance
_sms_service = None


def get_sms_service() -> SMSService:
    """Get or create the SMSService singleton instance."""
    global _sms_service
    if _sms_service is None:
        _sms_service = SMSService()
    return _sms_service
