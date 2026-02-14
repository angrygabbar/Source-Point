"""
MCQ Questions Seed Runner
Run this inside the Docker container:
    docker-compose exec web python seed_questions/runner.py
"""
import sys, os
# Add parent dir (for app, extensions, models imports)
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
# Add seed_questions dir itself (for question module imports)
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from app import create_app
from extensions import db
from models.mcq import MCQQuestion
from models.auth import User

# Import all category question sets (shuffled originals)
from java_questions import JAVA_QUESTIONS
from python_questions import PYTHON_QUESTIONS
from nodejs_questions import NODEJS_QUESTIONS
from angular_questions import ANGULAR_QUESTIONS
from ba_questions import BA_QUESTIONS

# Import new additional questions (batch 1)
from new_java_questions import NEW_JAVA_QUESTIONS
from new_python_questions import NEW_PYTHON_QUESTIONS
from new_nodejs_questions import NEW_NODEJS_QUESTIONS
from new_angular_questions import NEW_ANGULAR_QUESTIONS
from new_ba_questions import NEW_BA_QUESTIONS

# Import bulk questions (batch 1)
from generate_bulk_questions import JAVA_EXTRA
from bulk_python import PYTHON_EXTRA
from bulk_nodejs import NODEJS_EXTRA
from bulk_angular import ANGULAR_EXTRA
from bulk_ba import BA_EXTRA

# Import bulk questions (batch 2)
from bulk_java_2 import JAVA_EXTRA_2
from bulk_python_2 import PYTHON_EXTRA_2
from bulk_nodejs_2 import NODEJS_EXTRA_2
from bulk_angular_2 import ANGULAR_EXTRA_2
from bulk_ba_2 import BA_EXTRA_2

# Import bulk questions (batch 3)
from bulk_java_3 import JAVA_EXTRA_3
from bulk_python_3 import PYTHON_EXTRA_3
from bulk_nodejs_3 import NODEJS_EXTRA_3
from bulk_angular_3 import ANGULAR_EXTRA_3
from bulk_ba_3 import BA_EXTRA_3

# Import bulk questions (batch 4) - Node.js, Angular, BA need more to reach 300
from bulk_nodejs_4 import NODEJS_EXTRA_4
from bulk_angular_4 import ANGULAR_EXTRA_4
from bulk_ba_4 import BA_EXTRA_4

# Import bulk questions (batch 5) - Angular and BA need more to reach 300
from bulk_angular_5 import ANGULAR_EXTRA_5
from bulk_ba_5 import BA_EXTRA_5

ALL_CATEGORIES = {
    'Java Developer': JAVA_QUESTIONS + NEW_JAVA_QUESTIONS + JAVA_EXTRA + JAVA_EXTRA_2 + JAVA_EXTRA_3,
    'Python Developer': PYTHON_QUESTIONS + NEW_PYTHON_QUESTIONS + PYTHON_EXTRA + PYTHON_EXTRA_2 + PYTHON_EXTRA_3,
    'Node.js Developer': NODEJS_QUESTIONS + NEW_NODEJS_QUESTIONS + NODEJS_EXTRA + NODEJS_EXTRA_2 + NODEJS_EXTRA_3 + NODEJS_EXTRA_4,
    'Angular Developer': ANGULAR_QUESTIONS + NEW_ANGULAR_QUESTIONS + ANGULAR_EXTRA + ANGULAR_EXTRA_2 + ANGULAR_EXTRA_3 + ANGULAR_EXTRA_4 + ANGULAR_EXTRA_5,
    'Business Analyst': BA_QUESTIONS + NEW_BA_QUESTIONS + BA_EXTRA + BA_EXTRA_2 + BA_EXTRA_3 + BA_EXTRA_4 + BA_EXTRA_5,
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
        total_updated = 0
        for category, questions in ALL_CATEGORIES.items():
            existing = MCQQuestion.query.filter_by(category=category).count()
            print(f"\n{'='*60}")
            print(f"Category: {category}")
            print(f"Questions in file: {len(questions)}")
            print(f"Already in database: {existing}")
            
            added = 0
            updated = 0
            for q in questions:
                # Check for duplicate by question text
                exists = MCQQuestion.query.filter_by(
                    question_text=q['question_text'],
                    category=category
                ).first()
                if exists:
                    # Update options and correct answer (in case shuffled)
                    changed = False
                    if exists.option_a != q['option_a']:
                        exists.option_a = q['option_a']
                        changed = True
                    if exists.option_b != q['option_b']:
                        exists.option_b = q['option_b']
                        changed = True
                    if exists.option_c != q['option_c']:
                        exists.option_c = q['option_c']
                        changed = True
                    if exists.option_d != q['option_d']:
                        exists.option_d = q['option_d']
                        changed = True
                    if exists.correct_option != q['correct_option']:
                        exists.correct_option = q['correct_option']
                        changed = True
                    if changed:
                        updated += 1
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
            total_updated += updated
            print(f"Added: {added} new questions")
            print(f"Updated: {updated} existing questions (shuffled options)")
        
        print(f"\n{'='*60}")
        print(f"TOTAL NEW QUESTIONS ADDED: {total_added}")
        print(f"TOTAL EXISTING UPDATED: {total_updated}")
        print(f"TOTAL IN DATABASE: {MCQQuestion.query.count()}")
        
        # Print distribution check
        print(f"\n{'='*60}")
        print("ANSWER DISTRIBUTION CHECK:")
        for category in ALL_CATEGORIES.keys():
            questions = MCQQuestion.query.filter_by(category=category).all()
            dist = {'A': 0, 'B': 0, 'C': 0, 'D': 0}
            for q in questions:
                dist[q.correct_option] = dist.get(q.correct_option, 0) + 1
            print(f"  {category}: {len(questions)} total | A:{dist['A']} B:{dist['B']} C:{dist['C']} D:{dist['D']}")

if __name__ == '__main__':
    seed_questions()
