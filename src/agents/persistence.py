"""
MEB RAG Sistemi - LangGraph Persistence
PostgresSaver for production state persistence
"""
from typing import Optional
import os


def get_postgres_checkpointer():
    """
    Get PostgresSaver for production environment.
    
    Requires:
    - langgraph-checkpoint-postgres package
    - DATABASE_URL environment variable
    
    Returns:
        PostgresSaver instance or None if not available
    """
    try:
        from langgraph.checkpoint.postgres import PostgresSaver
        
        # Get database URL from environment
        database_url = os.environ.get("DATABASE_URL")
        
        if not database_url:
            print("Warning: DATABASE_URL not set, falling back to memory")
            return None
        
        # Convert to async-compatible URL if needed
        if database_url.startswith("postgresql://"):
            # langgraph-checkpoint-postgres needs psycopg connection
            return PostgresSaver.from_conn_string(database_url)
        
        return None
        
    except ImportError:
        print("Warning: langgraph-checkpoint-postgres not installed")
        return None
    except Exception as e:
        print(f"Error creating PostgresSaver: {e}")
        return None


class ProductionCheckpointer:
    """
    Factory for production-ready checkpointing.
    
    Tries PostgresSaver first, falls back to MemorySaver.
    """
    
    _instance = None
    
    @classmethod
    def get_instance(cls):
        """Get singleton checkpointer instance"""
        if cls._instance is None:
            postgres = get_postgres_checkpointer()
            if postgres:
                cls._instance = postgres
            else:
                from langgraph.checkpoint.memory import MemorySaver
                cls._instance = MemorySaver()
        
        return cls._instance
    
    @classmethod
    def reset(cls):
        """Reset singleton (for testing)"""
        cls._instance = None


async def setup_postgres_tables():
    """
    Set up required tables for PostgresSaver.
    
    Call this once at application startup.
    """
    try:
        from langgraph.checkpoint.postgres import PostgresSaver
        
        database_url = os.environ.get("DATABASE_URL")
        if not database_url:
            return False
        
        checkpointer = PostgresSaver.from_conn_string(database_url)
        
        # Create tables
        await checkpointer.setup()
        
        print("✅ PostgresSaver tables created")
        return True
        
    except Exception as e:
        print(f"Error setting up PostgresSaver tables: {e}")
        return False
