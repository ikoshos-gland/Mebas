"""
MEB RAG Sistemi - Content Routes
Serve static content like images safely
"""
import os
from fastapi import APIRouter, HTTPException, Depends
from fastapi.responses import FileResponse
from sqlalchemy.orm import Session

from src.database.db import get_session
from src.database.models import TextbookImage

router = APIRouter(prefix="/content", tags=["Content"])

@router.get("/images/{image_id}")
async def get_image(image_id: str, db: Session = Depends(get_session)):
    """
    Serve a textbook image by ID.
    
    This endpoint looks up the file path in the database 
    and serves the actual image file.
    """
    try:
        # Lookup image in DB
        image_record = db.query(TextbookImage).filter(TextbookImage.id == image_id).first()
        
        if not image_record:
            raise HTTPException(status_code=404, detail="Image not found")
            
        file_path = image_record.image_path
        
        # Verify file exists
        if not os.path.exists(file_path):
            raise HTTPException(status_code=404, detail="Image file not found on server")
            
        # Serve file
        return FileResponse(file_path)
        
    except Exception as e:
        # If it's already an HTTP exception, re-raise
        if isinstance(e, HTTPException):
            raise e
        # Log unexpected errors
        print(f"Error serving image {image_id}: {str(e)}")
        raise HTTPException(status_code=500, detail="Error serving image") 
