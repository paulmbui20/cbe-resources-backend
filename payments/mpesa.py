import base64
import logging
from datetime import datetime

import requests
from django.conf import settings

logger = logging.getLogger(__name__)


class MPesaAPI:
    """M-Pesa API integration class"""

    def __init__(self):
        self.consumer_key = settings.MPESA_CONSUMER_KEY
        self.consumer_secret = settings.MPESA_CONSUMER_SECRET
        self.base_url = settings.MPESA_BASE_URL
        self.shortcode = settings.MPESA_SHORTCODE
        self.passkey = settings.MPESA_PASSKEY
        self.callback_url = settings.MPESA_CALLBACK_URL

    def get_access_token(self):
        """Get OAuth access token"""
        try:
            url = f'{self.base_url}/oauth/v1/generate?grant_type=client_credentials'

            # Create basic auth header
            credentials = f'{self.consumer_key}:{self.consumer_secret}'
            encoded_credentials = base64.b64encode(credentials.encode()).decode()

            headers = {
                'Authorization': f'Basic {encoded_credentials}',
                'Content-Type': 'application/json'
            }

            response = requests.get(url, headers=headers, timeout=30)
            response.raise_for_status()

            data = response.json()
            return data['access_token']

        except requests.exceptions.RequestException as e:
            logger.error(f"Error getting M-Pesa access token: {e}")
            raise
        except Exception as e:
            logger.error(f"Unexpected error getting access token: {e}")
            raise

    def generate_password(self, timestamp=None):
        """Generate password for STK push"""
        if not timestamp:
            timestamp = datetime.now().strftime('%Y%m%d%H%M%S')

        password_string = f'{self.shortcode}{self.passkey}{timestamp}'
        password = base64.b64encode(password_string.encode()).decode()
        return password, timestamp

    def stk_push(self, phone_number, amount, account_reference, transaction_desc):
        """Initiate STK Push payment"""
        try:
            access_token = self.get_access_token()
            password, timestamp = self.generate_password()

            url = f'{self.base_url}/mpesa/stkpush/v1/processrequest'

            headers = {
                'Authorization': f'Bearer {access_token}',
                'Content-Type': 'application/json'
            }

            # Clean phone number (ensure it's in 254 format)
            if phone_number.startswith('+'):
                phone_number = phone_number[1:]
            if phone_number.startswith('0'):
                phone_number = '254' + phone_number[1:]
            elif not phone_number.startswith('254'):
                phone_number = '254' + phone_number

            payload = {
                'BusinessShortCode': self.shortcode,
                'Password': password,
                'Timestamp': timestamp,
                'TransactionType': 'CustomerPayBillOnline',
                'Amount': int(amount),
                'PartyA': phone_number,
                'PartyB': self.shortcode,
                'PhoneNumber': phone_number,
                'CallBackURL': self.callback_url,
                'AccountReference': account_reference,
                'TransactionDesc': transaction_desc
            }

            response = requests.post(url, json=payload, headers=headers, timeout=30)
            response.raise_for_status()

            return response.json()

        except requests.exceptions.RequestException as e:
            logger.error(f"Error initiating M-Pesa STK push: {e}")
            if hasattr(e, 'response') and e.response is not None:
                logger.error(f"Response content: {e.response.text}")
            raise
        except Exception as e:
            logger.error(f"Unexpected error in STK push: {e}")
            raise

    def query_payment_status(self, checkout_request_id):
        """Query payment status"""
        try:
            access_token = self.get_access_token()
            password, timestamp = self.generate_password()

            url = f'{self.base_url}/mpesa/stkpushquery/v1/query'

            headers = {
                'Authorization': f'Bearer {access_token}',
                'Content-Type': 'application/json'
            }

            payload = {
                'BusinessShortCode': self.shortcode,
                'Password': password,
                'Timestamp': timestamp,
                'CheckoutRequestID': checkout_request_id
            }

            response = requests.post(url, json=payload, headers=headers, timeout=30)
            response.raise_for_status()

            return response.json()

        except requests.exceptions.RequestException as e:
            logger.error(f"Error querying M-Pesa payment status: {e}")
            if hasattr(e, 'response') and e.response is not None:
                logger.error(f"Response content: {e.response.text}")
            raise
        except Exception as e:
            logger.error(f"Unexpected error querying payment status: {e}")
            raise

    def register_c2b_url(self, validation_url, confirmation_url, response_type="Completed"):
        """Register C2B URLs"""
        try:
            access_token = self.get_access_token()

            url = f'{self.base_url}/mpesa/c2b/v1/registerurl'

            headers = {
                'Authorization': f'Bearer {access_token}',
                'Content-Type': 'application/json'
            }

            payload = {
                'ShortCode': self.shortcode,
                'ResponseType': response_type,
                'ConfirmationURL': confirmation_url,
                'ValidationURL': validation_url
            }

            response = requests.post(url, json=payload, headers=headers, timeout=30)
            response.raise_for_status()

            return response.json()

        except requests.exceptions.RequestException as e:
            logger.error(f"Error registering C2B URLs: {e}")
            if hasattr(e, 'response') and e.response is not None:
                logger.error(f"Response content: {e.response.text}")
            raise
        except Exception as e:
            logger.error(f"Unexpected error registering URLs: {e}")
            raise

    def b2c_payment(self, phone_number, amount, command_id="BusinessPayment", remarks="Payment"):
        """Initiate B2C payment"""
        try:
            access_token = self.get_access_token()
            password, timestamp = self.generate_password()

            url = f'{self.base_url}/mpesa/b2c/v1/paymentrequest'

            headers = {
                'Authorization': f'Bearer {access_token}',
                'Content-Type': 'application/json'
            }

            # Clean phone number
            if phone_number.startswith('+'):
                phone_number = phone_number[1:]
            if phone_number.startswith('0'):
                phone_number = '254' + phone_number[1:]
            elif not phone_number.startswith('254'):
                phone_number = '254' + phone_number

            payload = {
                'InitiatorName': settings.MPESA_INITIATOR_NAME,
                'SecurityCredential': settings.MPESA_SECURITY_CREDENTIAL,
                'CommandID': command_id,
                'Amount': int(amount),
                'PartyA': self.shortcode,
                'PartyB': phone_number,
                'Remarks': remarks,
                'QueueTimeOutURL': settings.MPESA_QUEUE_TIMEOUT_URL,
                'ResultURL': settings.MPESA_RESULT_URL,
                'Occasion': 'Payment'
            }

            response = requests.post(url, json=payload, headers=headers, timeout=30)
            response.raise_for_status()

            return response.json()

        except requests.exceptions.RequestException as e:
            logger.error(f"Error initiating B2C payment: {e}")
            if hasattr(e, 'response') and e.response is not None:
                logger.error(f"Response content: {e.response.text}")
            raise
        except Exception as e:
            logger.error(f"Unexpected error in B2C payment: {e}")
            raise


# Utility functions for the billing system
def generate_mpesa_password(shortcode, passkey):
    """Generate M-Pesa password (for use in billing.py)"""
    timestamp = datetime.now().strftime("%Y%m%d%H%M%S")
    data_to_encode = shortcode + passkey + timestamp
    online_password = base64.b64encode(data_to_encode.encode()).decode()
    return online_password, timestamp


def get_mpesa_access_token():
    """Get M-Pesa access token (for use in billing.py)"""
    try:
        auth_url = f"{settings.MPESA_BASE_URL}/oauth/v1/generate?grant_type=client_credentials"
        response = requests.get(
            auth_url,
            auth=(settings.MPESA_CONSUMER_KEY, settings.MPESA_CONSUMER_SECRET),
            timeout=30
        )

        if response.status_code == 200:
            token = response.json().get("access_token")
            if token:
                return token
        else:
            logger.error(f"MPesa token request failed: {response.status_code} - {response.text}")
            return None

    except Exception as e:
        logger.error(f"Error getting MPesa access token: {str(e)}")
        return None