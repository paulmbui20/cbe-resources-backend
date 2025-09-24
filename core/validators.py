from django.core.exceptions import ValidationError
import re


def validate_kenyan_phone(value):
    """Validate Kenyan phone number format"""
    pattern = r'^(\+254|254|0)(7|1)\d{8}$'
    if not re.match(pattern, value):
        raise ValidationError(
            'Enter a valid Kenyan phone number (e.g., +254712345678, 254712345678, or 0712345678)'
        )


def validate_mpesa_phone(value):
    """Validate M-Pesa compatible phone number"""
    # Remove any spaces or dashes
    clean_number = re.sub(r'[\s\-]', '', value)

    # Convert to 254 format
    if clean_number.startswith('0'):
        clean_number = '254' + clean_number[1:]
    elif clean_number.startswith('+254'):
        clean_number = clean_number[1:]

    # Validate format
    if not re.match(r'^254[17]\d{8}$', clean_number):
        raise ValidationError(
            'Enter a valid M-Pesa phone number (Safaricom or Airtel Kenya)'
        )

    return clean_number
