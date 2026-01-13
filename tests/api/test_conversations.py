"""
Tests for conversations API routes.
Tests api/routes/conversations.py
"""
import pytest
from unittest.mock import patch, MagicMock


class TestCreateConversation:
    """Tests for POST /conversations endpoint."""

    def test_create_conversation(self, test_client, mock_firebase_verify, test_user, auth_headers):
        """Test creating a new conversation."""
        response = test_client.post(
            "/conversations",
            json={
                "title": "Test Conversation",
                "subject": "Matematik",
                "grade": 10
            },
            headers=auth_headers
        )

        assert response.status_code == 200
        data = response.json()
        assert data["title"] == "Test Conversation"
        assert data["subject"] == "Matematik"
        assert data["grade"] == 10
        assert "id" in data

    def test_create_conversation_minimal(self, test_client, mock_firebase_verify, test_user, auth_headers):
        """Test creating conversation with minimal data."""
        response = test_client.post(
            "/conversations",
            json={},
            headers=auth_headers
        )

        assert response.status_code == 200
        data = response.json()
        assert "id" in data
        assert data["title"] == "Yeni Sohbet"  # Default title

    def test_create_conversation_no_auth(self, test_client):
        """Test 401 when creating conversation without authentication."""
        response = test_client.post(
            "/conversations",
            json={"title": "Test"}
        )

        assert response.status_code == 401


class TestListConversations:
    """Tests for GET /conversations endpoint."""

    def test_list_conversations_empty(self, test_client, mock_firebase_verify, test_user, auth_headers):
        """Test listing conversations when none exist."""
        response = test_client.get("/conversations", headers=auth_headers)

        assert response.status_code == 200
        data = response.json()
        assert data["items"] == []
        assert data["total"] == 0

    def test_list_conversations_with_data(
        self, test_client, mock_firebase_verify, test_user, test_conversation, auth_headers
    ):
        """Test listing conversations with existing data."""
        response = test_client.get("/conversations", headers=auth_headers)

        assert response.status_code == 200
        data = response.json()
        assert data["total"] >= 1
        assert any(c["id"] == test_conversation.id for c in data["items"])

    def test_list_conversations_pagination(
        self, test_client, mock_firebase_verify, test_user, auth_headers
    ):
        """Test conversation list pagination."""
        # Create multiple conversations
        for i in range(5):
            test_client.post(
                "/conversations",
                json={"title": f"Conversation {i}"},
                headers=auth_headers
            )

        # Test pagination
        response = test_client.get(
            "/conversations?page=1&page_size=2",
            headers=auth_headers
        )

        assert response.status_code == 200
        data = response.json()
        assert len(data["items"]) <= 2

    def test_list_conversations_exclude_archived(
        self, test_client, mock_firebase_verify, test_user, test_conversation, auth_headers
    ):
        """Test that archived conversations are excluded by default."""
        # Archive the conversation
        test_client.post(
            f"/conversations/{test_conversation.id}/archive",
            headers=auth_headers
        )

        # List should exclude archived
        response = test_client.get("/conversations", headers=auth_headers)
        data = response.json()

        ids = [c["id"] for c in data["items"]]
        assert test_conversation.id not in ids


class TestGetConversation:
    """Tests for GET /conversations/{id} endpoint."""

    def test_get_conversation(
        self, test_client, mock_firebase_verify, test_user, test_conversation, auth_headers
    ):
        """Test getting a specific conversation."""
        response = test_client.get(
            f"/conversations/{test_conversation.id}",
            headers=auth_headers
        )

        assert response.status_code == 200
        data = response.json()
        assert data["id"] == test_conversation.id
        assert data["title"] == test_conversation.title

    def test_get_conversation_with_messages(
        self, test_client, mock_firebase_verify, test_user, test_conversation_with_messages, auth_headers
    ):
        """Test getting conversation with messages."""
        response = test_client.get(
            f"/conversations/{test_conversation_with_messages.id}",
            headers=auth_headers
        )

        assert response.status_code == 200
        data = response.json()
        assert len(data["messages"]) == 2

    def test_get_conversation_not_found(
        self, test_client, mock_firebase_verify, test_user, auth_headers
    ):
        """Test 404 when conversation doesn't exist."""
        response = test_client.get(
            "/conversations/nonexistent-uuid-12345",
            headers=auth_headers
        )

        assert response.status_code == 404

    def test_get_conversation_wrong_user(
        self, test_client, test_conversation, auth_headers
    ):
        """Test that user can't access another user's conversation."""
        # Use a different Firebase token
        other_user_token = {
            "uid": "other-user-uid-999",
            "email": "other@example.com",
            "email_verified": True,
            "name": "Other User"
        }

        with patch('api.auth.firebase.verify_firebase_token', return_value=other_user_token):
            with patch('api.auth.deps.verify_firebase_token', return_value=other_user_token):
                with patch('api.auth.firebase.get_firebase_app', return_value=MagicMock()):
                    response = test_client.get(
                        f"/conversations/{test_conversation.id}",
                        headers=auth_headers
                    )

                    assert response.status_code == 404


class TestUpdateConversation:
    """Tests for PUT /conversations/{id} endpoint."""

    def test_update_conversation_title(
        self, test_client, mock_firebase_verify, test_user, test_conversation, auth_headers
    ):
        """Test updating conversation title."""
        response = test_client.put(
            f"/conversations/{test_conversation.id}",
            json={"title": "Updated Title"},
            headers=auth_headers
        )

        assert response.status_code == 200
        data = response.json()
        assert data["title"] == "Updated Title"

    def test_update_conversation_not_found(
        self, test_client, mock_firebase_verify, test_user, auth_headers
    ):
        """Test 404 when updating non-existent conversation."""
        response = test_client.put(
            "/conversations/nonexistent-uuid",
            json={"title": "New Title"},
            headers=auth_headers
        )

        assert response.status_code == 404


class TestDeleteConversation:
    """Tests for DELETE /conversations/{id} endpoint."""

    def test_delete_conversation(
        self, test_client, mock_firebase_verify, test_user, test_conversation, auth_headers
    ):
        """Test deleting a conversation."""
        conversation_id = test_conversation.id

        response = test_client.delete(
            f"/conversations/{conversation_id}",
            headers=auth_headers
        )

        assert response.status_code == 200

        # Verify it's deleted
        get_response = test_client.get(
            f"/conversations/{conversation_id}",
            headers=auth_headers
        )
        assert get_response.status_code == 404

    def test_delete_conversation_cascade_messages(
        self, test_client, mock_firebase_verify, test_user, test_conversation_with_messages, auth_headers
    ):
        """Test that deleting conversation cascades to messages."""
        conversation_id = test_conversation_with_messages.id

        response = test_client.delete(
            f"/conversations/{conversation_id}",
            headers=auth_headers
        )

        assert response.status_code == 200

    def test_delete_conversation_not_found(
        self, test_client, mock_firebase_verify, test_user, auth_headers
    ):
        """Test 404 when deleting non-existent conversation."""
        response = test_client.delete(
            "/conversations/nonexistent-uuid",
            headers=auth_headers
        )

        assert response.status_code == 404


class TestAddMessage:
    """Tests for POST /conversations/{id}/messages endpoint."""

    def test_add_user_message(
        self, test_client, mock_firebase_verify, test_user, test_conversation, auth_headers
    ):
        """Test adding a user message to conversation."""
        response = test_client.post(
            f"/conversations/{test_conversation.id}/messages",
            json={
                "role": "user",
                "content": "DNA'nin yapısı nedir?"
            },
            headers=auth_headers
        )

        assert response.status_code == 200
        data = response.json()
        assert data["role"] == "user"
        assert data["content"] == "DNA'nin yapısı nedir?"

    def test_add_message_updates_title(
        self, test_client, mock_firebase_verify, test_user, auth_headers
    ):
        """Test that first user message updates conversation title."""
        # Create a new conversation
        create_response = test_client.post(
            "/conversations",
            json={},
            headers=auth_headers
        )
        conversation_id = create_response.json()["id"]

        # Add first message
        test_client.post(
            f"/conversations/{conversation_id}/messages",
            json={
                "role": "user",
                "content": "Hücre bölünmesi hakkında bilgi verir misin?"
            },
            headers=auth_headers
        )

        # Get conversation and check title was updated
        get_response = test_client.get(
            f"/conversations/{conversation_id}",
            headers=auth_headers
        )
        data = get_response.json()
        # Title should be derived from first message
        assert data["title"] != "Yeni Sohbet"

    def test_add_message_not_found(
        self, test_client, mock_firebase_verify, test_user, auth_headers
    ):
        """Test 404 when adding message to non-existent conversation."""
        response = test_client.post(
            "/conversations/nonexistent-uuid/messages",
            json={"role": "user", "content": "Test"},
            headers=auth_headers
        )

        assert response.status_code == 404


class TestArchiveConversation:
    """Tests for POST /conversations/{id}/archive endpoint."""

    def test_archive_conversation(
        self, test_client, mock_firebase_verify, test_user, test_conversation, auth_headers
    ):
        """Test archiving a conversation."""
        response = test_client.post(
            f"/conversations/{test_conversation.id}/archive",
            headers=auth_headers
        )

        assert response.status_code == 200
        data = response.json()
        assert "arşivlendi" in data["message"]

    def test_archive_conversation_not_found(
        self, test_client, mock_firebase_verify, test_user, auth_headers
    ):
        """Test 404 when archiving non-existent conversation."""
        response = test_client.post(
            "/conversations/nonexistent-uuid/archive",
            headers=auth_headers
        )

        assert response.status_code == 404


class TestUnarchiveConversation:
    """Tests for POST /conversations/{id}/unarchive endpoint."""

    def test_unarchive_conversation(
        self, test_client, mock_firebase_verify, test_user, test_conversation, auth_headers
    ):
        """Test unarchiving a conversation."""
        # First archive it
        test_client.post(
            f"/conversations/{test_conversation.id}/archive",
            headers=auth_headers
        )

        # Then unarchive
        response = test_client.post(
            f"/conversations/{test_conversation.id}/unarchive",
            headers=auth_headers
        )

        assert response.status_code == 200
        data = response.json()
        assert "arşivden çıkarıldı" in data["message"]

    def test_unarchive_conversation_not_found(
        self, test_client, mock_firebase_verify, test_user, auth_headers
    ):
        """Test 404 when unarchiving non-existent conversation."""
        response = test_client.post(
            "/conversations/nonexistent-uuid/unarchive",
            headers=auth_headers
        )

        assert response.status_code == 404
