import pytest
from src.infrastructure.security.password import PasswordHasher

@pytest.fixture
def password_hasher():
    return PasswordHasher()

def test_hash_and_verify(password_hasher):
    password = "MySecurePassword123!"
    hashed = password_hasher.hash_password(password)
    assert hashed != password
    assert password_hasher.verify_password(password, hashed) is True

def test_wrong_password(password_hasher):
    password = "MySecurePassword123!"
    hashed = password_hasher.hash_password(password)
    assert password_hasher.verify_password("wrong_password", hashed) is False

def test_hash_uniqueness(password_hasher):
    password = "SamePassword"
    hash1 = password_hasher.hash_password(password)
    hash2 = password_hasher.hash_password(password)
    assert hash1 != hash2
    assert password_hasher.verify_password(password, hash1) is True
    assert password_hasher.verify_password(password, hash2) is True
