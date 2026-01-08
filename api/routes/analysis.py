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
            summary=response_data.get("summary"),
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
        
        # Extract textbook references from related_chunks
        related_chunks = result.get("related_chunks", [])
        textbook_refs = []
        for chunk in related_chunks:
            textbook_refs.append({
                "chapter": chunk.get("hierarchy_path", ""),
                "pages": chunk.get("page_range", ""),
                "content": chunk.get("content", "")[:500] if chunk.get("content") else "",
                "relevance": f"Eşleşme skoru: {chunk.get('score', 0):.2f}"
            })
        
        # Generate teacher explanation using GPT-5.2
        teacher_explanation = None
        try:
            from src.rag.teacher_synthesizer import TeacherSynthesizer
            synthesizer = TeacherSynthesizer()
            teacher_explanation = await synthesizer.synthesize(
                question_text=request.question_text,
                matched_kazanimlar=result.get("matched_kazanimlar", []),
                textbook_chunks=related_chunks,
                summary=response_data.get("summary")
            )
        except Exception as synth_error:
            # Log but don't fail - teacher explanation is optional enhancement
            print(f"Teacher synthesis error: {synth_error}")
            teacher_explanation = None
        
        total_time = int((time.time() - start_time) * 1000)
        
        return AnalysisResponse(
            analysis_id=result.get("analysis_id", ""),
            status=result.get("status", "unknown"),
            summary=response_data.get("summary"),
            teacher_explanation=teacher_explanation,
            matched_kazanimlar=[
                KazanimMatch(
                    code=k.get("kazanim_code", ""),
                    description=k.get("kazanim_description", ""),
                    score=k.get("score", 0),
                    grade=k.get("grade"),
                    subject=k.get("subject"),
                    reason=None
                )
                for k in result.get("matched_kazanimlar", [])
            ],
            textbook_references=textbook_refs,
            question_text=result.get("question_text"),
            detected_topics=result.get("detected_topics", []),
            confidence=response_data.get("confidence", 0) if isinstance(response_data, dict) else 0,
            processing_time_ms=total_time,
            error=result.get("error")
        )
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/text-stream")
async def analyze_text_stream(request: AnalyzeTextRequest):
    """
    Stream analysis with GPT-5.2 teacher explanation.
    
    First does RAG retrieval, then streams the teacher explanation token by token.
    """
    async def event_generator() -> AsyncGenerator[str, None]:
        try:
            # Step 1: Do RAG retrieval (non-streaming)
            graph = get_graph()
            result = await graph.analyze(
                question_text=request.question_text,
                user_grade=request.grade,
                user_subject=request.subject,
                is_exam_mode=request.is_exam_mode
            )
            
            # Send RAG results first
            response_data = result.get("response", {})
            matched_kazanimlar = result.get("matched_kazanimlar", [])
            related_chunks = result.get("related_chunks", [])
            
            # Format textbook refs
            textbook_refs = []
            for chunk in related_chunks:
                textbook_refs.append({
                    "chapter": chunk.get("hierarchy_path", ""),
                    "pages": chunk.get("page_range", ""),
                    "content": chunk.get("content", "")[:500] if chunk.get("content") else ""
                })
            
            # Send initial data
            rag_data = {
                "event": "rag_complete",
                "data": {
                    "analysis_id": result.get("analysis_id", ""),
                    "status": result.get("status", "unknown"),
                    "summary": response_data.get("summary"),
                    "matched_kazanimlar": [
                        {
                            "code": k.get("kazanim_code", ""),
                            "description": k.get("kazanim_description", ""),
                            "score": k.get("score", 0),
                            "grade": k.get("grade")
                        }
                        for k in matched_kazanimlar
                    ],
                    "textbook_references": textbook_refs,
                    "confidence": response_data.get("confidence", 0) if isinstance(response_data, dict) else 0
                }
            }
            yield f"data: {json.dumps(rag_data, ensure_ascii=False)}\n\n"
            
            # Step 2: Stream teacher explanation
            yield f"data: {json.dumps({'event': 'teacher_start'})}\n\n"
            
            from src.rag.teacher_synthesizer import TeacherSynthesizer
            synthesizer = TeacherSynthesizer()
            
            async for token in synthesizer.synthesize_stream(
                question_text=request.question_text,
                matched_kazanimlar=matched_kazanimlar,
                textbook_chunks=related_chunks,
                summary=response_data.get("summary")
            ):
                yield f"data: {json.dumps({'event': 'teacher_token', 'token': token}, ensure_ascii=False)}\n\n"
            
            yield f"data: {json.dumps({'event': 'done'})}\n\n"
            
        except Exception as e:
            yield f"data: {json.dumps({'event': 'error', 'error': str(e)})}\n\n"
    
    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no"
        }
    )


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
