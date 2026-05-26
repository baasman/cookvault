"""
Lulu Print API Service

This service handles all interactions with the Lulu Print API including:
- OAuth2 authentication
- Print job creation and management
- Cost calculations
- File validation
- Order tracking
"""

import base64
import hashlib
import hmac
import logging
import time
from datetime import datetime, timedelta
from decimal import Decimal
from typing import Dict, Any, Optional, List, Tuple
from urllib.parse import urljoin

import requests
from flask import current_app
from requests.exceptions import RequestException, Timeout

from app.models.print_order import (
    PrintOrder,
    PrintSpecification,
    TrimSize,
    BindingType,
    PaperType,
)

logger = logging.getLogger(__name__)


class LuluAPIError(Exception):
    """Custom exception for Lulu API errors."""

    def __init__(
        self,
        message: str,
        status_code: Optional[int] = None,
        response_data: Optional[Dict] = None,
    ):
        super().__init__(message)
        self.status_code = status_code
        self.response_data = response_data
        self.is_retryable = self._determine_retryable()

    def _determine_retryable(self) -> bool:
        """Determine if this error is retryable based on status code."""
        if not self.status_code:
            return False

        # Retryable errors
        if self.status_code in [
            429,
            502,
            503,
            504,
        ]:  # Rate limit, bad gateway, service unavailable
            return True
        if self.status_code >= 500:  # Other server errors
            return True

        # Non-retryable errors
        return False

    def get_retry_delay(self) -> int:
        """Get recommended retry delay in seconds."""
        if self.status_code == 429:
            return 60  # Rate limit - wait longer
        elif self.status_code >= 500:
            return 5  # Server error - shorter wait
        return 1


class LuluAuthenticationError(LuluAPIError):
    """Authentication-specific error."""

    pass


class LuluValidationError(LuluAPIError):
    """File validation error."""

    def __init__(
        self, message: str, validation_errors: Optional[List] = None, **kwargs
    ):
        super().__init__(message, **kwargs)
        self.validation_errors = validation_errors or []


class LuluQuotaExceededError(LuluAPIError):
    """API quota exceeded error."""

    pass


class LuluServiceUnavailableError(LuluAPIError):
    """Service temporarily unavailable."""

    pass


class LuluService:
    """Service for interacting with Lulu Print API."""

    # Lulu's POD package IDs are a single 27-character SKU encoding trim,
    # color, print quality, binding, paper weight + color, finish, and
    # laminate. We can't build them from per-attribute pieces — Lulu only
    # accepts a small set of pre-validated full SKUs. Hardcoded table is the
    # simplest correct approach; missing combinations raise a clear error.
    #
    # Reference: https://developers.lulu.com/product-data
    # SKU format: <trim mm 9-char> <BW|FC> <paper-prefix 3> <binding 2>
    #             <weight 3> <paper-color 2> <finish 3> <laminate 3>
    POD_PACKAGE_IDS = {
        # (trim, binding, paper, color_pages): SKU
        (TrimSize.A5, BindingType.PERFECT_BOUND, PaperType.STANDARD_WHITE, False):
            "0148X0210BWSTDPB060UW444MNG",
        (TrimSize.A5, BindingType.PERFECT_BOUND, PaperType.STANDARD_CREAM, False):
            "0148X0210BWSTDPB060UC444MNG",
        (TrimSize.US_TRADE, BindingType.PERFECT_BOUND, PaperType.STANDARD_WHITE, False):
            "0600X0900BWSTDPB060UW444MNG",
        (TrimSize.US_TRADE, BindingType.PERFECT_BOUND, PaperType.STANDARD_CREAM, False):
            "0600X0900BWSTDPB060UC444MNG",
        (TrimSize.DIGEST, BindingType.PERFECT_BOUND, PaperType.STANDARD_WHITE, False):
            "0550X0850BWSTDPB060UW444MNG",
        (TrimSize.US_LETTER, BindingType.PERFECT_BOUND, PaperType.STANDARD_WHITE, False):
            "0850X1100BWSTDPB060UW444MNG",
        (TrimSize.A4, BindingType.PERFECT_BOUND, PaperType.STANDARD_WHITE, False):
            "0210X0297BWSTDPB060UW444MNG",
        # Color variants
        (TrimSize.A5, BindingType.PERFECT_BOUND, PaperType.PREMIUM_COLOR, True):
            "0148X0210FCSTDPB080CW444MNG",
        (TrimSize.US_TRADE, BindingType.PERFECT_BOUND, PaperType.PREMIUM_COLOR, True):
            "0600X0900FCSTDPB080CW444MNG",
    }

    # Legacy per-attribute mappings kept for downstream consumers that need
    # symbolic names (logging, UI). NOT used to build POD SKUs.
    TRIM_SIZE_MAPPING = {
        TrimSize.US_LETTER: "USTRADE0850X1100",
        TrimSize.US_TRADE: "USTRADE0600X0900",
        TrimSize.DIGEST: "DIGEST0550X0850",
        TrimSize.SQUARE_8: "SQUARE0800X0800",
        TrimSize.LANDSCAPE_9x7: "LANDSCAPE0900X0700",
        TrimSize.A4: "A4",
        TrimSize.A5: "A5",
    }
    BINDING_TYPE_MAPPING = {
        BindingType.PERFECT_BOUND: "PERFECT",
        BindingType.COIL_BOUND: "COIL",
        BindingType.SADDLE_STITCH: "SADDLE",
        BindingType.CASE_WRAP: "CASE_WRAP",
        BindingType.DUST_JACKET: "DUST_JACKET",
    }
    PAPER_TYPE_MAPPING = {
        PaperType.STANDARD_WHITE: "STANDARD_WHITE",
        PaperType.STANDARD_CREAM: "STANDARD_CREAM",
        PaperType.PREMIUM_WHITE: "PREMIUM_WHITE",
        PaperType.PREMIUM_COLOR: "PREMIUM_COLOR",
    }

    def __init__(self):
        """Initialize Lulu service with configuration."""
        self.client_key = current_app.config.get("LULU_CLIENT_KEY")
        self.client_secret = current_app.config.get("LULU_CLIENT_SECRET")
        self.api_url = current_app.config.get("LULU_API_URL", "https://api.lulu.com")
        self.sandbox_mode = current_app.config.get("LULU_SANDBOX_MODE", True)
        self.webhook_secret = current_app.config.get("LULU_WEBHOOK_SECRET")
        self.dev_mode = current_app.config.get("LULU_DEV_MODE", False)

        # OAuth token management
        self._access_token = None
        self._refresh_token = None
        self._token_expires_at = None

        # Request timeout
        self.timeout = 30  # seconds

        if not self.client_key or not self.client_secret:
            logger.warning("Lulu API credentials not configured")

    def _get_auth_token(self, force_refresh: bool = False) -> str:
        """
        Get or refresh OAuth2 access token with enhanced error handling and retry logic.

        Args:
            force_refresh: Force token refresh even if current token is valid

        Returns:
            str: Valid access token

        Raises:
            LuluAPIError: If authentication fails after retries
        """
        # Check if we have a valid token (unless forcing refresh)
        if not force_refresh and self._access_token and self._token_expires_at:
            # Add extra buffer for safety (10 minutes before expiration)
            safety_buffer = timedelta(minutes=10)
            if datetime.utcnow() < (self._token_expires_at - safety_buffer):
                logger.debug("Using existing valid access token")
                return self._access_token

        logger.info("Refreshing Lulu API access token")
        return self._refresh_access_token()

    def _refresh_access_token(self, max_retries: int = 3) -> str:
        """
        Refresh OAuth2 access token with retry logic.

        Args:
            max_retries: Maximum number of retry attempts

        Returns:
            str: New access token

        Raises:
            LuluAPIError: If authentication fails after all retries
        """
        auth_url = urljoin(
            self.api_url, "/auth/realms/glasstree/protocol/openid-connect/token"
        )

        # Create basic auth header
        credentials = f"{self.client_key}:{self.client_secret}"
        auth_header = base64.b64encode(credentials.encode()).decode()

        headers = {
            "Authorization": f"Basic {auth_header}",
            "Content-Type": "application/x-www-form-urlencoded",
            "User-Agent": "CookbookCreator/1.0",
        }

        data = {
            "grant_type": "client_credentials",
        }

        last_error = None

        for attempt in range(max_retries):
            try:
                logger.debug(f"Token refresh attempt {attempt + 1}/{max_retries}")

                response = requests.post(
                    auth_url, headers=headers, data=data, timeout=self.timeout
                )

                # Log response for debugging
                logger.debug(f"Auth response status: {response.status_code}")

                if response.status_code == 401:
                    raise LuluAPIError("Invalid client credentials", 401)
                elif response.status_code == 429:
                    # Rate limited - wait and retry
                    retry_after = int(response.headers.get("Retry-After", 60))
                    logger.warning(f"Rate limited, waiting {retry_after} seconds")
                    time.sleep(min(retry_after, 120))  # Cap at 2 minutes
                    continue

                response.raise_for_status()

                token_data = response.json()

                # Validate token response
                if not token_data.get("access_token"):
                    raise LuluAPIError("Invalid token response: missing access_token")

                self._access_token = token_data.get("access_token")
                self._refresh_token = token_data.get(
                    "refresh_token"
                )  # Store if available

                # Set expiration with safety buffer (5-minute buffer)
                expires_in = token_data.get("expires_in", 3600)
                self._token_expires_at = datetime.utcnow() + timedelta(
                    seconds=expires_in - 300
                )

                logger.info(
                    f"Successfully refreshed Lulu API access token (expires in {expires_in}s)"
                )
                return self._access_token

            except requests.exceptions.Timeout:
                last_error = LuluAPIError("Authentication request timed out")
                logger.warning(f"Token refresh timeout on attempt {attempt + 1}")
                if attempt < max_retries - 1:
                    time.sleep(2**attempt)  # Exponential backoff

            except requests.exceptions.ConnectionError as e:
                last_error = LuluAPIError(
                    f"Connection error during authentication: {str(e)}"
                )
                logger.warning(f"Connection error on attempt {attempt + 1}: {e}")
                if attempt < max_retries - 1:
                    time.sleep(2**attempt)  # Exponential backoff

            except requests.exceptions.RequestException as e:
                last_error = LuluAPIError(f"Authentication failed: {str(e)}")
                logger.error(f"Auth request failed on attempt {attempt + 1}: {e}")
                if attempt < max_retries - 1:
                    time.sleep(1)

        # All retries failed
        logger.error("Failed to refresh Lulu API token after all retries")
        raise last_error or LuluAPIError("Token refresh failed after all retries")

    def is_token_valid(self) -> bool:
        """
        Check if current access token is valid and not expired.

        Returns:
            bool: True if token is valid and not expired
        """
        if not self._access_token or not self._token_expires_at:
            return False

        # Consider token invalid if it expires within 5 minutes
        safety_buffer = timedelta(minutes=5)
        return datetime.utcnow() < (self._token_expires_at - safety_buffer)

    def force_token_refresh(self) -> str:
        """
        Force refresh of access token.

        Returns:
            str: New access token

        Raises:
            LuluAPIError: If refresh fails
        """
        return self._get_auth_token(force_refresh=True)

    def _make_request(
        self,
        method: str,
        endpoint: str,
        data: Optional[Dict] = None,
        params: Optional[Dict] = None,
        max_retries: int = 2,
    ) -> Dict[str, Any]:
        """
        Make authenticated request to Lulu API with automatic token refresh.

        Args:
            method: HTTP method (GET, POST, etc.)
            endpoint: API endpoint path
            data: Request body data
            params: Query parameters
            max_retries: Maximum number of retries for 401/403 errors

        Returns:
            Dict: API response data

        Raises:
            LuluAPIError: If request fails after retries
        """
        url = urljoin(self.api_url, endpoint)
        last_error = None

        for attempt in range(max_retries + 1):
            try:
                # Get fresh token for each attempt
                token = self._get_auth_token(force_refresh=(attempt > 0))

                headers = {
                    "Authorization": f"Bearer {token}",
                    "Content-Type": "application/json",
                    "Accept": "application/json",
                    "User-Agent": "CookbookCreator/1.0",
                }

                # Log request details for debugging
                if attempt == 0:
                    logger.debug(f"Lulu API request: {method} {url}")
                else:
                    logger.debug(f"Lulu API retry {attempt}: {method} {url}")

                response = requests.request(
                    method,
                    url,
                    headers=headers,
                    json=data,
                    params=params,
                    timeout=self.timeout,
                )

                logger.debug(f"Response status: {response.status_code}")

                # Handle specific status codes
                if response.status_code == 401:
                    logger.warning(f"Unauthorized response on attempt {attempt + 1}")
                    if attempt < max_retries:
                        # Force token refresh and retry
                        logger.info("Forcing token refresh due to 401 error")
                        continue
                    error_data = response.json() if response.content else {}
                    raise LuluAPIError("Authentication failed", 401, error_data)

                elif response.status_code == 403:
                    error_data = response.json() if response.content else {}
                    raise LuluAPIError("Access forbidden", 403, error_data)

                elif response.status_code == 429:
                    # Rate limited
                    retry_after = int(response.headers.get("Retry-After", 60))
                    logger.warning(f"Rate limited, waiting {retry_after} seconds")
                    time.sleep(min(retry_after, 120))  # Cap at 2 minutes
                    continue

                elif response.status_code >= 500:
                    # Server error - retry with exponential backoff
                    if attempt < max_retries:
                        wait_time = 2**attempt
                        logger.warning(
                            f"Server error {response.status_code}, retrying in {wait_time}s"
                        )
                        time.sleep(wait_time)
                        continue

                elif response.status_code >= 400:
                    # Client error - don't retry. Lulu's error body is
                    # sometimes a dict ({"detail": "..."} / {"message": "..."}
                    # / per-field errors) and sometimes a list of field
                    # validation errors. Handle both shapes so we surface the
                    # actual message instead of crashing during error logging.
                    error_data = response.json() if response.content else {}
                    if isinstance(error_data, dict):
                        error_message = error_data.get(
                            "message",
                            error_data.get("detail", f"API error: {response.status_code}"),
                        )
                    elif isinstance(error_data, list) and error_data:
                        # List of field errors — stringify for visibility.
                        error_message = f"API error: {response.status_code}: {error_data}"
                    else:
                        error_message = f"API error: {response.status_code}"
                    raise LuluAPIError(error_message, response.status_code, error_data)

                # Success - return response
                return response.json() if response.content else {}

            except Timeout:
                last_error = LuluAPIError("Request timed out")
                logger.error(
                    f"Lulu API request timed out: {method} {endpoint} (attempt {attempt + 1})"
                )
                if attempt < max_retries:
                    time.sleep(1)
                    continue

            except requests.exceptions.ConnectionError as e:
                last_error = LuluAPIError(f"Connection error: {str(e)}")
                logger.error(f"Connection error: {e} (attempt {attempt + 1})")
                if attempt < max_retries:
                    time.sleep(2**attempt)
                    continue

            except RequestException as e:
                last_error = LuluAPIError(f"Request failed: {str(e)}")
                logger.error(f"Lulu API request failed: {e}")
                break  # Don't retry for other request exceptions

            except LuluAPIError:
                # Re-raise LuluAPIError as-is
                raise

        # All attempts failed
        raise last_error or LuluAPIError("Request failed after all retries")

    def upload_pdf_file(
        self, pdf_bytes: bytes, file_type: str, filename: Optional[str] = None
    ) -> Optional[str]:
        """
        Upload PDF file to Lulu's file storage and return the file URL.

        Args:
            pdf_bytes: PDF file content as bytes
            file_type: Type of file ('interior' or 'cover')
            filename: Optional custom filename

        Returns:
            str: File URL from Lulu, or None if upload failed

        Raises:
            LuluAPIError: If upload fails
        """
        if not pdf_bytes:
            raise ValueError("PDF bytes cannot be empty")

        if file_type not in ["interior", "cover"]:
            raise ValueError("file_type must be 'interior' or 'cover'")

        # Generate filename if not provided
        if not filename:
            timestamp = int(time.time())
            filename = f"cookbook_{file_type}_{timestamp}.pdf"
        elif not filename.endswith(".pdf"):
            filename += ".pdf"

        logger.info(
            f"Uploading {file_type} PDF file: {filename} ({len(pdf_bytes)} bytes)"
        )

        # Lulu's Print API doesn't expose a file-hosting endpoint anymore —
        # the model is "you provide PDFs at public HTTPS URLs, we fetch them
        # when creating the print job and again when validating." We host
        # PDFs on Cloudinary (already used for digital BookProject exports)
        # and pass those URLs straight through to Lulu downstream.
        from app.services.cloudinary_service import cloudinary_service

        if not cloudinary_service.is_enabled():
            raise LuluAPIError(
                "Cloudinary must be enabled to host print PDFs — set USE_CLOUDINARY=true"
                " and CLOUDINARY_* credentials"
            )

        try:
            upload = cloudinary_service.upload_pdf(
                pdf_bytes,
                filename=filename,
                folder=f"print_orders/{file_type}",
            )
        except Exception as e:
            logger.error(
                f"Cloudinary upload failed for {file_type} PDF: {e}", exc_info=True
            )
            raise LuluAPIError(f"File upload error: {str(e)}")

        file_url = upload["url"]
        logger.info(
            f"Hosted {file_type} PDF on Cloudinary for Lulu fetch: {file_url}"
        )
        return file_url

    def upload_interior_pdf(
        self, pdf_bytes: bytes, filename: Optional[str] = None
    ) -> Optional[str]:
        """
        Upload interior PDF file to Lulu.

        Args:
            pdf_bytes: PDF file content as bytes
            filename: Optional custom filename

        Returns:
            str: File URL from Lulu
        """
        return self.upload_pdf_file(pdf_bytes, "interior", filename)

    def upload_cover_pdf(
        self, pdf_bytes: bytes, filename: Optional[str] = None
    ) -> Optional[str]:
        """
        Upload cover PDF file to Lulu.

        Args:
            pdf_bytes: PDF file content as bytes
            filename: Optional custom filename

        Returns:
            str: File URL from Lulu
        """
        return self.upload_pdf_file(pdf_bytes, "cover", filename)

    def validate_uploaded_file(
        self,
        file_url: str,
        file_type: str,
        page_count: Optional[int] = None,
        trim_size: Optional[str] = None,
    ) -> Tuple[bool, Optional[str], Optional[Dict]]:
        """
        Validate uploaded PDF file with enhanced validation info.

        Args:
            file_url: URL of uploaded file
            file_type: Type of file ('interior' or 'cover')
            page_count: Expected page count for interior files
            trim_size: Expected trim size

        Returns:
            Tuple of (is_valid, error_message, validation_details)
        """
        if file_type not in ["interior", "cover"]:
            raise ValueError("file_type must be 'interior' or 'cover'")

        endpoint = (
            "/print-file-validations/"
            if file_type == "interior"
            else "/cover-validations/"
        )

        request_data = {"file_url": file_url, "file_type": file_type}

        if file_type == "interior" and page_count:
            request_data["page_count"] = page_count

        if trim_size:
            request_data["trim_size"] = trim_size

        try:
            response = self._make_request("POST", endpoint, data=request_data)

            is_valid = response.get("status") == "VALID"
            errors = response.get("errors", [])
            warnings = response.get("warnings", [])

            # Build error message
            error_message = None
            if errors:
                error_list = [error.get("message", str(error)) for error in errors]
                error_message = "; ".join(error_list)

            # Build validation details
            validation_details = {
                "status": response.get("status"),
                "errors": errors,
                "warnings": warnings,
                "file_info": response.get("file_info", {}),
                "validation_time": response.get("validation_time"),
            }

            if warnings:
                warning_list = [
                    warning.get("message", str(warning)) for warning in warnings
                ]
                logger.warning(f"File validation warnings: {'; '.join(warning_list)}")

            return is_valid, error_message, validation_details

        except LuluAPIError as e:
            logger.error(f"File validation failed: {e}")
            return False, str(e), None

    def calculate_print_cost(
        self,
        specification: PrintSpecification,
        quantity: int = 1,
        shipping_country: str = "US",
        shipping_state: Optional[str] = None,
    ) -> Dict[str, Decimal]:
        """
        Calculate printing and shipping costs for a book.

        Args:
            specification: Book specifications
            quantity: Number of copies
            shipping_country: Destination country code
            shipping_state: Destination state code (for US)

        Returns:
            Dict with cost breakdown:
                - printing_cost: Cost to print
                - shipping_cost: Shipping cost
                - tax_amount: Estimated tax
                - total_cost: Total including all fees
        """
        # Build cost calculation request
        pod_package_id = self._get_pod_package_id(specification)

        request_data = {
            "line_items": [
                {
                    "page_count": specification.page_count,
                    "pod_package_id": pod_package_id,
                    "quantity": quantity,
                }
            ],
            "shipping_address": {
                "country": shipping_country,
            },
        }

        if shipping_state and shipping_country == "US":
            request_data["shipping_address"]["state_code"] = shipping_state

        # Make API request
        response = self._make_request(
            "POST", "/print-job-cost-calculations/", data=request_data
        )

        # Extract costs
        total_cost = Decimal(str(response.get("total_cost_incl_tax", 0)))
        total_cost_excl_tax = Decimal(str(response.get("total_cost_excl_tax", 0)))
        shipping_cost = Decimal(
            str(response.get("shipping_cost", {}).get("total_cost_incl_tax", 0))
        )

        # Calculate breakdown
        tax_amount = total_cost - total_cost_excl_tax
        printing_cost = total_cost_excl_tax - shipping_cost

        # Add platform markup with quantity-based scaling
        markup_rate = self._get_dynamic_markup_rate(quantity)
        platform_fee = printing_cost * markup_rate

        return {
            "printing_cost": printing_cost,
            "shipping_cost": shipping_cost,
            "tax_amount": tax_amount,
            "platform_fee": platform_fee,
            "total_cost": total_cost + platform_fee,
        }

    def get_print_quote(
        self,
        specification: PrintSpecification,
        quantity: int = 1,
        shipping_country: str = "US",
        shipping_state: Optional[str] = None,
    ) -> Optional[Dict[str, Any]]:
        """
        Get a comprehensive print quote including costs, delivery estimates, and validity period.

        Args:
            specification: Book specifications
            quantity: Number of copies
            shipping_country: Destination country code
            shipping_state: Destination state code (for US)

        Returns:
            Dict with quote information including:
                - printing_cost: Cost to print
                - shipping_cost: Shipping cost
                - tax_amount: Estimated tax
                - platform_fee: Platform markup fee
                - total_cost: Total including all fees
                - estimated_delivery_days: Estimated delivery time
                - valid_until: Quote validity expiration
                - quote_id: Unique quote identifier
        """
        # Development mode - return mock data
        if self.dev_mode:
            logger.info("Lulu service in development mode - returning mock print quote")
            from datetime import datetime, timedelta
            from decimal import Decimal
            import uuid

            # Mock pricing based on specification and quantity (using Decimal for consistency)
            base_cost = Decimal("8.50")  # Base printing cost
            page_cost = specification.page_count * Decimal("0.02")  # 2 cents per page
            binding_cost = (
                Decimal("2.00")
                if specification.binding_type != BindingType.SADDLE_STITCH
                else Decimal("0.50")
            )
            color_cost = (
                Decimal("3.00") if specification.color_pages else Decimal("0.00")
            )
            printing_cost = (
                base_cost + page_cost + binding_cost + color_cost
            ) * quantity

            # Mock shipping cost
            shipping_cost = Decimal("4.99") if quantity <= 5 else Decimal("7.99")

            # Mock tax (8.25% for US)
            tax_rate = Decimal("0.0825") if shipping_country == "US" else Decimal("0.0")

            # Calculate platform fee
            platform_fee = printing_cost * self._get_dynamic_markup_rate(quantity)
            subtotal = printing_cost + shipping_cost + platform_fee
            tax_amount = subtotal * tax_rate
            total_cost = subtotal + tax_amount

            return {
                "printing_cost": float(printing_cost.quantize(Decimal("0.01"))),
                "shipping_cost": float(shipping_cost.quantize(Decimal("0.01"))),
                "tax_amount": float(tax_amount.quantize(Decimal("0.01"))),
                "platform_fee": float(platform_fee.quantize(Decimal("0.01"))),
                "total_cost": float(total_cost.quantize(Decimal("0.01"))),
                "estimated_delivery_days": 5 + (2 if shipping_country != "US" else 0),
                "valid_until": (datetime.utcnow() + timedelta(hours=24)).isoformat()
                + "Z",
                "quote_id": f"dev-{uuid.uuid4().hex[:8]}",
                "shipping_destination": {
                    "country": shipping_country,
                    "state": shipping_state,
                },
            }

        try:
            # Get cost calculation from Lulu
            costs = self.calculate_print_cost(
                specification=specification,
                quantity=quantity,
                shipping_country=shipping_country,
                shipping_state=shipping_state,
            )

            # Calculate estimated delivery days based on shipping method and location
            estimated_delivery_days = self._estimate_delivery_days(
                shipping_country, shipping_state
            )

            # Quotes are typically valid for 30 days
            valid_until = (datetime.utcnow() + timedelta(days=30)).isoformat()

            # Generate a quote ID for tracking
            quote_id = f"quote_{int(time.time())}_{specification.id}_{quantity}"

            quote = {
                **costs,  # Include all cost fields
                "estimated_delivery_days": estimated_delivery_days,
                "valid_until": valid_until,
                "quote_id": quote_id,
                "quantity": quantity,
                "specification_id": specification.id,
                "created_at": datetime.utcnow().isoformat(),
            }

            logger.info(
                f"Generated print quote {quote_id}: ${costs['total_cost']:.2f} for {quantity} copies"
            )
            return quote

        except Exception as e:
            logger.error(f"Failed to get print quote: {str(e)}")
            self.handle_api_error(e, "print quote generation")
            return None

    def _estimate_delivery_days(
        self, shipping_country: str, shipping_state: Optional[str] = None
    ) -> int:
        """
        Estimate delivery days based on shipping destination.

        Args:
            shipping_country: Destination country code
            shipping_state: Destination state code (for US)

        Returns:
            Estimated delivery days
        """
        # Base production time (typical for Lulu)
        production_days = 3

        # Shipping time based on location
        if shipping_country == "US":
            if shipping_state in ["CA", "NV", "OR", "WA"]:  # West Coast
                shipping_days = 3
            elif shipping_state in ["TX", "CO", "AZ", "NM"]:  # Southwest/Central
                shipping_days = 4
            else:  # East Coast and other US states
                shipping_days = 5
        elif shipping_country == "CA":  # Canada
            shipping_days = 7
        elif shipping_country in ["GB", "DE", "FR", "ES", "IT", "NL", "BE"]:  # Europe
            shipping_days = 10
        elif shipping_country in ["AU", "NZ"]:  # Oceania
            shipping_days = 12
        else:  # Other international
            shipping_days = 14

        return production_days + shipping_days

    def _get_dynamic_markup_rate(self, quantity: int) -> Decimal:
        """
        Get dynamic platform markup rate based on quantity.
        Higher quantities get lower markup rates to encourage bulk orders.

        Args:
            quantity: Number of copies

        Returns:
            Markup rate as decimal (e.g., 0.25 for 25%)
        """
        base_markup = Decimal(
            str(current_app.config.get("PRINT_PLATFORM_MARKUP", 0.25))
        )

        # Quantity-based markup scaling
        if quantity >= 100:  # Large bulk orders
            markup_rate = base_markup * Decimal("0.6")  # 40% discount on platform fee
        elif quantity >= 50:  # Medium bulk orders
            markup_rate = base_markup * Decimal("0.7")  # 30% discount on platform fee
        elif quantity >= 25:  # Small bulk orders
            markup_rate = base_markup * Decimal("0.8")  # 20% discount on platform fee
        elif quantity >= 10:  # Multi-copy orders
            markup_rate = base_markup * Decimal("0.9")  # 10% discount on platform fee
        else:  # Single copy or small orders
            markup_rate = base_markup  # Full markup

        return markup_rate

    def get_bulk_pricing_tiers(self) -> List[Dict[str, Any]]:
        """
        Get bulk pricing tier information for frontend display.

        Returns:
            List of pricing tiers with quantity ranges and discount information
        """
        base_markup = float(current_app.config.get("PRINT_PLATFORM_MARKUP", 0.25))

        return [
            {
                "quantity_min": 1,
                "quantity_max": 9,
                "markup_rate": base_markup,
                "discount_percent": 0,
                "description": "Standard pricing",
            },
            {
                "quantity_min": 10,
                "quantity_max": 24,
                "markup_rate": base_markup * 0.9,
                "discount_percent": 10,
                "description": "10% platform fee discount",
            },
            {
                "quantity_min": 25,
                "quantity_max": 49,
                "markup_rate": base_markup * 0.8,
                "discount_percent": 20,
                "description": "20% platform fee discount",
            },
            {
                "quantity_min": 50,
                "quantity_max": 99,
                "markup_rate": base_markup * 0.7,
                "discount_percent": 30,
                "description": "30% platform fee discount",
            },
            {
                "quantity_min": 100,
                "quantity_max": None,
                "markup_rate": base_markup * 0.6,
                "discount_percent": 40,
                "description": "40% platform fee discount",
            },
        ]

    def validate_pdf_file(
        self, file_url: str, is_cover: bool = False, page_count: Optional[int] = None
    ) -> Tuple[bool, Optional[str]]:
        """
        Validate PDF file for printing.

        Args:
            file_url: Public URL to PDF file
            is_cover: Whether this is a cover file
            page_count: Expected page count (for interior files)

        Returns:
            Tuple of (is_valid, error_message)
        """
        endpoint = (
            "/printfile-validation/" if not is_cover else "/coverfile-validation/"
        )

        request_data = {
            "file_url": file_url,
        }

        if not is_cover and page_count:
            request_data["page_count"] = page_count

        try:
            response = self._make_request("POST", endpoint, data=request_data)

            # Check validation status
            status = response.get("status")
            if status == "VALID":
                return True, None
            else:
                errors = response.get("errors", [])
                error_message = "; ".join([e.get("message", "") for e in errors])
                return False, error_message

        except LuluAPIError as e:
            logger.error(f"PDF validation failed: {e}")
            return False, str(e)

    def create_print_job(self, order: PrintOrder) -> Dict[str, Any]:
        """
        Create a complete print job with Lulu including file upload and validation.

        Args:
            order: PrintOrder instance with complete details

        Returns:
            Dict with print job details including ID and status

        Raises:
            LuluAPIError: If job creation fails
        """
        logger.info(f"Creating Lulu print job for order {order.order_number}")

        try:
            # Get interior and cover file URLs (should already be uploaded)
            interior_file_url = order.interior_file_url
            cover_file_url = order.cover_file_url

            if not interior_file_url:
                raise LuluAPIError(
                    "Interior file URL not found - file must be uploaded first"
                )
            if not cover_file_url:
                raise LuluAPIError(
                    "Cover file URL not found - file must be uploaded first"
                )

            # Lulu's current API doesn't expose standalone pre-validation
            # endpoints — validation happens implicitly when /print-jobs/
            # fetches the URLs. Validation errors come back via the print-job
            # response and the async validation webhook.

            # Get POD package ID
            pod_package_id = self._get_pod_package_id(order.specification)

            # Build line item details. Title/author/isbn/description come
            # from whichever entity (Cookbook or BookProject) the order is
            # for — polymorphism lives on the PrintOrder model.
            meta = order.lulu_line_item_metadata()
            line_item = {
                "title": meta["title"],
                "cover": cover_file_url,
                "interior": interior_file_url,
                "pod_package_id": pod_package_id,
                "quantity": order.quantity,
                "author": meta["author"],
                "isbn": meta["isbn"],
                "description": meta["description"],
            }

            # Build shipping address
            shipping_address = {
                "name": order.shipping_name,
                "street1": order.shipping_address_line1,
                "city": order.shipping_city,
                "state_code": order.shipping_state_code,
                "postcode": order.shipping_postal_code,
                "country_code": order.shipping_country_code,
                "email": order.shipping_email,
            }

            if order.shipping_address_line2:
                shipping_address["street2"] = order.shipping_address_line2

            if order.shipping_phone:
                shipping_address["phone_number"] = order.shipping_phone

            # Build complete print job request
            request_data = {
                "line_items": [line_item],
                "shipping_address": shipping_address,
                "contact_email": order.shipping_email,
                "production_delay": 120,  # Standard production time (2 days)
                # Lulu's valid shipping levels: MAIL, PRIORITY_MAIL, GROUND_HD,
                # GROUND, GROUND_BUS, EXPEDITED, EXPRESS. We default to MAIL
                # (cheapest); the spec/order could expose this as a user-
                # selectable field later.
                "shipping_level": "MAIL",
                "external_id": order.order_number,  # Our order reference
            }

            # Add sandbox flag if in sandbox mode
            if self.sandbox_mode:
                request_data["sandbox"] = True

            logger.info(
                f"Submitting print job to Lulu API with {order.quantity} copies"
            )

            # Create print job
            response = self._make_request("POST", "/print-jobs/", data=request_data)

            # Extract response data
            job_id = response.get("id")
            line_items = response.get("line_items", [])
            status_info = response.get("status", {})

            result = {
                "print_job_id": job_id,
                "line_item_id": line_items[0].get("id") if line_items else None,
                "status": status_info.get("name"),
                "status_message": status_info.get("message"),
                "created_date": response.get("created_date"),
                "total_cost": response.get("total_cost"),
                "tracking_url": response.get("tracking_url"),
                "estimated_production_time": response.get("production_time"),
            }

            logger.info(f"Lulu print job created successfully: {job_id}")
            return result

        except LuluAPIError:
            raise  # Re-raise Lulu API errors as-is
        except Exception as e:
            logger.error(
                f"Unexpected error creating print job: {str(e)}", exc_info=True
            )
            raise LuluAPIError(f"Print job creation failed: {str(e)}")

    def get_print_job_status(self, print_job_id: str) -> Dict[str, Any]:
        """
        Get current status of a print job with comprehensive details.

        Args:
            print_job_id: Lulu print job ID

        Returns:
            Dict with detailed status information

        Raises:
            LuluAPIError: If status check fails
        """
        try:
            response = self._make_request("GET", f"/print-jobs/{print_job_id}/")

            status_info = response.get("status", {})
            shipping_info = response.get("shipping_info", {})
            cost_info = response.get("costs", {})
            line_items = response.get("line_items", [])

            # Extract line item details
            line_item_info = {}
            if line_items:
                first_item = line_items[0]
                line_item_info = {
                    "line_item_id": first_item.get("id"),
                    "title": first_item.get("title"),
                    "quantity": first_item.get("quantity"),
                    "unit_cost": first_item.get("unit_cost"),
                    "total_cost": first_item.get("total_cost"),
                    "status": first_item.get("status", {}).get("name"),
                    "status_message": first_item.get("status", {}).get("message"),
                }

            return {
                # Job level status
                "job_id": print_job_id,
                "status": status_info.get("name"),
                "status_message": status_info.get("message"),
                "created_date": response.get("created_date"),
                "updated_date": response.get("updated_date"),
                # Shipping information
                "shipping": {
                    "tracking_number": shipping_info.get("tracking_number"),
                    "carrier": shipping_info.get("carrier"),
                    "service": shipping_info.get("service"),
                    "estimated_delivery": shipping_info.get("estimated_delivery_date"),
                    "actual_delivery": shipping_info.get("actual_delivery_date"),
                    "tracking_url": shipping_info.get("tracking_url"),
                },
                # Cost breakdown
                "costs": {
                    "production_cost": cost_info.get("production_cost"),
                    "shipping_cost": cost_info.get("shipping_cost"),
                    "tax_cost": cost_info.get("tax_cost"),
                    "total_cost": cost_info.get("total_cost"),
                },
                # Line item details
                "line_item": line_item_info,
                # Production timeline
                "timeline": {
                    "estimated_production_time": response.get("production_time"),
                    "estimated_ship_date": response.get("estimated_ship_date"),
                    "production_delay": response.get("production_delay"),
                },
                # Additional metadata
                "external_id": response.get("external_id"),
                "contact_email": response.get("contact_email"),
            }

        except LuluAPIError:
            raise
        except Exception as e:
            logger.error(f"Error getting print job status: {str(e)}", exc_info=True)
            raise LuluAPIError(f"Failed to get job status: {str(e)}")

    def get_multiple_job_statuses(
        self, print_job_ids: List[str]
    ) -> Dict[str, Dict[str, Any]]:
        """
        Get status for multiple print jobs efficiently.

        Args:
            print_job_ids: List of Lulu print job IDs

        Returns:
            Dict mapping job IDs to their status information
        """
        if not print_job_ids:
            return {}

        # For small numbers, make individual requests
        if len(print_job_ids) <= 5:
            results = {}
            for job_id in print_job_ids:
                try:
                    results[job_id] = self.get_print_job_status(job_id)
                except LuluAPIError as e:
                    logger.warning(f"Failed to get status for job {job_id}: {e}")
                    results[job_id] = {"error": str(e)}
            return results

        # For larger numbers, use batch endpoint if available
        try:
            response = self._make_request(
                "POST", "/print-jobs/batch-status/", data={"job_ids": print_job_ids}
            )

            results = {}
            for job_data in response.get("jobs", []):
                job_id = job_data.get("id")
                if job_id:
                    # Convert to same format as individual status
                    results[job_id] = self._parse_job_status_response(job_data)

            return results

        except LuluAPIError:
            # Fall back to individual requests
            return self.get_multiple_job_statuses(
                print_job_ids[:5]
            )  # Recursive with limit

    def cancel_print_job(self, print_job_id: str, reason: Optional[str] = None) -> bool:
        """
        Cancel a print job if possible.

        Args:
            print_job_id: Lulu print job ID
            reason: Optional cancellation reason

        Returns:
            bool: True if cancellation was successful

        Raises:
            LuluAPIError: If cancellation fails
        """
        try:
            request_data = {"action": "cancel"}
            if reason:
                request_data["reason"] = reason

            response = self._make_request(
                "POST", f"/print-jobs/{print_job_id}/actions/", data=request_data
            )

            success = response.get("success", False)
            if success:
                logger.info(f"Successfully cancelled print job {print_job_id}")
            else:
                error_msg = response.get("message", "Unknown error")
                logger.error(f"Failed to cancel print job {print_job_id}: {error_msg}")

            return success

        except LuluAPIError:
            raise
        except Exception as e:
            logger.error(f"Error cancelling print job: {str(e)}", exc_info=True)
            raise LuluAPIError(f"Failed to cancel job: {str(e)}")

    def get_job_events(self, print_job_id: str) -> List[Dict[str, Any]]:
        """
        Get event history for a print job.

        Args:
            print_job_id: Lulu print job ID

        Returns:
            List of event dictionaries with timestamps and descriptions
        """
        try:
            response = self._make_request("GET", f"/print-jobs/{print_job_id}/events/")

            events = []
            for event in response.get("events", []):
                events.append(
                    {
                        "event_type": event.get("type"),
                        "event_name": event.get("name"),
                        "message": event.get("message"),
                        "timestamp": event.get("timestamp"),
                        "status": event.get("status"),
                        "metadata": event.get("metadata", {}),
                    }
                )

            return sorted(events, key=lambda x: x.get("timestamp", ""), reverse=True)

        except LuluAPIError:
            raise
        except Exception as e:
            logger.error(f"Error getting job events: {str(e)}", exc_info=True)
            raise LuluAPIError(f"Failed to get job events: {str(e)}")

    def _parse_job_status_response(self, job_data: Dict) -> Dict[str, Any]:
        """Parse job status response into standard format."""
        # Helper method to ensure consistent format across different API responses
        status_info = job_data.get("status", {})
        shipping_info = job_data.get("shipping_info", {})

        return {
            "job_id": job_data.get("id"),
            "status": status_info.get("name"),
            "status_message": status_info.get("message"),
            "tracking_number": shipping_info.get("tracking_number"),
            "carrier": shipping_info.get("carrier"),
            "estimated_delivery": shipping_info.get("estimated_delivery_date"),
            "created_date": job_data.get("created_date"),
            "updated_date": job_data.get("updated_date"),
        }

    def verify_webhook_signature(self, payload: str, signature: str) -> bool:
        """
        Verify webhook signature from Lulu.

        Args:
            payload: Raw webhook payload
            signature: Signature from X-Lulu-Signature header

        Returns:
            bool: Whether signature is valid
        """
        if not self.webhook_secret:
            logger.warning("Webhook secret not configured")
            return False

        expected_signature = hmac.new(
            self.webhook_secret.encode(), payload.encode(), hashlib.sha256
        ).hexdigest()

        return hmac.compare_digest(signature, expected_signature)

    def get_service_status(self) -> Dict[str, Any]:
        """
        Check Lulu API service status and connectivity.

        Returns:
            Dict with service status information
        """
        try:
            # Try a simple API call to check service
            response = self._make_request("GET", "/health/")

            return {
                "status": "operational",
                "api_version": response.get("version"),
                "server_time": response.get("timestamp"),
                "token_valid": self.is_token_valid(),
                "sandbox_mode": self.sandbox_mode,
                "last_check": datetime.utcnow().isoformat(),
            }

        except LuluAuthenticationError:
            return {
                "status": "authentication_error",
                "token_valid": False,
                "sandbox_mode": self.sandbox_mode,
                "last_check": datetime.utcnow().isoformat(),
                "error": "Invalid credentials",
            }
        except LuluServiceUnavailableError:
            return {
                "status": "service_unavailable",
                "sandbox_mode": self.sandbox_mode,
                "last_check": datetime.utcnow().isoformat(),
                "error": "Lulu service temporarily unavailable",
            }
        except LuluAPIError as e:
            return {
                "status": "error",
                "sandbox_mode": self.sandbox_mode,
                "last_check": datetime.utcnow().isoformat(),
                "error": str(e),
                "error_code": e.status_code,
            }

    def handle_api_error(self, error: Exception, context: str = "") -> None:
        """
        Enhanced error logging with context and recommendations.

        Args:
            error: The exception that occurred
            context: Context information about when the error occurred
        """
        error_context = f" during {context}" if context else ""

        if isinstance(error, LuluAuthenticationError):
            logger.error(
                f"Lulu authentication failed{error_context}. Check API credentials."
            )
        elif isinstance(error, LuluValidationError):
            logger.error(
                f"Lulu file validation failed{error_context}. PDF may not meet requirements."
            )
            if hasattr(error, "validation_errors") and error.validation_errors:
                for validation_error in error.validation_errors:
                    logger.error(f"  Validation error: {validation_error}")
        elif isinstance(error, LuluQuotaExceededError):
            logger.error(
                f"Lulu API quota exceeded{error_context}. Consider upgrading plan or reducing usage."
            )
        elif isinstance(error, LuluServiceUnavailableError):
            logger.error(f"Lulu service unavailable{error_context}. Retry later.")
        elif isinstance(error, LuluAPIError):
            if error.is_retryable:
                delay = error.get_retry_delay()
                logger.warning(
                    f"Retryable Lulu API error{error_context}. Retry in {delay}s. Error: {error}"
                )
            else:
                logger.error(f"Non-retryable Lulu API error{error_context}: {error}")
        else:
            logger.error(f"Unexpected error{error_context}: {error}", exc_info=True)

    def get_quota_info(self) -> Dict[str, Any]:
        """
        Get API quota and usage information.

        Returns:
            Dict with quota information
        """
        try:
            response = self._make_request("GET", "/account/quotas/")

            return {
                "daily_limit": response.get("daily_limit"),
                "daily_used": response.get("daily_used"),
                "monthly_limit": response.get("monthly_limit"),
                "monthly_used": response.get("monthly_used"),
                "reset_time": response.get("reset_time"),
                "overage_allowed": response.get("overage_allowed", False),
            }

        except LuluAPIError as e:
            logger.warning(f"Could not get quota info: {e}")
            return {"error": str(e)}

    def _get_pod_package_id(self, specification: PrintSpecification) -> str:
        """Resolve a valid Lulu POD package SKU for the given spec.

        Lulu only accepts a small set of pre-validated 27-character SKUs;
        they can't be built from independent attribute pieces. We look up
        the (trim, binding, paper, color) tuple in POD_PACKAGE_IDS and raise
        a clear LuluAPIError if no SKU is registered for that combination —
        better to fail at job submission with an actionable message than
        send a synthesized fake SKU that Lulu would reject."""
        if specification.lulu_pod_package_id:
            return specification.lulu_pod_package_id

        key = (
            specification.trim_size,
            specification.binding_type,
            specification.paper_type,
            bool(specification.color_pages),  # default-False on read
        )
        sku = self.POD_PACKAGE_IDS.get(key)
        if not sku:
            raise LuluAPIError(
                f"No Lulu POD package SKU registered for trim={specification.trim_size.value} "
                f"binding={specification.binding_type.value} paper={specification.paper_type.value} "
                f"color={specification.color_pages}. Add it to LuluService.POD_PACKAGE_IDS."
            )

        specification.lulu_pod_package_id = sku
        return sku

    def handle_webhook_event(self, event_type: str, event_data: Dict) -> None:
        """
        Handle webhook event from Lulu.

        Args:
            event_type: Type of webhook event
            event_data: Event payload data
        """
        logger.info(f"Processing Lulu webhook event: {event_type}")

        # Map Lulu events to our status updates
        event_handlers = {
            "print_job.created": self._handle_job_created,
            "print_job.status_changed": self._handle_status_changed,
            "print_job.shipped": self._handle_job_shipped,
            "print_job.delivered": self._handle_job_delivered,
            "print_job.cancelled": self._handle_job_cancelled,
        }

        handler = event_handlers.get(event_type)
        if handler:
            handler(event_data)
        else:
            logger.warning(f"Unhandled webhook event type: {event_type}")

    def _handle_job_created(self, data: Dict) -> None:
        """Handle print job created event."""
        # Implementation would update order status
        pass

    def _handle_status_changed(self, data: Dict) -> None:
        """Handle print job status change event."""
        # Implementation would update order status
        pass

    def _handle_job_shipped(self, data: Dict) -> None:
        """Handle print job shipped event."""
        # Implementation would update tracking info
        pass

    def _handle_job_delivered(self, data: Dict) -> None:
        """Handle print job delivered event."""
        # Implementation would mark order as delivered
        pass

    def _handle_job_cancelled(self, data: Dict) -> None:
        """Handle print job cancelled event."""
        # Implementation would handle cancellation
        pass
