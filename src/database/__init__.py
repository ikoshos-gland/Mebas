# Database module
from src.database.models import (
    Base,
    Subject,
    Kazanim,
    Textbook,
    Chapter,
    BookChunk,
    TextbookImage,
    Feedback,
    kazanim_prerequisites
)
from src.database.db import (
    engine,
    SessionLocal,
    init_db,
    drop_db,
    get_db,
    get_db_context,
    get_session
)
from src.database.import_chunks import (
    import_semantic_chunks,
    import_extracted_images,
    create_subject,
    get_subject_by_code,
    create_textbook,
    get_textbook_by_id,
    create_chapter,
    get_chapter_by_id,
    create_kazanim,
    get_kazanim_by_code,
    get_kazanimlar_by_grade,
    link_chunk_to_kazanim,
    import_full_document
)

__all__ = [
    # Models
    "Base",
    "Subject",
    "Kazanim", 
    "Textbook",
    "Chapter",
    "BookChunk",
    "TextbookImage",
    "Feedback",
    "kazanim_prerequisites",
    # Database
    "engine",
    "SessionLocal",
    "init_db",
    "drop_db",
    "get_db",
    "get_db_context",
    "get_session",
    # Import functions
    "import_semantic_chunks",
    "import_extracted_images",
    "create_subject",
    "get_subject_by_code",
    "create_textbook",
    "get_textbook_by_id",
    "create_chapter",
    "get_chapter_by_id",
    "create_kazanim",
    "get_kazanim_by_code",
    "get_kazanimlar_by_grade",
    "link_chunk_to_kazanim",
    "import_full_document",
]
