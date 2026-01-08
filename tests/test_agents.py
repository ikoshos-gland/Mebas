"""
Tests for Agents Module (Phase 6)
"""
import pytest


class TestQuestionAnalysisState:
    """Tests for state definition"""
    
    def test_state_creation(self):
        """Test initial state creation"""
        from src.agents.state import create_initial_state
        
        state = create_initial_state(
            question_text="Test soru",
            user_grade=5,
            user_subject="M"
        )
        
        assert state["question_text"] == "Test soru"
        assert state["user_grade"] == 5
        assert state["user_subject"] == "M"
        assert state["status"] == "processing"
        print("✅ State creation test passed!")
    
    def test_effective_grade(self):
        """Test grade priority (user > AI)"""
        from src.agents.state import get_effective_grade
        
        # User grade takes priority
        state = {
            "user_grade": 5,
            "ai_estimated_grade": 7
        }
        assert get_effective_grade(state) == 5
        
        # Fall back to AI if no user grade
        state = {
            "user_grade": None,
            "ai_estimated_grade": 7
        }
        assert get_effective_grade(state) == 7
        
        print("✅ Effective grade test passed!")
    
    def test_effective_subject(self):
        """Test subject detection"""
        from src.agents.state import get_effective_subject
        
        # User subject takes priority
        state = {
            "user_subject": "F",
            "detected_topics": ["matematik", "kesir"]
        }
        assert get_effective_subject(state) == "F"
        
        # Infer from topics
        state = {
            "user_subject": None,
            "detected_topics": ["matematik", "kesir"]
        }
        assert get_effective_subject(state) == "M"
        
        print("✅ Effective subject test passed!")


class TestDecorators:
    """Tests for decorators"""
    
    def test_timeout_decorator_exists(self):
        """Test timeout decorator exists"""
        from src.agents.decorators import with_timeout
        assert callable(with_timeout)
        print("✅ with_timeout decorator exists!")
    
    def test_error_handling_decorator_exists(self):
        """Test error handling decorator exists"""
        from src.agents.decorators import with_error_handling
        assert callable(with_error_handling)
        print("✅ with_error_handling decorator exists!")


class TestNodes:
    """Tests for graph nodes"""
    
    def test_node_registry(self):
        """Test node registry contains all nodes"""
        from src.agents.nodes import NODE_REGISTRY
        
        expected_nodes = [
            "analyze_input",
            "retrieve_kazanimlar",
            "retrieve_textbook",
            "rerank_results",
            "generate_response",
            "handle_error"
        ]
        
        for node in expected_nodes:
            assert node in NODE_REGISTRY, f"Missing node: {node}"
        
        print("✅ Node registry test passed!")


class TestConditions:
    """Tests for edge conditions"""
    
    def test_condition_registry(self):
        """Test condition registry"""
        from src.agents.conditions import CONDITION_REGISTRY
        
        expected = [
            "check_analysis_success",
            "check_retrieval_success",
            "check_has_results"
        ]
        
        for cond in expected:
            assert cond in CONDITION_REGISTRY, f"Missing condition: {cond}"
        
        print("✅ Condition registry test passed!")
    
    def test_analysis_success(self):
        """Test analysis success check"""
        from src.agents.conditions import check_analysis_success
        
        # Success case
        state = {"question_text": "Test", "error": None}
        assert check_analysis_success(state) == "continue"
        
        # Error case
        state = {"question_text": "", "error": None}
        assert check_analysis_success(state) == "error"
        
        print("✅ Analysis success condition test passed!")
    
    def test_retrieval_retry_logic(self):
        """Test retrieval retry logic"""
        from src.agents.conditions import check_retrieval_success, MAX_RETRIEVAL_RETRIES
        
        # Success case
        state = {
            "matched_kazanimlar": [{"id": 1}],
            "status": "processing",
            "retrieval_retry_count": 0
        }
        assert check_retrieval_success(state) == "continue"
        
        # Retry case
        state = {
            "matched_kazanimlar": [],
            "status": "needs_retry",
            "retrieval_retry_count": 1
        }
        assert check_retrieval_success(state) == "retry"
        
        # Max retries exceeded
        state = {
            "matched_kazanimlar": [],
            "status": "needs_retry",
            "retrieval_retry_count": MAX_RETRIEVAL_RETRIES
        }
        assert check_retrieval_success(state) == "error"
        
        print("✅ Retrieval retry logic test passed!")


class TestGraph:
    """Tests for graph assembly"""
    
    def test_graph_creation(self):
        """Test graph can be created"""
        from src.agents.graph import create_meb_rag_graph
        
        graph = create_meb_rag_graph()
        assert graph is not None
        print("✅ Graph creation test passed!")
    
    def test_meb_rag_graph_class(self):
        """Test MebRagGraph class"""
        from src.agents.graph import MebRagGraph
        
        rag = MebRagGraph(use_memory=True)
        assert rag.graph is not None
        print("✅ MebRagGraph class test passed!")


if __name__ == "__main__":
    # Run tests
    test_state = TestQuestionAnalysisState()
    test_state.test_state_creation()
    test_state.test_effective_grade()
    test_state.test_effective_subject()
    
    test_dec = TestDecorators()
    test_dec.test_timeout_decorator_exists()
    test_dec.test_error_handling_decorator_exists()
    
    test_nodes = TestNodes()
    test_nodes.test_node_registry()
    
    test_cond = TestConditions()
    test_cond.test_condition_registry()
    test_cond.test_analysis_success()
    test_cond.test_retrieval_retry_logic()
    
    test_graph = TestGraph()
    test_graph.test_graph_creation()
    test_graph.test_meb_rag_graph_class()
    
    print("\n✅ All Phase 6 tests passed!")
