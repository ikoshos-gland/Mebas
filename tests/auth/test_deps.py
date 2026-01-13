"""
Tests for authentication dependencies.
Tests api/auth/deps.py
"""
import pytest
from unittest.mock import MagicMock, patch, AsyncMock
from fastapi import HTTPException


class TestGetCurrentUser:
    """Tests for get_current_user dependency."""

    @pytest.mark.asyncio
    async def test_get_existing_user(self, test_db_session, test_user, mock_firebase_token):
        """Test getting an existing user from the database."""
        with patch('api.auth.deps.verify_firebase_token', return_value=mock_firebase_token):
            from api.auth.deps import get_current_user

            credentials = MagicMock()
            credentials.credentials = "valid-token"

            user = await get_current_user(credentials, test_db_session)

            assert user.email == test_user.email
            assert user.firebase_uid == mock_firebase_token["uid"]

    @pytest.mark.asyncio
    async def test_create_new_user_on_first_login(self, test_db_session):
        """Test automatic user creation on first Firebase login."""
        new_user_token = {
            "uid": "brand-new-uid-456",
            "email": "newuser@example.com",
            "email_verified": True,
            "name": "New User",
            "picture": "https://example.com/new-avatar.jpg"
        }

        with patch('api.auth.deps.verify_firebase_token', return_value=new_user_token):
            from api.auth.deps import get_current_user
            from src.database.models import User

            credentials = MagicMock()
            credentials.credentials = "new-user-token"

            user = await get_current_user(credentials, test_db_session)

            assert user is not None
            assert user.firebase_uid == new_user_token["uid"]
            assert user.email == new_user_token["email"]
            assert user.full_name == new_user_token["name"]
            assert user.profile_complete is False  # First login
            assert user.role == "student"  # Default role

            # Verify subscription was created
            assert user.subscription is not None
            assert user.subscription.plan == "free"
            assert user.subscription.questions_limit == 10

    @pytest.mark.asyncio
    async def test_syncs_email_verification(self, test_db_session, mock_firebase_token):
        """Test that email verification status syncs from Firebase."""
        from src.database.models import User, Subscription

        # Create user with unverified email
        user = User(
            firebase_uid=mock_firebase_token["uid"],
            email=mock_firebase_token["email"],
            full_name="Test User",
            is_verified=False,  # Not verified in DB
            role="student",
            profile_complete=True
        )
        test_db_session.add(user)
        test_db_session.flush()

        subscription = Subscription(
            user_id=user.id,
            plan="free",
            questions_limit=10,
            images_limit=0
        )
        test_db_session.add(subscription)
        test_db_session.commit()

        # Firebase says verified
        token_with_verified = {**mock_firebase_token, "email_verified": True}

        with patch('api.auth.deps.verify_firebase_token', return_value=token_with_verified):
            from api.auth.deps import get_current_user

            credentials = MagicMock()
            credentials.credentials = "token"

            updated_user = await get_current_user(credentials, test_db_session)

            assert updated_user.is_verified is True

    @pytest.mark.asyncio
    async def test_raises_401_without_credentials(self, test_db_session):
        """Test 401 error when no credentials provided."""
        from api.auth.deps import get_current_user

        with pytest.raises(HTTPException) as exc_info:
            await get_current_user(None, test_db_session)

        assert exc_info.value.status_code == 401
        assert "Oturum gecersiz" in exc_info.value.detail

    @pytest.mark.asyncio
    async def test_raises_401_on_invalid_token(self, test_db_session):
        """Test 401 error when token is invalid."""
        from firebase_admin.auth import InvalidIdTokenError

        with patch('api.auth.deps.verify_firebase_token') as mock_verify:
            mock_verify.side_effect = InvalidIdTokenError("Invalid", None)

            from api.auth.deps import get_current_user

            credentials = MagicMock()
            credentials.credentials = "invalid-token"

            with pytest.raises(HTTPException) as exc_info:
                await get_current_user(credentials, test_db_session)

            assert exc_info.value.status_code == 401

    @pytest.mark.asyncio
    async def test_raises_401_on_expired_token(self, test_db_session):
        """Test 401 error when token is expired."""
        from firebase_admin.auth import ExpiredIdTokenError

        with patch('api.auth.deps.verify_firebase_token') as mock_verify:
            mock_verify.side_effect = ExpiredIdTokenError("Expired", None)

            from api.auth.deps import get_current_user

            credentials = MagicMock()
            credentials.credentials = "expired-token"

            with pytest.raises(HTTPException) as exc_info:
                await get_current_user(credentials, test_db_session)

            assert exc_info.value.status_code == 401

    @pytest.mark.asyncio
    async def test_raises_401_missing_uid(self, test_db_session):
        """Test 401 error when decoded token has no UID."""
        token_without_uid = {"email": "test@example.com"}  # No uid

        with patch('api.auth.deps.verify_firebase_token', return_value=token_without_uid):
            from api.auth.deps import get_current_user

            credentials = MagicMock()
            credentials.credentials = "token"

            with pytest.raises(HTTPException) as exc_info:
                await get_current_user(credentials, test_db_session)

            assert exc_info.value.status_code == 401


class TestGetCurrentActiveUser:
    """Tests for get_current_active_user dependency."""

    @pytest.mark.asyncio
    async def test_returns_active_user(self, test_user):
        """Test returning active user."""
        from api.auth.deps import get_current_active_user

        user = await get_current_active_user(test_user)

        assert user == test_user
        assert user.is_active is True

    @pytest.mark.asyncio
    async def test_raises_403_for_inactive_user(self, test_user_inactive):
        """Test 403 error for inactive user."""
        from api.auth.deps import get_current_active_user

        with pytest.raises(HTTPException) as exc_info:
            await get_current_active_user(test_user_inactive)

        assert exc_info.value.status_code == 403
        assert "devre disi" in exc_info.value.detail


class TestGetOptionalUser:
    """Tests for get_optional_user dependency."""

    @pytest.mark.asyncio
    async def test_returns_user_when_authenticated(self, test_db_session, test_user, mock_firebase_token):
        """Test returning user when valid token provided."""
        with patch('api.auth.deps.verify_firebase_token', return_value=mock_firebase_token):
            from api.auth.deps import get_optional_user

            credentials = MagicMock()
            credentials.credentials = "valid-token"

            user = await get_optional_user(credentials, test_db_session)

            assert user is not None
            assert user.firebase_uid == mock_firebase_token["uid"]

    @pytest.mark.asyncio
    async def test_returns_none_without_token(self, test_db_session):
        """Test returning None when no token provided."""
        from api.auth.deps import get_optional_user

        user = await get_optional_user(None, test_db_session)

        assert user is None

    @pytest.mark.asyncio
    async def test_returns_none_on_invalid_token(self, test_db_session):
        """Test returning None on invalid token (no exception raised)."""
        from firebase_admin.auth import InvalidIdTokenError

        with patch('api.auth.deps.verify_firebase_token') as mock_verify:
            mock_verify.side_effect = InvalidIdTokenError("Invalid", None)

            from api.auth.deps import get_optional_user

            credentials = MagicMock()
            credentials.credentials = "invalid-token"

            # Should return None, NOT raise exception
            user = await get_optional_user(credentials, test_db_session)

            assert user is None

    @pytest.mark.asyncio
    async def test_does_not_create_user(self, test_db_session):
        """Test that get_optional_user does NOT create user on first login."""
        new_user_token = {
            "uid": "unknown-new-uid-789",
            "email": "unknown@example.com",
            "email_verified": True,
            "name": "Unknown User"
        }

        with patch('api.auth.deps.verify_firebase_token', return_value=new_user_token):
            from api.auth.deps import get_optional_user
            from src.database.models import User

            credentials = MagicMock()
            credentials.credentials = "token"

            # Unlike get_current_user, this should return None for unknown users
            user = await get_optional_user(credentials, test_db_session)

            assert user is None

            # Verify user was NOT created in DB
            db_user = test_db_session.query(User).filter(
                User.firebase_uid == new_user_token["uid"]
            ).first()
            assert db_user is None
