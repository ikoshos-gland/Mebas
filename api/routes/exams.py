"""
MEB RAG Sistemi - Exam Routes
Sınav oluşturma ve yönetim endpoint'leri
"""
import logging
import os
from typing import List, Optional
from datetime import datetime

from fastapi import APIRouter, HTTPException, Depends, Request
from fastapi.responses import FileResponse
from sqlalchemy.orm import Session

from api.models import (
    ExamGenerateRequest,
    ExamGenerateResponse,
    ExamQuestionDetail,
    ExamListItem,
    ExamListResponse
)
from api.auth.deps import get_current_active_user
from src.database.db import get_db
from src.database.models import User, GeneratedExam, UserKazanimProgress
from src.exam.skill import ExamGeneratorService
from api.limiter import limiter

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/exams", tags=["Exams"])


def get_user_tracked_kazanimlar(db: Session, user_id: int, exclude_understood: bool = True) -> List[str]:
    """
    Kullanıcının takip ettiği kazanım kodlarını döndürür.

    Args:
        db: Database session
        user_id: Kullanıcı ID'si
        exclude_understood: True ise 'understood' durumundaki kazanımları hariç tutar

    Returns:
        Kazanım kodları listesi
    """
    query = db.query(UserKazanimProgress).filter(
        UserKazanimProgress.user_id == user_id
    )

    if exclude_understood:
        # Sadece 'tracked' ve 'in_progress' durumundaki kazanımları al
        query = query.filter(UserKazanimProgress.status != 'understood')

    progress_records = query.all()
    return [p.kazanim_code for p in progress_records]


@router.post("/generate", response_model=ExamGenerateResponse)
@limiter.limit("5/minute")
async def generate_exam(
    request: Request,
    body: ExamGenerateRequest,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """
    Sınav PDF'i oluşturur.

    Kullanıcının takip ettiği kazanımlara veya belirtilen kazanımlara göre
    soru seçimi yapar ve PDF oluşturur.

    Args:
        body: Sınav oluşturma isteği

    Returns:
        Oluşturulan sınav bilgileri ve download URL'i
    """
    try:
        # Kazanımları belirle
        kazanim_codes = body.kazanim_codes
        if not kazanim_codes:
            # Kullanıcının takip ettiği kazanımları al
            kazanim_codes = get_user_tracked_kazanimlar(db, current_user.id)

        if not kazanim_codes:
            raise HTTPException(
                status_code=400,
                detail="Sınav oluşturmak için en az bir kazanım gerekli. "
                       "Önce sohbet bölümünde sorular çözerek kazanım biriktirin."
            )

        # Sınav oluştur
        service = ExamGeneratorService()
        result = await service.generate(
            kazanim_codes=kazanim_codes,
            question_count=body.question_count,
            difficulty_distribution=body.difficulty_distribution,
            title=body.title
        )

        if not result.success:
            raise HTTPException(
                status_code=400,
                detail=result.error or "Sınav oluşturulamadı."
            )

        # Database'e kaydet
        exam = GeneratedExam(
            user_id=current_user.id,
            title=body.title,
            pdf_path=result.pdf_path,
            question_count=result.question_count,
            kazanimlar_json=result.kazanimlar_covered,
            questions_json=result.questions,
            difficulty_distribution={
                "kolay": sum(1 for q in result.questions if q.get("difficulty") == "kolay"),
                "orta": sum(1 for q in result.questions if q.get("difficulty") == "orta"),
                "zor": sum(1 for q in result.questions if q.get("difficulty") == "zor")
            }
        )
        db.add(exam)
        db.commit()
        db.refresh(exam)

        return ExamGenerateResponse(
            exam_id=exam.id,
            pdf_url=f"/exams/{exam.id}/download",
            kazanimlar_covered=result.kazanimlar_covered,
            question_count=result.question_count,
            questions=[
                ExamQuestionDetail(
                    file=q["file"],
                    kazanim=q["kazanim"],
                    difficulty=q["difficulty"],
                    answer=q.get("answer")
                )
                for q in result.questions
            ],
            created_at=exam.created_at,
            skipped_kazanimlar=result.skipped_kazanimlar or [],
            warning=result.warning
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Sınav oluşturma hatası: {e}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail=f"Sınav oluşturulurken bir hata oluştu: {str(e)}"
        )


@router.get("/{exam_id}/download")
async def download_exam(
    exam_id: str,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """
    Sınav PDF'ini indirir.

    Args:
        exam_id: Sınav ID'si

    Returns:
        PDF dosyası
    """
    # Sınavı bul
    exam = db.query(GeneratedExam).filter(
        GeneratedExam.id == exam_id,
        GeneratedExam.user_id == current_user.id
    ).first()

    if not exam:
        raise HTTPException(
            status_code=404,
            detail="Sınav bulunamadı."
        )

    # PDF dosyasını kontrol et
    if not os.path.exists(exam.pdf_path):
        raise HTTPException(
            status_code=404,
            detail="PDF dosyası bulunamadı."
        )

    # Dosya adını oluştur
    filename = f"{exam.title.replace(' ', '_')}_{exam.id[:8]}.pdf"

    return FileResponse(
        path=exam.pdf_path,
        media_type="application/pdf",
        filename=filename
    )


@router.get("/", response_model=ExamListResponse)
async def list_exams(
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db),
    limit: int = 20,
    offset: int = 0
):
    """
    Kullanıcının sınavlarını listeler.

    Args:
        limit: Sayfa boyutu
        offset: Başlangıç indeksi

    Returns:
        Sınav listesi
    """
    # Toplam sayı
    total = db.query(GeneratedExam).filter(
        GeneratedExam.user_id == current_user.id
    ).count()

    # Sınavları getir
    exams = db.query(GeneratedExam).filter(
        GeneratedExam.user_id == current_user.id
    ).order_by(
        GeneratedExam.created_at.desc()
    ).offset(offset).limit(limit).all()

    return ExamListResponse(
        exams=[
            ExamListItem(
                exam_id=exam.id,
                title=exam.title,
                question_count=exam.question_count,
                kazanimlar_count=len(exam.kazanimlar_json or []),
                pdf_url=f"/exams/{exam.id}/download",
                created_at=exam.created_at
            )
            for exam in exams
        ],
        total=total
    )


@router.delete("/{exam_id}")
async def delete_exam(
    exam_id: str,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """
    Sınavı siler.

    Args:
        exam_id: Silinecek sınav ID'si

    Returns:
        Silme sonucu
    """
    # Sınavı bul
    exam = db.query(GeneratedExam).filter(
        GeneratedExam.id == exam_id,
        GeneratedExam.user_id == current_user.id
    ).first()

    if not exam:
        raise HTTPException(
            status_code=404,
            detail="Sınav bulunamadı."
        )

    # PDF dosyasını sil
    if exam.pdf_path and os.path.exists(exam.pdf_path):
        try:
            os.remove(exam.pdf_path)
        except Exception as e:
            logger.warning(f"PDF dosyası silinemedi: {e}")

    # Database'den sil
    db.delete(exam)
    db.commit()

    return {"message": "Sınav başarıyla silindi.", "exam_id": exam_id}


@router.get("/{exam_id}", response_model=ExamGenerateResponse)
async def get_exam(
    exam_id: str,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """
    Sınav detaylarını getirir.

    Args:
        exam_id: Sınav ID'si

    Returns:
        Sınav detayları
    """
    exam = db.query(GeneratedExam).filter(
        GeneratedExam.id == exam_id,
        GeneratedExam.user_id == current_user.id
    ).first()

    if not exam:
        raise HTTPException(
            status_code=404,
            detail="Sınav bulunamadı."
        )

    return ExamGenerateResponse(
        exam_id=exam.id,
        pdf_url=f"/exams/{exam.id}/download",
        kazanimlar_covered=exam.kazanimlar_json or [],
        question_count=exam.question_count,
        questions=[
            ExamQuestionDetail(
                file=q.get("file", ""),
                kazanim=q.get("kazanim", ""),
                difficulty=q.get("difficulty", "orta"),
                answer=q.get("answer")
            )
            for q in (exam.questions_json or [])
        ],
        created_at=exam.created_at
    )


@router.get("/stats/available")
async def get_available_questions_stats(
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """
    Kullanıcının kazanımları için mevcut soru istatistiklerini döndürür.

    Returns:
        Kazanım başına mevcut soru sayıları
    """
    # Kullanıcının kazanımlarını al
    kazanim_codes = get_user_tracked_kazanimlar(db, current_user.id)

    if not kazanim_codes:
        return {
            "kazanimlar": [],
            "total_questions": 0,
            "message": "Henüz takip edilen kazanım yok."
        }

    # Mevcut soru sayılarını al
    service = ExamGeneratorService()
    counts = service.get_available_questions_count(kazanim_codes)

    return {
        "kazanimlar": [
            {"code": code, "available_questions": count}
            for code, count in counts.items()
        ],
        "total_questions": sum(counts.values()),
        "total_kazanimlar": len(kazanim_codes)
    }
