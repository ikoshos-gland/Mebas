"""
MEB RAG Sistemi - Analysis Routes
Question analysis endpoints
"""
from fastapi import APIRouter, HTTPException, Depends
from fastapi.responses import StreamingResponse
from typing import AsyncGenerator
import time
import json

from api.models import (
    AnalyzeImageRequest,
    AnalyzeTextRequest,
    AnalysisResponse,
    KazanimMatch,
    PrerequisiteGap
)
from src.agents import MebRagGraph, get_effective_grade


router = APIRouter(prefix="/analyze", tags=["Analysis"])


# Singleton graph instance
_graph_instance = None

def get_graph() -> MebRagGraph:
    """Get or create graph instance"""
    global _graph_instance
    if _graph_instance is None:
        _graph_instance = MebRagGraph(use_memory=True)
    return _graph_instance


@router.post("/image", response_model=AnalysisResponse)
async def analyze_image(request: AnalyzeImageRequest):
    """
    Analyze a question image.
    
    Upload a base64 encoded image of a student question
    and receive matched kazanımlar and study suggestions.
    """
    start_time = time.time()
    
    try:
        graph = get_graph()
        
        # Run analysis
        result = await graph.analyze(
            question_image_base64=request.image_base64,
            user_grade=request.grade,
            user_subject=request.subject,
            is_exam_mode=request.is_exam_mode
        )
        
        processing_time = int((time.time() - start_time) * 1000)
        
        # Extract response data
        response_data = result.get("response", {})
        
        return AnalysisResponse(
            analysis_id=result.get("analysis_id", ""),
            status=result.get("status", "unknown"),
            summary=response_data.get("message"),
            matched_kazanimlar=[
                KazanimMatch(
                    code=k.get("kazanim_code", ""),
                    description=k.get("kazanim_description", ""),
                    score=k.get("score", 0),
                    reason=None
                )
                for k in result.get("matched_kazanimlar", [])
            ],
            prerequisite_gaps=[
                PrerequisiteGap(
                    kazanim_code=g.get("missing_kazanim_code", ""),
                    description=g.get("missing_kazanim_description", ""),
                    importance=g.get("importance", ""),
                    suggestion=g.get("suggestion", "")
                )
                for g in result.get("prerequisite_gaps", [])
            ],
            question_text=result.get("question_text"),
            detected_topics=result.get("detected_topics", []),
            confidence=response_data.get("confidence", 0) if isinstance(response_data, dict) else 0,
            processing_time_ms=processing_time,
            error=result.get("error")
        )
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/text", response_model=AnalysisResponse)
async def analyze_text(request: AnalyzeTextRequest):
    """
    Analyze a text question.
    
    Submit a question text and receive matched kazanımlar
    and study suggestions.
    """
    start_time = time.time()
    
    try:
        graph = get_graph()
        
        result = await graph.analyze(
            question_text=request.question_text,
            user_grade=request.grade,
            user_subject=request.subject,
            is_exam_mode=request.is_exam_mode
        )
        
        processing_time = int((time.time() - start_time) * 1000)
        
        response_data = result.get("response", {})
        
        return AnalysisResponse(
            analysis_id=result.get("analysis_id", ""),
            status=result.get("status", "unknown"),
            summary=response_data.get("message"),
            matched_kazanimlar=[
                KazanimMatch(
                    code=k.get("kazanim_code", ""),
                    description=k.get("kazanim_description", ""),
                    score=k.get("score", 0),
                    reason=None
                )
                for k in result.get("matched_kazanimlar", [])
            ],
            question_text=result.get("question_text"),
            detected_topics=result.get("detected_topics", []),
            processing_time_ms=processing_time,
            error=result.get("error")
        )
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/stream")
async def analyze_stream(request: AnalyzeTextRequest):
    """
    Stream analysis events using Server-Sent Events.
    
    Provides real-time updates as the analysis progresses.
    """
    async def event_generator() -> AsyncGenerator[str, None]:
        try:
            graph = get_graph()
            
            async for event in graph.stream_analysis(
                question_text=request.question_text,
                user_grade=request.grade,
                user_subject=request.subject,
                is_exam_mode=request.is_exam_mode
            ):
                # Format as SSE
                event_data = {
                    "event": event.get("event", "update"),
                    "data": event.get("data", {})
                }
                yield f"data: {json.dumps(event_data, ensure_ascii=False)}\n\n"
            
            yield "data: {\"event\": \"done\"}\n\n"
            
        except Exception as e:
            yield f"data: {{\"event\": \"error\", \"error\": \"{str(e)}\"}}\n\n"
    
    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive"
        }
    )
