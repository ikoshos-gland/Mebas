import pytest
from src.rag.output_models import AnalysisOutput, SolutionStep

class TestStructureUpdate:
    """Verifies the new structured output fields"""
    
    def test_solution_step_model(self):
        """Test SolutionStep instantiation"""
        step = SolutionStep(
            step_number=1,
            description="First step",
            result="x = 5"
        )
        assert step.step_number == 1
        assert step.description == "First step"
        assert step.result == "x = 5"
        print("✅ SolutionStep model test passed!")

    def test_analysis_output_structure(self):
        """Test AnalysisOutput with new fields"""
        output = AnalysisOutput(
            summary="Test summary",
            solution_steps=[
                SolutionStep(step_number=1, description="Step 1"),
                SolutionStep(step_number=2, description="Step 2", result="42")
            ],
            final_answer="42",
            confidence=0.9
        )
        
        assert len(output.solution_steps) == 2
        assert output.final_answer == "42"
        assert output.solution_steps[1].result == "42"
        print("✅ AnalysisOutput structure test passed!")

if __name__ == "__main__":
    test = TestStructureUpdate()
    test.test_solution_step_model()
    test.test_analysis_output_structure()
