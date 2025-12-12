"""Encryption utilities using Fernet symmetric encryption."""

import hmac
import hashlib
import base64
from cryptography.fernet import Fernet, InvalidToken


class EncryptionError(Exception):
    """Raised when encryption/decryption fails."""
    pass


def get_encryption_key(bot_token: str, user_id: int) -> bytes:
    """
    Derive an encryption key from bot token and user ID.

    Uses HMAC-SHA256 to derive a key, then formats it for Fernet.

    Args:
        bot_token: Telegram bot token (secret)
        user_id: Telegram user ID

    Returns:
        bytes: Fernet-compatible encryption key
    """
    # Create HMAC using bot token as key and user_id as message
    message = str(user_id).encode('utf-8')
    key_material = hmac.new(
        bot_token.encode('utf-8'),
        message,
        hashlib.sha256
    ).digest()

    # Fernet requires 32 bytes, URL-safe base64 encoded
    # We already have 32 bytes from SHA256, encode to base64
    return base64.urlsafe_b64encode(key_material)


def encrypt_value(value: str, key: bytes) -> str:
    """
    Encrypt a string value using Fernet.

    Args:
        value: String to encrypt
        key: Encryption key from get_encryption_key()

    Returns:
        str: Encrypted value (base64 encoded)

    Raises:
        EncryptionError: If encryption fails
    """
    try:
        fernet = Fernet(key)
        encrypted = fernet.encrypt(value.encode('utf-8'))
        return encrypted.decode('utf-8')
    except Exception as e:
        raise EncryptionError(f"Failed to encrypt value: {e}")


def decrypt_value(encrypted: str, key: bytes) -> str:
    """
    Decrypt a Fernet-encrypted value.

    Args:
        encrypted: Encrypted string (from encrypt_value)
        key: Encryption key from get_encryption_key()

    Returns:
        str: Decrypted value

    Raises:
        EncryptionError: If decryption fails or data is corrupted
    """
    try:
        fernet = Fernet(key)
        decrypted = fernet.decrypt(encrypted.encode('utf-8'))
        return decrypted.decode('utf-8')
    except InvalidToken:
        raise EncryptionError("Invalid encryption key or corrupted data")
    except Exception as e:
        raise EncryptionError(f"Failed to decrypt value: {e}")
