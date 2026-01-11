"""
Tests for RAG Module (Phase 7) and API Module (Phase 8)
"""
import pytest


class TestOutputModels:
    """Tests for Pydantic output models"""
    
    def test_matched_kazanim(self):
        """Test MatchedKazanim model"""
        from src.rag.output_models import MatchedKazanim
        
        kazanim = MatchedKazanim(
            kazanim_code="M.5.1.2.3",
            kazanim_description="Test kazanım",
            match_score=0.85,
            match_reason="Konu uyumu"
        )
        
        assert kazanim.kazanim_code == "M.5.1.2.3"
        assert kazanim.match_score == 0.85
        print("✅ MatchedKazanim test passed!")
    
    def test_analysis_output(self):
        """Test AnalysisOutput model"""
        from src.rag.output_models import AnalysisOutput
        
        output = AnalysisOutput(
            summary="Test özet",
            matched_kazanimlar=[],
            confidence=0.9
        )
        
        assert output.summary == "Test özet"
        assert output.confidence == 0.9
        print("✅ AnalysisOutput test passed!")
    
    def test_prerequisite_gap(self):
        """Test PrerequisiteGap model"""
        from src.rag.output_models import PrerequisiteGap
        
        gap = PrerequisiteGap(
            missing_kazanim_code="M.4.1.1.1",
            missing_kazanim_description="Temel konu",
            importance="Kritik",
            suggestion="Bu konuyu çalışın"
        )
        
        assert gap.missing_kazanim_code == "M.4.1.1.1"
        print("✅ PrerequisiteGap test passed!")


class TestResponseGenerator:
    """Tests for ResponseGenerator"""
    
    def test_generator_exists(self):
        """Test ResponseGenerator class exists"""
        from src.rag.response_generator import ResponseGenerator
        assert ResponseGenerator is not None
        print("✅ ResponseGenerator class exists!")
    
    def test_build_prompt(self):
        """Test prompt building"""
        from src.rag.response_generator import ResponseGenerator
        from unittest.mock import MagicMock

        # Create instance properly with mock LLM to avoid Azure connection
        mock_llm = MagicMock()
        mock_llm.with_structured_output = MagicMock(return_value=mock_llm)
        gen = ResponseGenerator(llm=mock_llm)

        prompt = gen._build_prompt(
            question_text="Test soru",
            kazanimlar=[{"kazanim_code": "M.5.1.1.1", "kazanim_description": "Test"}],
            textbook_sections=[],
            topics=["matematik"]
        )

        assert "Test soru" in prompt
        assert "M.5.1.1.1" in prompt
        print("✅ Build prompt test passed!")


class TestGapFinder:
    """Tests for GapFinder"""
    
    def test_simple_gap_finder(self):
        """Test SimpleGapFinder heuristics"""
        from src.rag.gap_finder import SimpleGapFinder
        
        finder = SimpleGapFinder()
        gaps = finder.find_gaps(["M.5.1.2.3"])
        
        assert len(gaps) > 0
        assert gaps[0]["missing_kazanim_code"] == "M.5.1.1.1"
        print("✅ SimpleGapFinder test passed!")


class TestAPIModels:
    """Tests for API models"""
    
    def test_analyze_image_request(self):
        """Test AnalyzeImageRequest model"""
        from api.models import AnalyzeImageRequest
        
        req = AnalyzeImageRequest(
            image_base64="test",
            grade=5,
            subject="M"
        )
        
        assert req.grade == 5
        print("✅ AnalyzeImageRequest test passed!")
    
    def test_analysis_response(self):
        """Test AnalysisResponse model"""
        from api.models import AnalysisResponse
        
        resp = AnalysisResponse(
            analysis_id="test-123",
            status="success",
            summary="Test"
        )
        
        assert resp.analysis_id == "test-123"
        assert resp.status == "success"
        print("✅ AnalysisResponse test passed!")
    
    def test_health_response(self):
        """Test HealthResponse model"""
        from api.models import HealthResponse
        
        health = HealthResponse()
        
        assert health.status == "healthy"
        print("✅ HealthResponse test passed!")


class TestFastAPIApp:
    """Tests for FastAPI app"""
    
    def test_app_exists(self):
        """Test app can be imported"""
        from api.main import app
        assert app is not None
        print("✅ FastAPI app exists!")
    
    def test_routes_registered(self):
        """Test routes are registered"""
        from api.main import app
        
        routes = [r.path for r in app.routes]
        
        assert "/" in routes
        assert "/health" in routes
        print("✅ Routes registered test passed!")


if __name__ == "__main__":
    # Phase 7 tests
    test_models = TestOutputModels()
    test_models.test_matched_kazanim()
    test_models.test_analysis_output()
    test_models.test_prerequisite_gap()
    
    test_gen = TestResponseGenerator()
    test_gen.test_generator_exists()
    test_gen.test_build_prompt()
    
    test_gap = TestGapFinder()
    test_gap.test_simple_gap_finder()
    
    # Phase 8 tests
    test_api = TestAPIModels()
    test_api.test_analyze_image_request()
    test_api.test_analysis_response()
    test_api.test_health_response()
    
    test_app = TestFastAPIApp()
    test_app.test_app_exists()
    test_app.test_routes_registered()
    
    print("\n✅ All Phase 7 & 8 tests passed!")
