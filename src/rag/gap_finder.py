"""
MEB RAG Sistemi - Prerequisite Gap Finder
Detects missing prerequisite knowledge using kazanım relationships
"""
from typing import List, Dict, Any, Optional
from sqlalchemy.orm import Session

from src.database.models import Kazanim, kazanim_prerequisites


class GapFinder:
    """
    Finds prerequisite knowledge gaps for matched kazanımlar.
    
    Uses the kazanim_prerequisites many-to-many relationship
    from the database to identify missing prerequisites.
    """
    
    def __init__(self, db_session: Optional[Session] = None):
        """
        Args:
            db_session: SQLAlchemy session for database queries
        """
        self.db_session = db_session
    
    def find_gaps(
        self,
        matched_kazanim_codes: List[str],
        student_grade: Optional[int] = None
    ) -> List[Dict[str, Any]]:
        """
        Find prerequisite gaps for given kazanımlar.
        
        Args:
            matched_kazanim_codes: List of kazanım codes the student is working on
            student_grade: Student's grade level for filtering
            
        Returns:
            List of prerequisite gap dicts
        """
        if not self.db_session:
            return []
        
        gaps = []
        
        for code in matched_kazanim_codes:
            # Get the kazanım and its prerequisites
            kazanim = self.db_session.query(Kazanim).filter_by(code=code).first()
            
            if not kazanim:
                continue
            
            # Get prerequisites
            prerequisites = kazanim.prerequisites
            
            for prereq in prerequisites:
                # Filter by grade if provided (only show prerequisites at or below grade)
                if student_grade and prereq.grade > student_grade:
                    continue
                
                gaps.append({
                    "missing_kazanim_code": prereq.code,
                    "missing_kazanim_description": prereq.description,
                    "importance": self._determine_importance(kazanim, prereq),
                    "suggestion": self._generate_suggestion(prereq),
                    "required_by": code
                })
        
        # Remove duplicates
        seen = set()
        unique_gaps = []
        for gap in gaps:
            if gap["missing_kazanim_code"] not in seen:
                seen.add(gap["missing_kazanim_code"])
                unique_gaps.append(gap)
        
        return unique_gaps
    
    def find_gaps_from_analysis(
        self,
        matched_kazanimlar: List[Dict[str, Any]],
        student_grade: Optional[int] = None
    ) -> List[Dict[str, Any]]:
        """
        Convenience method that takes retrieval results directly.
        
        Args:
            matched_kazanimlar: Retrieval results from Phase 4
            student_grade: Student's grade level
            
        Returns:
            List of prerequisite gap dicts
        """
        codes = [k.get("kazanim_code", "") for k in matched_kazanimlar if k.get("kazanim_code")]
        return self.find_gaps(codes, student_grade)
    
    def _determine_importance(self, target: Kazanim, prereq: Kazanim) -> str:
        """Determine how important the prerequisite is"""
        grade_diff = target.grade - prereq.grade
        
        if grade_diff >= 2:
            return "Kritik - Bu temel kavramı mutlaka öğrenmelisiniz"
        elif grade_diff == 1:
            return "Önemli - Bu konuyu gözden geçirmeniz faydalı olacaktır"
        else:
            return "Yardımcı - Bu konu bağlam sağlayacaktır"
    
    def _generate_suggestion(self, prereq: Kazanim) -> str:
        """Generate a study suggestion for the prerequisite"""
        return f"{prereq.grade}. sınıf {prereq.learning_area or 'ilgili'} konusunu çalışınız: {prereq.description}"


class SimpleGapFinder:
    """
    Simple gap finder without database (for testing/fallback).
    
    Uses heuristics based on kazanım codes to infer prerequisites.
    """
    
    def find_gaps(
        self,
        matched_kazanim_codes: List[str],
        student_grade: Optional[int] = None
    ) -> List[Dict[str, Any]]:
        """
        Find prerequisite gaps using code-based heuristics.
        
        Kazanım code format: M.5.1.2.3
        - M = subject
        - 5 = grade
        - 1 = unit
        - 2 = topic
        - 3 = subtopic
        
        Prerequisites are inferred as earlier topics in the same unit.
        """
        gaps = []
        
        for code in matched_kazanim_codes:
            parts = code.split(".")
            if len(parts) < 5:
                continue
            
            subject, grade_str, unit, topic, subtopic = parts[:5]
            grade = int(grade_str)
            
            # Only add gap if topic > 1 (earlier topics are prerequisites)
            if int(topic) > 1:
                prereq_code = f"{subject}.{grade_str}.{unit}.1.1"
                gaps.append({
                    "missing_kazanim_code": prereq_code,
                    "missing_kazanim_description": f"Ünite {unit} temel konuları",
                    "importance": "Bu ünitenin temel kavramlarını gözden geçirin",
                    "suggestion": f"Önce {prereq_code} kazanımını çalışın"
                })
            
            # If grade > provided student grade, suggest review
            if student_grade and grade > student_grade:
                gaps.append({
                    "missing_kazanim_code": f"{subject}.{student_grade}.1.1.1",
                    "missing_kazanim_description": f"{student_grade}. sınıf temel konuları",
                    "importance": "Bu konu sizin sınıf seviyenizin üstünde",
                    "suggestion": f"Önce {student_grade}. sınıf konularını pekiştirin"
                })
        
        return gaps
