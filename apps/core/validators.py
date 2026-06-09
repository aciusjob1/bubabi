"""
File upload and input validators.
Prevents malicious file uploads and injection attacks.
"""
import os
import mimetypes
from django.core.exceptions import ValidationError


ALLOWED_UPLOAD_EXTENSIONS = {'.jpg', '.jpeg', '.png', '.gif', '.pdf', '.doc', '.docx'}
ALLOWED_MIME_TYPES = {
    'image/jpeg', 'image/png', 'image/gif', 
    'application/pdf',
    'application/msword',
    'application/vnd.openxmlformats-officedocument.wordprocessingml.document'
}
MAX_FILE_SIZE = 10 * 1024 * 1024  # 10MB


def validate_upload_file(file):
    """
    Validate uploaded file for security.
    Checks: size, extension, MIME type, file header (magic bytes)
    """
    if file.size > MAX_FILE_SIZE:
        raise ValidationError(f"File too large (max {MAX_FILE_SIZE/1024/1024}MB)")
    
    # Check extension
    ext = os.path.splitext(file.name)[1].lower()
    if ext not in ALLOWED_UPLOAD_EXTENSIONS:
        raise ValidationError(f"File type '{ext}' not allowed")
    
    # Check MIME type
    mime_type, _ = mimetypes.guess_type(file.name)
    if mime_type not in ALLOWED_MIME_TYPES:
        raise ValidationError(f"MIME type '{mime_type}' not allowed")
    
    # Check file header (magic bytes)
    file.seek(0)
    header = file.read(512)
    file.seek(0)
    
    if ext == '.pdf' and not header.startswith(b'%PDF'):
        raise ValidationError("Invalid PDF file (bad magic bytes)")
    
    if ext in {'.jpg', '.jpeg'} and not header.startswith(b'\xFF\xD8\xFF'):
        raise ValidationError("Invalid JPEG file (bad magic bytes)")
    
    if ext == '.png' and not header.startswith(b'\x89PNG'):
        raise ValidationError("Invalid PNG file (bad magic bytes)")


def validate_phone_number(phone):
    """Validate Tanzania phone number format."""
    import re
    # Tanzania: +255 or 0 prefix, then 7-9 digit, then 8 digits
    pattern = r'^\+?255[67]\d{8}$|^0[67]\d{8}$'
    if not re.match(pattern, phone):
        raise ValidationError("Must be valid Tanzania phone number (e.g., +255712345678)")
