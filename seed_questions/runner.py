"""
MCQ Questions Seed Runner
Run this inside the Docker container:
    docker-compose exec web python seed_questions/runner.py
"""
import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app import create_app
from extensions import db
from models.mcq import MCQQuestion
from models._init__ import User

# Import all category question sets
from java_questions import JAVA_QUESTIONS
from python_questions import PYTHON_QUESTIONS
from nodejs_questions import NODEJS_QUESTIONS
from angular_questions import ANGULAR_QUESTIONS
from ba_questions import BA_QUESTIONS

ALL_CATEGORIES = {
    'Java Developer': JAVA_QUESTIONS,
    'Python Developer': PYTHON_QUESTIONS,
    'Node.js Developer': NODEJS_QUESTIONS,
    'Angular Developer': ANGULAR_QUESTIONS,
    'Business Analyst': BA_QUESTIONS,
}

def seed_questions():
    app = create_app()
    with app.app_context():
        # Get admin user (first admin or first user)
        admin = User.query.filter_by(role='admin').first()
        if not admin:
            admin = User.query.first()
        if not admin:
            print("ERROR: No users found in database. Create a user first.")
            return
        
        print(f"Using admin user: {admin.username} (ID: {admin.id})")
        
        total_added = 0
        for category, questions in ALL_CATEGORIES.items():
            existing = MCQQuestion.query.filter_by(category=category).count()
            print(f"\n{'='*60}")
            print(f"Category: {category}")
            print(f"Questions to add: {len(questions)}")
            print(f"Already existing: {existing}")
            
            added = 0
            for q in questions:
                # Check for duplicate by question text
                exists = MCQQuestion.query.filter_by(
                    question_text=q['question_text'],
                    category=category
                ).first()
                if exists:
                    continue
                
                question = MCQQuestion(
                    question_text=q['question_text'],
                    option_a=q['option_a'],
                    option_b=q['option_b'],
                    option_c=q['option_c'],
                    option_d=q['option_d'],
                    correct_option=q['correct_option'],
                    category=category,
                    created_by_id=admin.id
                )
                db.session.add(question)
                added += 1
            
            db.session.commit()
            total_added += added
            print(f"Added: {added} new questions")
        
        print(f"\n{'='*60}")
        print(f"TOTAL QUESTIONS ADDED: {total_added}")
        print(f"TOTAL IN DATABASE: {MCQQuestion.query.count()}")

if __name__ == '__main__':
    seed_questions()
