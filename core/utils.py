import hashlib
import uuid
import secrets
from typing import Dict, List, Tuple

from django.core.exceptions import ValidationError
from django.core.files.uploadedfile import UploadedFile


def generate_secure_filename(original_filename: str, user_id: int = None) -> str:
    """
    Generate a secure, unguessable filename for uploads
    Format: {timestamp}_{random_hex}_{user_hash}.{ext}
    """
    import time

    # Extract original extension (keep it for compatibility)
    ext = original_filename.split('.')[-1].lower() if '.' in original_filename else ''

    # Generate timestamp
    timestamp = str(int(time.time()))

    # Generate cryptographically secure random string
    random_hex = secrets.token_hex(16)  # 32 character hex string

    # Generate user hash if user_id provided
    user_hash = ''
    if user_id:
        user_data = f"{user_id}:{secrets.token_hex(8)}"
        user_hash = f"_{hashlib.sha256(user_data.encode()).hexdigest()[:12]}"

    # Combine all parts
    if ext:
        secure_name = f"{timestamp}_{random_hex}{user_hash}.{ext}"
    else:
        secure_name = f"{timestamp}_{random_hex}{user_hash}"

    return secure_name


def generate_download_token(user_id: int, product_id: int) -> str:
    """Generate secure download token"""
    import time
    timestamp = str(int(time.time()))
    nonce = secrets.token_hex(16)
    data = f"{user_id}:{product_id}:{timestamp}:{nonce}"
    return hashlib.sha256(data.encode()).hexdigest()


class MagicNumberValidator:
    """
    File content validation using magic numbers (file signatures)
    More secure than extension-based validation
    """

    # Magic number signatures for different file types
    FILE_SIGNATURES = {
        # PDF files
        'pdf': [b'\x25\x50\x44\x46'],  # %PDF

        # Microsoft Office (newer formats)
        'docx': [b'\x50\x4B\x03\x04', b'\x50\x4B\x05\x06', b'\x50\x4B\x07\x08'],  # ZIP-based
        'pptx': [b'\x50\x4B\x03\x04', b'\x50\x4B\x05\x06', b'\x50\x4B\x07\x08'],  # ZIP-based
        'xlsx': [b'\x50\x4B\x03\x04', b'\x50\x4B\x05\x06', b'\x50\x4B\x07\x08'],  # ZIP-based

        # Microsoft Office (older formats)
        'doc': [b'\xD0\xCF\x11\xE0\xA1\xB1\x1A\xE1'],  # OLE2 format
        'ppt': [b'\xD0\xCF\x11\xE0\xA1\xB1\x1A\xE1'],  # OLE2 format
        'xls': [b'\xD0\xCF\x11\xE0\xA1\xB1\x1A\xE1'],  # OLE2 format

        # Images
        'jpg': [b'\xFF\xD8\xFF'],  # JPEG
        'jpeg': [b'\xFF\xD8\xFF'],  # JPEG
        'png': [b'\x89\x50\x4E\x47\x0D\x0A\x1A\x0A'],  # PNG
        'gif': [b'\x47\x49\x46\x38\x37\x61', b'\x47\x49\x46\x38\x39\x61'],  # GIF87a, GIF89a
        'webp': [b'\x52\x49\x46\x46'],  # RIFF (need to check WEBP at offset 8)
        'bmp': [b'\x42\x4D'],  # BM
        'tiff': [b'\x49\x49\x2A\x00', b'\x4D\x4D\x00\x2A'],  # Little/Big endian TIFF

        # Text files
        'txt': [b'\xEF\xBB\xBF'],  # UTF-8 BOM (optional, text files might not have magic)

        # Archive formats
        'zip': [b'\x50\x4B\x03\x04', b'\x50\x4B\x05\x06', b'\x50\x4B\x07\x08'],
        'rar': [b'\x52\x61\x72\x21\x1A\x07\x00', b'\x52\x61\x72\x21\x1A\x07\x01\x00'],
        '7z': [b'\x37\x7A\xBC\xAF\x27\x1C'],
    }

    # Special handling for compound formats
    COMPOUND_FORMATS = {
        # Office formats that are ZIP-based need content inspection
        'docx': b'word/',
        'pptx': b'ppt/',
        'xlsx': b'xl/',
    }

    @classmethod
    def detect_file_type(cls, file: UploadedFile) -> str:
        """
        Detect file type based on content (magic numbers)
        Returns the detected file type or None if unknown
        """
        # Read first 512 bytes for magic number detection
        file.seek(0)
        header = file.read(512)
        file.seek(0)  # Reset file pointer

        if not header:
            return None

        # Check each file type
        for file_type, signatures in cls.FILE_SIGNATURES.items():
            for signature in signatures:
                if header.startswith(signature):
                    # Special handling for Office formats
                    if file_type in ['docx', 'pptx', 'xlsx']:
                        return cls._verify_office_format(file, file_type)
                    elif file_type == 'webp':
                        # WEBP has "WEBP" at offset 8 after RIFF
                        if len(header) >= 12 and header[8:12] == b'WEBP':
                            return 'webp'
                        continue
                    return file_type

        # Special case for text files (no reliable magic number)
        if cls._is_text_file(header):
            return 'txt'

        return None

    @classmethod
    def _verify_office_format(cls, file: UploadedFile, expected_type: str) -> str:
        """
        Verify Office format by checking internal structure
        Office 2007+ formats are ZIP files with specific internal structure
        """
        try:
            import zipfile
            import io

            # Read file content
            file.seek(0)
            content = file.read()
            file.seek(0)

            # Try to open as ZIP
            with zipfile.ZipFile(io.BytesIO(content)) as zf:
                file_list = zf.namelist()

                # Check for Office-specific files
                if expected_type == 'docx' and any('word/' in f for f in file_list):
                    return 'docx'
                elif expected_type == 'pptx' and any('ppt/' in f for f in file_list):
                    return 'pptx'
                elif expected_type == 'xlsx' and any('xl/' in f for f in file_list):
                    return 'xlsx'

                # If it's a ZIP but not the expected Office format
                return 'zip'

        except (zipfile.BadZipFile, Exception):
            # If ZIP parsing fails, it might be an older Office format
            return cls._check_ole_format(file)

    @classmethod
    def _check_ole_format(cls, file: UploadedFile) -> str:
        """Check if file is an OLE2 format (older Office files)"""
        file.seek(0)
        header = file.read(512)
        file.seek(0)

        if header.startswith(b'\xD0\xCF\x11\xE0\xA1\xB1\x1A\xE1'):
            # This is OLE2, but we can't easily distinguish between doc/ppt/xls
            # without more complex parsing, so we'll return generic 'doc'
            return 'doc'

        return None

    @classmethod
    def _is_text_file(cls, header: bytes) -> bool:
        """
        Check if file appears to be text based on content analysis
        """
        try:
            # Try to decode as UTF-8
            header.decode('utf-8')

            # Check if content is mostly printable ASCII/UTF-8
            printable_ratio = sum(1 for b in header if 32 <= b <= 126 or b in [9, 10, 13]) / len(header)
            return printable_ratio > 0.7  # 70% printable characters

        except UnicodeDecodeError:
            return False

    @classmethod
    def validate_file_content(cls, file: UploadedFile, allowed_types: List[str]) -> str:
        """
        Validate file content against allowed types
        Returns the detected file type if valid
        """
        detected_type = cls.detect_file_type(file)

        if not detected_type:
            raise ValidationError("Unable to determine file type from content")

        if detected_type not in allowed_types:
            raise ValidationError(
                f"File content indicates type '{detected_type}' which is not allowed. "
                f"Allowed types: {', '.join(allowed_types)}"
            )

        return detected_type


class FileValidator:
    """Enhanced file validator with content-based validation"""

    ALLOWED_DOCUMENT_TYPES = ['pdf', 'doc', 'docx', 'ppt', 'pptx', 'txt', 'xlsx', 'xls']
    ALLOWED_IMAGE_TYPES = ['jpg', 'jpeg', 'png', 'gif', 'webp', 'bmp']
    MAX_DOCUMENT_SIZE = 50 * 1024 * 1024  # 50MB
    MAX_IMAGE_SIZE = 10 * 1024 * 1024  # 10MB

    @classmethod
    def validate_document(cls, file: UploadedFile) -> Dict[str, any]:
        """
        Validate document files with content-based detection
        Returns validation results including detected type
        """
        result = {
            'is_valid': False,
            'detected_type': None,
            'original_name': file.name,
            'size': file.size,
            'errors': []
        }

        try:
            # Validate size first
            cls._validate_size(file, cls.MAX_DOCUMENT_SIZE)

            # Validate content
            detected_type = MagicNumberValidator.validate_file_content(
                file, cls.ALLOWED_DOCUMENT_TYPES
            )

            result['detected_type'] = detected_type
            result['is_valid'] = True

        except ValidationError as e:
            result['errors'].append(str(e))

        return result

    @classmethod
    def validate_image(cls, file: UploadedFile) -> Dict[str, any]:
        """
        Validate image files with content-based detection
        Returns validation results including detected type
        """
        result = {
            'is_valid': False,
            'detected_type': None,
            'original_name': file.name,
            'size': file.size,
            'errors': []
        }

        try:
            # Validate size first
            cls._validate_size(file, cls.MAX_IMAGE_SIZE)

            # Validate content
            detected_type = MagicNumberValidator.validate_file_content(
                file, cls.ALLOWED_IMAGE_TYPES
            )

            result['detected_type'] = detected_type
            result['is_valid'] = True

        except ValidationError as e:
            result['errors'].append(str(e))

        return result

    @classmethod
    def _validate_size(cls, file: UploadedFile, max_size: int) -> None:
        """Validate file size"""
        if file.size > max_size:
            max_mb = max_size // (1024 * 1024)
            current_mb = file.size / (1024 * 1024)
            raise ValidationError(
                f"File size ({current_mb:.1f}MB) exceeds maximum allowed size ({max_mb}MB)"
            )

    @classmethod
    def get_secure_upload_path(cls, instance, filename: str, folder: str = '') -> str:
        """
        Generate secure upload path with random filename
        """
        user_id = getattr(instance, 'user_id', None) or getattr(instance, 'vendor_id', None)
        secure_filename = generate_secure_filename(filename, user_id)

        if folder:
            return f"{folder}/{secure_filename}"
        return secure_filename


# Upload path functions for models
def secure_product_upload_path(instance, filename):
    """Secure upload path for product files"""
    return FileValidator.get_secure_upload_path(instance, filename, 'products')


def secure_preview_upload_path(instance, filename):
    """Secure upload path for preview files"""
    return FileValidator.get_secure_upload_path(instance, filename, 'previews')


def secure_thumbnail_upload_path(instance, filename):
    """Secure upload path for thumbnails"""
    return FileValidator.get_secure_upload_path(instance, filename, 'thumbnails')


def secure_category_image_upload_path(instance, filename):
    """Secure upload path for category images"""
    return FileValidator.get_secure_upload_path(instance, filename, 'categories')


def secure_product_image_upload_path(instance, filename):
    """Secure upload path for additional product images"""
    return FileValidator.get_secure_upload_path(instance, filename, 'product_images')