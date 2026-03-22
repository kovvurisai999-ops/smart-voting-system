import os
import hmac
import hashlib
import base64
from cryptography.fernet import Fernet
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.asymmetric import padding
from cryptography.hazmat.primitives import serialization

# ── Key Management ────────────────────────────────────────────────────────────
KEY_FILE = 'secret.key'

def get_encryption_key():
    """Load or generate a persistent encryption key."""
    if not os.path.exists(KEY_FILE):
        key = Fernet.generate_key()
        with open(KEY_FILE, 'wb') as f:
            f.write(key)
    else:
        with open(KEY_FILE, 'rb') as f:
            key = f.read()
    return key

# Initialize Cipher
_key = get_encryption_key()
_cipher = Fernet(_key)

def encrypt_data(data):
    """Encrypts string or bytes to base64 tokens."""
    if isinstance(data, str):
        data = data.encode()
    return _cipher.encrypt(data).decode()

def decrypt_data(token):
    """Decrypts base64 tokens back to string."""
    try:
        if isinstance(token, str):
            token = token.encode()
        return _cipher.decrypt(token).decode()
    except Exception:
        # Fallback for old unencrypted data
        if isinstance(token, bytes):
            return token.decode()
        return token

def encrypt_blob(blob_bytes):
    """Encrypts raw binary data."""
    return _cipher.encrypt(blob_bytes)

def decrypt_blob(encrypted_blob):
    """Decrypts binary data."""
    if not encrypted_blob:
        return None
    try:
        return _cipher.decrypt(encrypted_blob)
    except Exception:
        return encrypted_blob # Fallback

def hash_data(data):
    """Creates a salted SHA-256 hash for anonymized indexing."""
    if isinstance(data, str):
        data = data.encode()
    # We use the first 16 chars of the secret key as a salt
    salt = _key[:16]
    return hashlib.sha256(salt + data).hexdigest()

# ── Aadhaar v2.5 Cryptography ──────────────────────────────────────────────────
def compute_hmac(data_bytes, key_bytes):
    """Computes SHA-256 HMAC for Aadhaar v2.5 data integrity."""
    return hmac.new(key_bytes, data_bytes, hashlib.sha256).digest()

def sign_xml_data(xml_string, p12_path=None, password=None):
    """Placeholder for signing the Aadhaar XML request with a digital certificate."""
    # In production, use 'cryptography' or 'pyOpenSSL' to sign with your .p12 certificate
    if not p12_path:
        return "MOCK_SIGNATURE_BASE64"
    return "SIGNED_XML_PLACEHOLDER"

def encrypt_session_key(session_key, public_key_path):
    """Encrypts the UIDAI Session Key (Skey) using the UIDAI Public Key."""
    # In production, UIDAI provides a Public Key to encrypt your generated Skey
    return base64.b64encode(b"ENCRYPTED_SKEY").decode()
