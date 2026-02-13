"""
Shuffle MCQ options so correct answers are evenly distributed across A, B, C, D.
Run this script to rewrite all question files with balanced answer distribution.
"""
import random
import json
import os
import sys

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

def shuffle_question_options(questions):
    """Shuffle options for each question, maintaining correct answer tracking."""
    target_distribution = ['A', 'B', 'C', 'D']
    shuffled = []
    
    for i, q in enumerate(questions):
        # Get the correct answer text
        correct_key = f"option_{q['correct_option'].lower()}"
        correct_text = q[correct_key]
        
        # Collect all options with their texts
        options = [
            q['option_a'],
            q['option_b'],
            q['option_c'],
            q['option_d']
        ]
        
        # Assign target letter for correct answer (cycle through A,B,C,D)
        target_correct = target_distribution[i % 4]
        
        # Remove correct answer from options
        options.remove(correct_text)
        random.shuffle(options)
        
        # Place correct answer at target position
        target_idx = ord(target_correct) - ord('A')
        options.insert(target_idx, correct_text)
        
        new_q = {
            'question_text': q['question_text'],
            'option_a': options[0],
            'option_b': options[1],
            'option_c': options[2],
            'option_d': options[3],
            'correct_option': target_correct
        }
        shuffled.append(new_q)
    
    return shuffled


def format_questions_to_python(questions, var_name):
    """Format questions list as Python source code."""
    lines = [f"{var_name} = ["]
    for q in questions:
        # Escape backslashes, quotes, and newlines in text
        qt = q['question_text'].replace('\\', '\\\\').replace('"', '\\"').replace('\n', '\\n')
        oa = q['option_a'].replace('\\', '\\\\').replace('"', '\\"').replace('\n', '\\n')
        ob = q['option_b'].replace('\\', '\\\\').replace('"', '\\"').replace('\n', '\\n')
        oc = q['option_c'].replace('\\', '\\\\').replace('"', '\\"').replace('\n', '\\n')
        od = q['option_d'].replace('\\', '\\\\').replace('"', '\\"').replace('\n', '\\n')
        co = q['correct_option']
        
        line = f'    {{"question_text": "{qt}", "option_a": "{oa}", "option_b": "{ob}", "option_c": "{oc}", "option_d": "{od}", "correct_option": "{co}"}},'
        lines.append(line)
    lines.append("]")
    return "\n".join(lines)


if __name__ == "__main__":
    from java_questions import JAVA_QUESTIONS
    from python_questions import PYTHON_QUESTIONS
    from nodejs_questions import NODEJS_QUESTIONS
    from angular_questions import ANGULAR_QUESTIONS
    from ba_questions import BA_QUESTIONS
    
    random.seed(42)  # For reproducibility
    
    all_sets = [
        ("JAVA_QUESTIONS", JAVA_QUESTIONS, "java_questions.py"),
        ("PYTHON_QUESTIONS", PYTHON_QUESTIONS, "python_questions.py"),
        ("NODEJS_QUESTIONS", NODEJS_QUESTIONS, "nodejs_questions.py"),
        ("ANGULAR_QUESTIONS", ANGULAR_QUESTIONS, "angular_questions.py"),
        ("BA_QUESTIONS", BA_QUESTIONS, "ba_questions.py"),
    ]
    
    for var_name, questions, filename in all_sets:
        shuffled = shuffle_question_options(questions)
        
        # Count distribution
        dist = {'A': 0, 'B': 0, 'C': 0, 'D': 0}
        for q in shuffled:
            dist[q['correct_option']] += 1
        
        print(f"{filename}: {len(shuffled)} questions - A:{dist['A']} B:{dist['B']} C:{dist['C']} D:{dist['D']}")
        
        # Write back
        filepath = os.path.join(os.path.dirname(os.path.abspath(__file__)), filename)
        content = format_questions_to_python(shuffled, var_name) + "\n"
        with open(filepath, 'w') as f:
            f.write(content)
        
    print("\nAll question files have been rewritten with balanced answer distribution!")
