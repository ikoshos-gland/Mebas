"""
Tests for Firebase token verification.
Tests api/auth/firebase.py
"""
import pytest
from unittest.mock import patch, MagicMock


class TestVerifyFirebaseToken:
    """Tests for verify_firebase_token function."""

    def test_verify_valid_token(self):
        """Test verification of valid Firebase token."""
        mock_decoded = {
            "uid": "test-uid-123",
            "email": "test@example.com",
            "email_verified": True,
            "name": "Test User",
            "picture": "https://example.com/avatar.jpg"
        }

        with patch('api.auth.firebase.auth.verify_id_token', return_value=mock_decoded):
            with patch('api.auth.firebase.get_firebase_app', return_value=MagicMock()):
                from api.auth.firebase import verify_firebase_token

                result = verify_firebase_token("valid-token")

                assert result["uid"] == "test-uid-123"
                assert result["email"] == "test@example.com"
                assert result["email_verified"] is True

    def test_verify_expired_token(self):
        """Test handling of expired Firebase token."""
        from firebase_admin.auth import ExpiredIdTokenError

        with patch('api.auth.firebase.auth.verify_id_token') as mock_verify:
            mock_verify.side_effect = ExpiredIdTokenError("Token expired", None)
            with patch('api.auth.firebase.get_firebase_app', return_value=MagicMock()):
                from api.auth.firebase import verify_firebase_token

                with pytest.raises(ExpiredIdTokenError):
                    verify_firebase_token("expired-token")

    def test_verify_invalid_token(self):
        """Test handling of invalid Firebase token format."""
        from firebase_admin.auth import InvalidIdTokenError

        with patch('api.auth.firebase.auth.verify_id_token') as mock_verify:
            mock_verify.side_effect = InvalidIdTokenError("Invalid token", None)
            with patch('api.auth.firebase.get_firebase_app', return_value=MagicMock()):
                from api.auth.firebase import verify_firebase_token

                with pytest.raises(InvalidIdTokenError):
                    verify_firebase_token("invalid-token")

    def test_verify_revoked_token(self):
        """Test handling of revoked Firebase token."""
        from firebase_admin.auth import RevokedIdTokenError

        with patch('api.auth.firebase.auth.verify_id_token') as mock_verify:
            mock_verify.side_effect = RevokedIdTokenError("Token revoked")
            with patch('api.auth.firebase.get_firebase_app', return_value=MagicMock()):
                from api.auth.firebase import verify_firebase_token

                with pytest.raises(RevokedIdTokenError):
                    verify_firebase_token("revoked-token")


class TestGetFirebaseApp:
    """Tests for Firebase app initialization."""

    def test_singleton_pattern(self):
        """Test that Firebase app is initialized only once (singleton)."""
        import api.auth.firebase as firebase_module

        # Reset the global state
        firebase_module._firebase_app = None

        mock_app = MagicMock()

        with patch('api.auth.firebase.firebase_admin.initialize_app', return_value=mock_app):
            with patch('api.auth.firebase.credentials.Certificate', return_value=MagicMock()):
                with patch('api.auth.firebase.os.path.exists', return_value=True):
                    with patch('api.auth.firebase.get_settings') as mock_settings:
                        mock_settings.return_value.firebase_credentials_path = "/path/to/creds.json"

                        # First call should initialize
                        app1 = firebase_module.get_firebase_app()

                        # Second call should return same instance
                        app2 = firebase_module.get_firebase_app()

                        assert app1 is app2

        # Reset for other tests
        firebase_module._firebase_app = None

    def test_init_fails_without_credentials(self):
        """Test error when no Firebase credentials are available."""
        import api.auth.firebase as firebase_module

        # Reset the global state
        firebase_module._firebase_app = None

        with patch('api.auth.firebase.os.path.exists', return_value=False):
            with patch('api.auth.firebase.os.environ.get', return_value=None):
                with patch('api.auth.firebase.get_settings') as mock_settings:
                    mock_settings.return_value.firebase_credentials_path = None

                    with pytest.raises(RuntimeError) as exc_info:
                        firebase_module.get_firebase_app()

                    assert "Firebase credentials not found" in str(exc_info.value)

        # Reset for other tests
        firebase_module._firebase_app = None


class TestGetFirebaseUser:
    """Tests for get_firebase_user function."""

    def test_get_existing_user(self):
        """Test getting an existing Firebase user."""
        mock_user_record = MagicMock()
        mock_user_record.uid = "test-uid"
        mock_user_record.email = "test@example.com"

        with patch('api.auth.firebase.auth.get_user', return_value=mock_user_record):
            with patch('api.auth.firebase.get_firebase_app', return_value=MagicMock()):
                from api.auth.firebase import get_firebase_user

                result = get_firebase_user("test-uid")

                assert result.uid == "test-uid"
                assert result.email == "test@example.com"

    def test_get_nonexistent_user(self):
        """Test getting a non-existent Firebase user returns None."""
        from firebase_admin.auth import UserNotFoundError

        with patch('api.auth.firebase.auth.get_user') as mock_get:
            mock_get.side_effect = UserNotFoundError("User not found")
            with patch('api.auth.firebase.get_firebase_app', return_value=MagicMock()):
                from api.auth.firebase import get_firebase_user

                result = get_firebase_user("nonexistent-uid")

                assert result is None


class TestRevokeUserTokens:
    """Tests for revoke_user_tokens function."""

    def test_revoke_tokens(self):
        """Test revoking all tokens for a user."""
        with patch('api.auth.firebase.auth.revoke_refresh_tokens') as mock_revoke:
            with patch('api.auth.firebase.get_firebase_app', return_value=MagicMock()):
                from api.auth.firebase import revoke_user_tokens

                revoke_user_tokens("test-uid")

                mock_revoke.assert_called_once_with("test-uid")
