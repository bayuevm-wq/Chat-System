"""
Simplified end-to-end encryption service.

Provides RSA key pair generation, message encryption, and decryption
using the cryptography library. This is a simulation of E2E encryption
for educational purposes — production systems should use Signal Protocol.
"""

from __future__ import annotations

import base64

from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import padding, rsa

from src.config import get_settings


class EncryptionService:
    """Simplified RSA-based message encryption/decryption."""

    def __init__(self) -> None:
        settings = get_settings()
        self._key_size = settings.RSA_KEY_SIZE

    def generate_key_pair(self) -> tuple[str, str]:
        """Generate an RSA public/private key pair.

        Returns:
            Tuple of (public_key_pem, private_key_pem) as strings.
        """
        private_key = rsa.generate_private_key(
            public_exponent=65537,
            key_size=self._key_size,
        )

        private_pem = private_key.private_bytes(
            encoding=serialization.Encoding.PEM,
            format=serialization.PrivateFormat.PKCS8,
            encryption_algorithm=serialization.NoEncryption(),
        ).decode("utf-8")

        public_pem = private_key.public_key().public_bytes(
            encoding=serialization.Encoding.PEM,
            format=serialization.PublicFormat.SubjectPublicKeyInfo,
        ).decode("utf-8")

        return public_pem, private_pem

    def encrypt_message(self, content: str, public_key_pem: str) -> str:
        """Encrypt a message using the recipient's public key.

        Args:
            content: Plaintext message to encrypt.
            public_key_pem: Recipient's PEM-encoded public key.

        Returns:
            Base64-encoded ciphertext string.
        """
        public_key = serialization.load_pem_public_key(
            public_key_pem.encode("utf-8")
        )
        ciphertext = public_key.encrypt(  # type: ignore[union-attr]
            content.encode("utf-8"),
            padding.OAEP(
                mgf=padding.MGF1(algorithm=hashes.SHA256()),
                algorithm=hashes.SHA256(),
                label=None,
            ),
        )
        return base64.b64encode(ciphertext).decode("utf-8")

    def decrypt_message(self, encrypted: str, private_key_pem: str) -> str:
        """Decrypt a message using the recipient's private key.

        Args:
            encrypted: Base64-encoded ciphertext.
            private_key_pem: Recipient's PEM-encoded private key.

        Returns:
            Decrypted plaintext string.
        """
        private_key = serialization.load_pem_private_key(
            private_key_pem.encode("utf-8"),
            password=None,
        )
        ciphertext = base64.b64decode(encrypted)
        plaintext = private_key.decrypt(  # type: ignore[union-attr]
            ciphertext,
            padding.OAEP(
                mgf=padding.MGF1(algorithm=hashes.SHA256()),
                algorithm=hashes.SHA256(),
                label=None,
            ),
        )
        return plaintext.decode("utf-8")
