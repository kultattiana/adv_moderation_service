# tests/test_password.py
import pytest
import hashlib
import secrets
from unittest.mock import patch, Mock
import hmac

from utils.hash import hash_password, verify_password, generate_salt


class TestHashPassword:

    @pytest.mark.parametrize("password, salt, expected", [
    ("test", None, hashlib.md5(b"test").hexdigest()),
    ("hello", "world", hashlib.md5(b"helloworld").hexdigest()),
    ("", None, hashlib.md5(b"").hexdigest()),
    ("123", "", hashlib.md5(b"123").hexdigest()),
    ])
    def test_hash_password_parametrized(self, password, salt, expected):
        assert hash_password(password, salt) == expected
    
    
    def test_hash_password_consistency(self):
        password = "testpassword"
        salt = "testsalt"
        
        result1 = hash_password(password, salt)
        result2 = hash_password(password, salt)
        
        assert result1 == result2
    
    def test_hash_password_different_salts_different_hashes(self):
        password = "testpassword"
        
        hash1 = hash_password(password, "salt1")
        hash2 = hash_password(password, "salt2")
        
        assert hash1 != hash2


class TestVerifyPassword:
    
    @pytest.mark.parametrize("password, salt, wrong_salt, wrong_password, expected", [
    ("correct", "salt", "salt", "correct", True),
    ("correct", "salt", "salt", "wrong", False),
    ("correct", None, None, "correct", True),
    ("correct", None, None,  "wrong", False),
    ("mysecretpassword", "correctsalt", "wrongsalt",  "mysecretpassword", False),
    ])
    def test_verify_password_parametrized(self, password, salt, wrong_salt, wrong_password, expected):
        hashed = hash_password(password, salt)
        assert verify_password(wrong_password, hashed, wrong_salt) == expected
    

    def test_verify_password_empty_string(self):
        empty_password = ""
        hashed = hash_password(empty_password)
        assert verify_password("", hashed) is True
        assert verify_password("notempty", hashed) is False
    
    def test_verify_password_different_hash_lengths(self):
        password = "test"
        invalid_hash = "abc"
        result = verify_password(password, invalid_hash)
        assert result is False


class TestGenerateSalt:
    
    def test_generate_salt_length(self):
        salt = generate_salt()
        assert len(salt) == 32
        assert isinstance(salt, str)
    
    def test_generate_salt_uniqueness(self):
        salts = [generate_salt() for _ in range(100)]
        assert len(salts) == len(set(salts))
    
    def test_generate_salt_format(self):
        salt = generate_salt()
        assert all(c in '0123456789abcdef' for c in salt)
    
    def test_generate_salt_not_empty(self):
        salt = generate_salt()
        assert salt != ""
        assert salt is not None
    
    @patch('secrets.token_hex')
    def test_generate_salt_uses_secrets(self, mock_token_hex):
        
        mock_token_hex.return_value = "mocked_salt"
        salt = generate_salt()
        mock_token_hex.assert_called_once_with(16)
        assert salt == "mocked_salt"


