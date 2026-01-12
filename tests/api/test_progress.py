"""
Tests for progress API routes.
Tests api/routes/progress.py
"""
import pytest
from unittest.mock import patch, MagicMock


class TestGetProgress:
    """Tests for GET /users/me/progress endpoint."""

    def test_get_progress_empty(self, authenticated_client):
        """Test getting progress when no kazanims are tracked."""
        client, user, db = authenticated_client
        response = client.get("/users/me/progress")

        assert response.status_code == 200
        data = response.json()
        assert data["items"] == []
        assert data["total"] == 0

    def test_get_progress_with_data(self, authenticated_client):
        """Test getting progress with tracked kazanims."""
        client, user, db = authenticated_client

        # Create progress entries directly in DB
        from src.database.models import UserKazanimProgress
        progress = UserKazanimProgress(
            user_id=user.id,
            kazanim_code="B.9.1.2.1",
            status="tracked",
            initial_confidence_score=0.85
        )
        db.add(progress)
        db.commit()

        response = client.get("/users/me/progress")

        assert response.status_code == 200
        data = response.json()
        assert data["total"] >= 1

    def test_get_progress_with_status_filter(self, authenticated_client):
        """Test filtering progress by status."""
        client, user, db = authenticated_client

        from src.database.models import UserKazanimProgress
        progress = UserKazanimProgress(
            user_id=user.id,
            kazanim_code="B.9.2.1.1",
            status="understood",
            initial_confidence_score=0.90
        )
        db.add(progress)
        db.commit()

        response = client.get("/users/me/progress?status=understood")

        assert response.status_code == 200
        data = response.json()
        assert all(item["status"] == "understood" for item in data["items"])

    def test_get_progress_no_auth(self, test_client):
        """Test 401 when getting progress without authentication."""
        response = test_client.get("/users/me/progress")
        assert response.status_code == 401


class TestTrackKazanim:
    """Tests for POST /users/me/progress/track endpoint."""

    def test_track_kazanim_new(self, authenticated_client):
        """Test tracking a new kazanim."""
        client, user, db = authenticated_client

        response = client.post(
            "/users/me/progress/track",
            json={
                "kazanim_code": "M.10.1.2.1",
                "confidence_score": 0.85
            }
        )

        assert response.status_code == 200
        data = response.json()
        assert data["kazanim_code"] == "M.10.1.2.1"
        assert data["status"] == "tracked"
        assert data["initial_confidence_score"] == 0.85

    def test_track_kazanim_idempotent(self, authenticated_client):
        """Test tracking same kazanim twice returns existing (idempotent)."""
        client, user, db = authenticated_client

        # First track
        response1 = client.post(
            "/users/me/progress/track",
            json={
                "kazanim_code": "B.9.3.1.1",
                "confidence_score": 0.85
            }
        )
        assert response1.status_code == 200

        # Track again - should return existing
        response2 = client.post(
            "/users/me/progress/track",
            json={
                "kazanim_code": "B.9.3.1.1",
                "confidence_score": 0.90
            }
        )

        assert response2.status_code == 200
        data = response2.json()
        # Should return existing, not update confidence
        assert data["initial_confidence_score"] == 0.85

    def test_track_kazanim_invalid_confidence(self, authenticated_client):
        """Test validation error for invalid confidence score."""
        client, user, db = authenticated_client

        response = client.post(
            "/users/me/progress/track",
            json={
                "kazanim_code": "M.10.1.2.1",
                "confidence_score": 1.5  # Invalid: > 1.0
            }
        )

        assert response.status_code == 422  # Validation error


class TestMarkUnderstood:
    """Tests for PUT /users/me/progress/{code}/understood endpoint."""

    def test_mark_understood(self, authenticated_client):
        """Test marking a tracked kazanim as understood."""
        client, user, db = authenticated_client

        # Create tracked entry
        from src.database.models import UserKazanimProgress
        progress = UserKazanimProgress(
            user_id=user.id,
            kazanim_code="B.9.4.1.1",
            status="tracked",
            initial_confidence_score=0.85
        )
        db.add(progress)
        db.commit()

        response = client.put(
            "/users/me/progress/B.9.4.1.1/understood",
            json={
                "understanding_confidence": 0.95,
                "understanding_signals": ["correct_explanation"]
            }
        )

        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "understood"
        assert data["understanding_confidence"] == 0.95

    def test_mark_understood_not_tracked(self, authenticated_client):
        """Test error when marking untracked kazanim as understood."""
        client, user, db = authenticated_client

        response = client.put(
            "/users/me/progress/X.99.99.99.99/understood",
            json={"understanding_confidence": 1.0}
        )

        assert response.status_code == 404
        assert "takipte değil" in response.json()["detail"]


class TestMarkInProgress:
    """Tests for PUT /users/me/progress/{code}/in-progress endpoint."""

    def test_mark_in_progress(self, authenticated_client):
        """Test marking a tracked kazanim as in-progress."""
        client, user, db = authenticated_client

        from src.database.models import UserKazanimProgress
        progress = UserKazanimProgress(
            user_id=user.id,
            kazanim_code="B.9.5.1.1",
            status="tracked",
            initial_confidence_score=0.75
        )
        db.add(progress)
        db.commit()

        response = client.put("/users/me/progress/B.9.5.1.1/in-progress")

        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "in_progress"

    def test_mark_in_progress_not_tracked(self, authenticated_client):
        """Test error when marking untracked kazanim as in-progress."""
        client, user, db = authenticated_client

        response = client.put("/users/me/progress/UNKNOWN.1.2.3/in-progress")
        assert response.status_code == 404


class TestGetProgressStats:
    """Tests for GET /users/me/progress/stats endpoint."""

    def test_get_stats_empty(self, authenticated_client):
        """Test getting stats when no kazanims tracked."""
        client, user, db = authenticated_client

        response = client.get("/users/me/progress/stats")

        assert response.status_code == 200
        data = response.json()
        assert data["total_tracked"] == 0
        assert data["total_understood"] == 0

    def test_get_stats_with_data(self, authenticated_client):
        """Test getting stats with tracked kazanims."""
        client, user, db = authenticated_client

        from src.database.models import UserKazanimProgress
        progress = UserKazanimProgress(
            user_id=user.id,
            kazanim_code="B.9.6.1.1",
            status="understood",
            initial_confidence_score=0.90
        )
        db.add(progress)
        db.commit()

        response = client.get("/users/me/progress/stats")

        assert response.status_code == 200
        data = response.json()
        assert data["total_tracked"] >= 1
        assert data["total_understood"] >= 1


class TestGetRecommendations:
    """Tests for GET /users/me/progress/recommendations endpoint."""

    def test_get_recommendations_empty(self, authenticated_client):
        """Test getting recommendations when no kazanims tracked."""
        client, user, db = authenticated_client

        response = client.get("/users/me/progress/recommendations")

        assert response.status_code == 200
        data = response.json()
        assert data == []


class TestRemoveProgress:
    """Tests for DELETE /users/me/progress/{code} endpoint."""

    def test_remove_progress(self, authenticated_client):
        """Test removing a tracked kazanim."""
        client, user, db = authenticated_client

        from src.database.models import UserKazanimProgress
        progress = UserKazanimProgress(
            user_id=user.id,
            kazanim_code="B.9.7.1.1",
            status="tracked",
            initial_confidence_score=0.80
        )
        db.add(progress)
        db.commit()

        response = client.delete("/users/me/progress/B.9.7.1.1")

        assert response.status_code == 200
        assert "kaldırıldı" in response.json()["message"]

    def test_remove_progress_not_found(self, authenticated_client):
        """Test error when removing untracked kazanim."""
        client, user, db = authenticated_client

        response = client.delete("/users/me/progress/NONEXISTENT.1.2.3")
        assert response.status_code == 404

    def test_remove_progress_no_auth(self, test_client):
        """Test 401 when removing progress without authentication."""
        response = test_client.delete("/users/me/progress/B.9.1.2.1")
        assert response.status_code == 401
