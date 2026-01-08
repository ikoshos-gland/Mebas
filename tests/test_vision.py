"""
Tests for Vision Module (Phase 5)
"""
import pytest
from io import BytesIO


class TestVisionAnalysisResult:
    """Tests for VisionAnalysisResult dataclass"""
    
    def test_result_dataclass(self):
        """Test VisionAnalysisResult structure"""
        from src.vision.azure_vision_client import VisionAnalysisResult
        
        result = VisionAnalysisResult(
            extracted_text="Test question",
            question_type="problem",
            topics=["matematik", "kesirler"],
            estimated_grade=5,
            confidence=0.9
        )
        
        assert result.extracted_text == "Test question"
        assert result.question_type == "problem"
        assert len(result.topics) == 2
        assert result.estimated_grade == 5
        print("✅ VisionAnalysisResult test passed!")
    
    def test_default_values(self):
        """Test default values are properly set"""
        from src.vision.azure_vision_client import VisionAnalysisResult
        
        result = VisionAnalysisResult(extracted_text="Test")
        
        assert result.topics == []
        assert result.math_expressions == []
        assert result.confidence == 0.0
        print("✅ Default values test passed!")


class TestAzureVisionClient:
    """Tests for AzureVisionClient class"""
    
    def test_client_exists(self):
        """Test client class exists"""
        from src.vision.azure_vision_client import AzureVisionClient
        assert AzureVisionClient is not None
        print("✅ AzureVisionClient class exists!")
    
    def test_clean_markdown_blocks(self):
        """Test markdown block cleaning"""
        from src.vision.azure_vision_client import AzureVisionClient
        
        client = AzureVisionClient.__new__(AzureVisionClient)
        
        # Test with markdown wrapper
        raw = '```json\n{"test": "value"}\n```'
        cleaned = client._clean_markdown_blocks(raw)
        
        assert cleaned == '{"test": "value"}'
        print("✅ Markdown cleaning test passed!")
    
    def test_fallback_parse(self):
        """Test fallback parsing for malformed JSON"""
        from src.vision.azure_vision_client import AzureVisionClient
        
        client = AzureVisionClient.__new__(AzureVisionClient)
        
        # Malformed but parseable content
        raw = '"extracted_text": "Bu bir soru", "estimated_grade": 5'
        result = client._fallback_parse(raw)
        
        assert "soru" in result.extracted_text
        assert result.estimated_grade == 5
        assert result.confidence == 0.3  # Low confidence for fallback
        print("✅ Fallback parse test passed!")


class TestImagePreprocessor:
    """Tests for ImagePreprocessor class"""
    
    def test_preprocessor_exists(self):
        """Test preprocessor class exists"""
        from src.vision.preprocessor import ImagePreprocessor
        assert ImagePreprocessor is not None
        print("✅ ImagePreprocessor class exists!")
    
    def test_get_image_info(self):
        """Test image info extraction"""
        from src.vision.preprocessor import ImagePreprocessor
        from PIL import Image
        from io import BytesIO
        
        preprocessor = ImagePreprocessor()
        
        # Create test image
        img = Image.new('RGB', (100, 100), color='white')
        buffer = BytesIO()
        img.save(buffer, format='PNG')
        image_bytes = buffer.getvalue()
        
        info = preprocessor.get_image_info(image_bytes)
        
        assert info["width"] == 100
        assert info["height"] == 100
        assert info["format"] == "PNG"
        print("✅ Image info test passed!")
    
    def test_enhance_from_bytes(self):
        """Test image enhancement from bytes"""
        from src.vision.preprocessor import ImagePreprocessor
        from PIL import Image
        from io import BytesIO
        
        preprocessor = ImagePreprocessor()
        
        # Create test image
        img = Image.new('RGB', (100, 100), color='red')
        buffer = BytesIO()
        img.save(buffer, format='PNG')
        image_bytes = buffer.getvalue()
        
        enhanced_bytes, base64_str = preprocessor.enhance_from_bytes(image_bytes)
        
        assert len(enhanced_bytes) > 0
        assert len(base64_str) > 0
        print("✅ Image enhancement test passed!")


class TestQuestionAnalysisPipeline:
    """Tests for QuestionAnalysisPipeline class"""
    
    def test_pipeline_exists(self):
        """Test pipeline class exists"""
        from src.vision.pipeline import QuestionAnalysisPipeline
        assert QuestionAnalysisPipeline is not None
        print("✅ QuestionAnalysisPipeline class exists!")
    
    def test_input_output_dataclasses(self):
        """Test input/output dataclasses"""
        from src.vision.pipeline import QuestionAnalysisInput, QuestionAnalysisOutput
        
        input_data = QuestionAnalysisInput(
            image_bytes=b"test",
            user_grade=5
        )
        
        output = QuestionAnalysisOutput(
            extracted_text="Test",
            grade=5,
            grade_source="user"
        )
        
        assert input_data.user_grade == 5
        assert output.grade_source == "user"
        print("✅ Input/Output dataclasses test passed!")
    
    def test_grade_priority(self):
        """Test that user_grade takes priority over AI estimate"""
        from src.vision.pipeline import QuestionAnalysisPipeline, QuestionAnalysisInput
        from src.vision.azure_vision_client import VisionAnalysisResult
        
        pipeline = QuestionAnalysisPipeline.__new__(QuestionAnalysisPipeline)
        
        input_data = QuestionAnalysisInput(user_grade=7)
        vision_result = VisionAnalysisResult(
            extracted_text="Test",
            estimated_grade=5  # AI says 5
        )
        
        grade, source = pipeline._determine_grade(input_data, vision_result)
        
        # User grade (7) should win over AI grade (5)
        assert grade == 7
        assert source == "user"
        print("✅ Grade priority test passed!")


if __name__ == "__main__":
    # Run tests
    test_result = TestVisionAnalysisResult()
    test_result.test_result_dataclass()
    test_result.test_default_values()
    
    test_client = TestAzureVisionClient()
    test_client.test_client_exists()
    test_client.test_clean_markdown_blocks()
    test_client.test_fallback_parse()
    
    test_preproc = TestImagePreprocessor()
    test_preproc.test_preprocessor_exists()
    test_preproc.test_get_image_info()
    test_preproc.test_enhance_from_bytes()
    
    test_pipeline = TestQuestionAnalysisPipeline()
    test_pipeline.test_pipeline_exists()
    test_pipeline.test_input_output_dataclasses()
    test_pipeline.test_grade_priority()
    
    print("\n✅ All Phase 5 tests passed!")
