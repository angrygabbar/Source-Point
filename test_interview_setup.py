#!/usr/bin/env python
"""Test script to verify interview scheduling works"""
from app import app, db
from models.interview import Interview, InterviewParticipant
from models.auth import User
from datetime import datetime, timedelta

with app.app_context():
    print("=" * 50)
    print("Testing Interview Scheduling Setup")
    print("=" * 50)
    
    # Check if tables exist
    try:
        from sqlalchemy import inspect
        inspector = inspect(db.engine)
        tables = inspector.get_table_names()
        print(f"\n✓ Database tables: {len(tables)} tables found")
        print(f"  - interview table exists: {'interview' in tables}")
        print(f"  - interview_participant table exists: {'interview_participant' in tables}")
    except Exception as e:
        print(f"\n✗ Error checking tables: {e}")
    
    # Check if we can query Interview model
    try:
        count = Interview.query.count()
        print(f"\n✓ Interview model works: {count} interviews in database")
    except Exception as e:
        print(f"\n✗ Error querying Interview: {e}")
    
    # Check if we can query InterviewParticipant model
    try:
        count = InterviewParticipant.query.count()
        print(f"✓ InterviewParticipant model works: {count} participants in database")
    except Exception as e:
        print(f"✗ Error querying InterviewParticipant: {e}")
    
    # Check if we have users to test with
    try:
        candidates = User.query.filter_by(role='candidate', is_approved=True).count()
        moderators = User.query.filter_by(role='moderator', is_approved=True).count()
        print(f"\n✓ Users available:")
        print(f"  - Candidates: {candidates}")
        print(f"  - Moderators: {moderators}")
    except Exception as e:
        print(f"\n✗ Error querying Users: {e}")
    
    print("\n" + "=" * 50)
    print("Test Complete")
    print("=" * 50)
