"""
MEB RAG Sistemi - Veri Aktarım Fonksiyonları
Import Phase 2 data (chunks, images) into Phase 3 database
"""
from typing import List, Optional
from pathlib import Path

from src.database.db import SessionLocal, get_db_context
from src.database.models import (
    Subject, Kazanim, Textbook, Chapter, 
    BookChunk, TextbookImage
)


def import_semantic_chunks(
    chunks: list, 
    chapter_id: int,
    related_kazanim_id: Optional[int] = None
) -> List[str]:
    """
    Import Phase 2 SemanticChunk objects into database.
    
    Args:
        chunks: List of SemanticChunk from Phase 2
        chapter_id: ID of the parent Chapter
        related_kazanim_id: Optional kazanim ID to link
        
    Returns:
        List of created chunk IDs
    """
    created_ids = []
    
    with get_db_context() as db:
        for chunk in chunks:
            db_chunk = BookChunk(
                id=chunk.chunk_id,
                chapter_id=chapter_id,
                content=chunk.content,
                chunk_type=chunk.chunk_type,
                hierarchy_path=chunk.hierarchy_path,
                page_range=f"{chunk.page_range[0]}-{chunk.page_range[1]}",
                is_sidebar=chunk.is_sidebar_content,
                element_count=chunk.metadata.get("element_count", 0),
                related_kazanim_id=related_kazanim_id
            )
            db.add(db_chunk)
            created_ids.append(chunk.chunk_id)
    
    print(f"✅ {len(created_ids)} chunk veritabanına aktarıldı")
    return created_ids


def import_extracted_images(
    images: list, 
    chunk_id: str
) -> List[str]:
    """
    Import Phase 2 ExtractedImage objects into database.
    
    Args:
        images: List of ExtractedImage from Phase 2
        chunk_id: ID of the parent BookChunk
        
    Returns:
        List of created image IDs
    """
    created_ids = []
    
    with get_db_context() as db:
        for img in images:
            db_image = TextbookImage(
                id=img.image_id,
                chunk_id=chunk_id,
                image_path=str(img.image_path) if img.image_path else None,
                width=img.width,
                height=img.height,
                caption=img.caption,
                image_type=img.image_type,
                page_number=img.page_number
            )
            db.add(db_image)
            created_ids.append(img.image_id)
    
    print(f"✅ {len(created_ids)} görsel veritabanına aktarıldı")
    return created_ids


def create_subject(code: str, name: str) -> Subject:
    """Create a new subject"""
    with get_db_context() as db:
        subject = Subject(code=code, name=name)
        db.add(subject)
        db.flush()
        subject_id = subject.id
    
    return get_subject_by_code(code)


def get_subject_by_code(code: str) -> Optional[Subject]:
    """Get subject by code"""
    with get_db_context() as db:
        return db.query(Subject).filter_by(code=code).first()


def create_textbook(
    title: str,
    grade: int,
    subject_code: str,
    publisher: str = "",
    year: int = 2024,
    pdf_path: str = ""
) -> Textbook:
    """Create a new textbook"""
    with get_db_context() as db:
        subject = db.query(Subject).filter_by(code=subject_code).first()
        if not subject:
            raise ValueError(f"Subject with code '{subject_code}' not found")
        
        textbook = Textbook(
            title=title,
            grade=grade,
            subject_id=subject.id,
            publisher=publisher,
            year=year,
            pdf_path=pdf_path
        )
        db.add(textbook)
        db.flush()
        textbook_id = textbook.id
    
    return get_textbook_by_id(textbook_id)


def get_textbook_by_id(textbook_id: int) -> Optional[Textbook]:
    """Get textbook by ID"""
    with get_db_context() as db:
        return db.query(Textbook).filter_by(id=textbook_id).first()


def create_chapter(
    textbook_id: int,
    number: int,
    title: str,
    page_start: int,
    page_end: int
) -> Chapter:
    """Create a new chapter"""
    with get_db_context() as db:
        chapter = Chapter(
            textbook_id=textbook_id,
            number=number,
            title=title,
            page_start=page_start,
            page_end=page_end
        )
        db.add(chapter)
        db.flush()
        chapter_id = chapter.id
    
    return get_chapter_by_id(chapter_id)


def get_chapter_by_id(chapter_id: int) -> Optional[Chapter]:
    """Get chapter by ID"""
    with get_db_context() as db:
        return db.query(Chapter).filter_by(id=chapter_id).first()


def create_kazanim(
    code: str,
    description: str,
    grade: int,
    subject_code: str,
    learning_area: str = "",
    sub_learning_area: str = "",
    unit_number: int = 0,
    topic_number: int = 0,
    bloom_level: str = ""
) -> Kazanim:
    """Create a new kazanim"""
    with get_db_context() as db:
        subject = db.query(Subject).filter_by(code=subject_code).first()
        if not subject:
            raise ValueError(f"Subject with code '{subject_code}' not found")
        
        kazanim = Kazanim(
            code=code,
            description=description,
            grade=grade,
            subject_id=subject.id,
            learning_area=learning_area,
            sub_learning_area=sub_learning_area,
            unit_number=unit_number,
            topic_number=topic_number,
            bloom_level=bloom_level
        )
        db.add(kazanim)
    
    return get_kazanim_by_code(code)


def get_kazanim_by_code(code: str) -> Optional[Kazanim]:
    """Get kazanim by code"""
    with get_db_context() as db:
        return db.query(Kazanim).filter_by(code=code).first()


def get_kazanimlar_by_grade(grade: int, subject_code: Optional[str] = None) -> List[Kazanim]:
    """Get all kazanimlar for a grade, optionally filtered by subject"""
    with get_db_context() as db:
        query = db.query(Kazanim).filter_by(grade=grade)
        if subject_code:
            subject = db.query(Subject).filter_by(code=subject_code).first()
            if subject:
                query = query.filter_by(subject_id=subject.id)
        return query.all()


def link_chunk_to_kazanim(chunk_id: str, kazanim_code: str) -> bool:
    """Link a BookChunk to a Kazanim"""
    with get_db_context() as db:
        chunk = db.query(BookChunk).filter_by(id=chunk_id).first()
        kazanim = db.query(Kazanim).filter_by(code=kazanim_code).first()
        
        if not chunk or not kazanim:
            return False
        
        chunk.related_kazanim_id = kazanim.id
    
    return True


def import_full_document(
    textbook_id: int,
    chapter_data: dict,
    chunks: list,
    images_by_chunk: dict
) -> dict:
    """
    Import a complete document with chapters, chunks, and images.
    
    Args:
        textbook_id: Parent textbook ID
        chapter_data: Dict with number, title, page_start, page_end
        chunks: List of SemanticChunk from Phase 2
        images_by_chunk: Dict mapping chunk_id -> List[ExtractedImage]
        
    Returns:
        Dict with created IDs
    """
    result = {"chapter_id": None, "chunk_ids": [], "image_ids": []}
    
    with get_db_context() as db:
        # Create chapter
        chapter = Chapter(
            textbook_id=textbook_id,
            number=chapter_data["number"],
            title=chapter_data["title"],
            page_start=chapter_data["page_start"],
            page_end=chapter_data["page_end"]
        )
        db.add(chapter)
        db.flush()
        result["chapter_id"] = chapter.id
        
        # Create chunks
        for chunk in chunks:
            db_chunk = BookChunk(
                id=chunk.chunk_id,
                chapter_id=chapter.id,
                content=chunk.content,
                chunk_type=chunk.chunk_type,
                hierarchy_path=chunk.hierarchy_path,
                page_range=f"{chunk.page_range[0]}-{chunk.page_range[1]}",
                is_sidebar=chunk.is_sidebar_content,
                element_count=chunk.metadata.get("element_count", 0)
            )
            db.add(db_chunk)
            result["chunk_ids"].append(chunk.chunk_id)
            
            # Create images for this chunk
            if chunk.chunk_id in images_by_chunk:
                for img in images_by_chunk[chunk.chunk_id]:
                    db_image = TextbookImage(
                        id=img.image_id,
                        chunk_id=chunk.chunk_id,
                        image_path=str(img.image_path) if img.image_path else None,
                        width=img.width,
                        height=img.height,
                        caption=img.caption,
                        image_type=img.image_type,
                        page_number=img.page_number
                    )
                    db.add(db_image)
                    result["image_ids"].append(img.image_id)
    
    print(f"✅ Bölüm aktarıldı: {len(result['chunk_ids'])} chunk, {len(result['image_ids'])} görsel")
    return result
