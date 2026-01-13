#!/usr/bin/env python3
"""
SaaS Database Migration Script
Creates new tables for multi-tenant architecture

Run: python scripts/migrate_saas.py

This script:
1. Creates School, Classroom, StudentEnrollment, Assignment, ClassAssignment, AssignmentSubmission tables
2. Updates User table with school_id column
3. Creates necessary indexes
4. Optionally creates a demo school and admin user
"""
import sys
import os

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from sqlalchemy import text, inspect
from sqlalchemy.orm import Session
from datetime import datetime
import logging

from src.database.db import engine, get_db, Base
from src.database.models import (
    User, School, BillingRecord, Classroom, StudentEnrollment,
    Assignment, ClassAssignment, AssignmentSubmission
)

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)


def table_exists(table_name: str) -> bool:
    """Check if a table exists in the database."""
    inspector = inspect(engine)
    return table_name in inspector.get_table_names()


def column_exists(table_name: str, column_name: str) -> bool:
    """Check if a column exists in a table."""
    inspector = inspect(engine)
    columns = [col['name'] for col in inspector.get_columns(table_name)]
    return column_name in columns


def run_migration():
    """Run the SaaS migration."""
    logger.info("Starting SaaS migration...")

    # Create all tables from models
    logger.info("Creating tables from models...")
    Base.metadata.create_all(bind=engine)
    logger.info("Tables created successfully")

    # Verify tables were created
    tables_to_check = [
        'schools', 'billing_records', 'classrooms',
        'student_enrollments', 'assignments',
        'class_assignments', 'assignment_submissions'
    ]

    for table in tables_to_check:
        if table_exists(table):
            logger.info(f"  ✓ {table}")
        else:
            logger.warning(f"  ✗ {table} - NOT CREATED")

    # Verify User table has school_id
    if table_exists('users'):
        if column_exists('users', 'school_id'):
            logger.info("  ✓ users.school_id column exists")
        else:
            logger.warning("  ✗ users.school_id column does not exist")
            logger.info("Adding school_id column to users table...")
            with engine.begin() as conn:
                conn.execute(text("""
                    ALTER TABLE users
                    ADD COLUMN school_id INTEGER REFERENCES schools(id)
                """))
            logger.info("  ✓ users.school_id added")

    logger.info("Migration completed successfully!")


def create_demo_data():
    """Create demo school and admin user for testing."""
    logger.info("Creating demo data...")

    db = next(get_db())
    try:
        # Check if demo school already exists
        existing_school = db.query(School).filter(School.slug == "demo-okulu").first()
        if existing_school:
            logger.info("Demo school already exists, skipping...")
            return

        # Create demo school
        demo_school = School(
            name="Demo Okulu",
            slug="demo-okulu",
            admin_email="admin@demo.edu.tr",
            tier="medium",
            max_students=500,
            max_teachers=50,
            is_active=True,
            features={
                "exam_generator": True,
                "progress_tracking": True,
                "ai_chat": True
            }
        )
        db.add(demo_school)
        db.flush()
        logger.info(f"Created demo school: {demo_school.name} (ID: {demo_school.id})")

        # Find or create platform admin
        platform_admin = db.query(User).filter(User.role == "platform_admin").first()
        if not platform_admin:
            logger.info("No platform admin found. You'll need to create one manually or update an existing user.")
        else:
            logger.info(f"Platform admin exists: {platform_admin.email}")

        # Create demo teacher for the school
        demo_teacher = db.query(User).filter(User.email == "teacher@demo.edu.tr").first()
        if not demo_teacher:
            # Generate a random firebase_uid for demo user
            import uuid
            demo_teacher = User(
                firebase_uid=f"demo_teacher_{uuid.uuid4().hex[:16]}",
                email="teacher@demo.edu.tr",
                full_name="Demo Ogretmen",
                role="teacher",
                school_id=demo_school.id,
                is_active=True,
                is_verified=True,
                profile_complete=True
            )
            db.add(demo_teacher)
            db.flush()
            logger.info(f"Created demo teacher: {demo_teacher.email}")
        else:
            if demo_teacher.school_id != demo_school.id:
                demo_teacher.school_id = demo_school.id
                logger.info(f"Updated demo teacher school_id")

        # Create demo classroom
        demo_classroom = Classroom(
            school_id=demo_school.id,
            teacher_id=demo_teacher.id,
            name="10-A Matematik",
            grade=10,
            subject="Matematik",
            join_code="DEMO1234",
            join_enabled=True,
            is_active=True
        )
        db.add(demo_classroom)
        db.flush()
        logger.info(f"Created demo classroom: {demo_classroom.name} (Join code: {demo_classroom.join_code})")

        db.commit()
        logger.info("Demo data created successfully!")

    except Exception as e:
        db.rollback()
        logger.error(f"Error creating demo data: {e}")
        raise
    finally:
        db.close()


def show_stats():
    """Show current database statistics."""
    db = next(get_db())
    try:
        stats = {
            "Schools": db.query(School).count(),
            "Users": db.query(User).count(),
            "Teachers": db.query(User).filter(User.role == "teacher").count(),
            "Students": db.query(User).filter(User.role == "student").count(),
            "Classrooms": db.query(Classroom).count(),
            "Enrollments": db.query(StudentEnrollment).count(),
            "Assignments": db.query(Assignment).count(),
        }

        logger.info("\n=== Database Statistics ===")
        for key, value in stats.items():
            logger.info(f"  {key}: {value}")

    finally:
        db.close()


def main():
    """Main entry point."""
    import argparse

    parser = argparse.ArgumentParser(description="SaaS Database Migration")
    parser.add_argument('--demo', action='store_true', help='Create demo data')
    parser.add_argument('--stats', action='store_true', help='Show database statistics')
    args = parser.parse_args()

    if args.stats:
        show_stats()
        return

    # Run migration
    run_migration()

    if args.demo:
        create_demo_data()

    # Show stats after migration
    show_stats()


if __name__ == "__main__":
    main()
