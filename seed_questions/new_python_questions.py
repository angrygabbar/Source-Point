NEW_PYTHON_QUESTIONS = [
    # Q1 - correct: A
    {"question_text": "What is the output?\n\nx = [1, 2, 3]\ny = x\ny.append(4)\nprint(len(x))", "option_a": "4", "option_b": "3", "option_c": "TypeError", "option_d": "None", "correct_option": "A"},
    # Q2 - correct: B
    {"question_text": "What is the output?\n\nprint(type(lambda: None))", "option_a": "<class 'NoneType'>", "option_b": "<class 'function'>", "option_c": "<class 'lambda'>", "option_d": "SyntaxError", "correct_option": "B"},
    # Q3 - correct: C
    {"question_text": "What is the output?\n\na = {1, 2, 3}\nb = {2, 3, 4}\nprint(a ^ b)", "option_a": "{2, 3}", "option_b": "{1, 2, 3, 4}", "option_c": "{1, 4}", "option_d": "TypeError", "correct_option": "C"},
    # Q4 - correct: D
    {"question_text": "What is the output?\n\ntry:\n    x = 1 / 0\nexcept ZeroDivisionError:\n    print('A', end=' ')\nfinally:\n    print('B', end=' ')", "option_a": "A", "option_b": "B", "option_c": "Error", "option_d": "A B", "correct_option": "D"},
    # Q5 - correct: A
    {"question_text": "What is the output?\n\ndef func(a, b=[], c=None):\n    b.append(a)\n    return b\nprint(func(1))\nprint(func(2))", "option_a": "[1] then [1, 2] (mutable default argument trap)", "option_b": "[1] then [2]", "option_c": "[1] then TypeError", "option_d": "SyntaxError", "correct_option": "A"},
    # Q6 - correct: B
    {"question_text": "What is the output?\n\nimport copy\na = [[1, 2], [3, 4]]\nb = copy.copy(a)\nb[0].append(5)\nprint(a[0])", "option_a": "[1, 2]", "option_b": "[1, 2, 5]", "option_c": "[[1, 2, 5], [3, 4]]", "option_d": "TypeError", "correct_option": "B"},
    # Q7 - correct: C
    {"question_text": "Which Python data structure is ordered, immutable, and allows duplicates?", "option_a": "Set", "option_b": "Dictionary", "option_c": "Tuple", "option_d": "FrozenSet", "correct_option": "C"},
    # Q8 - correct: D
    {"question_text": "What is the output?\n\nclass A:\n    x = 10\n\nclass B(A):\n    pass\n\nB.x = 20\nprint(A.x)", "option_a": "20", "option_b": "None", "option_c": "AttributeError", "option_d": "10", "correct_option": "D"},
    # Q9 - correct: A
    {"question_text": "What is the output?\n\nprint(''.join(reversed('Python')))", "option_a": "nohtyP", "option_b": "Python", "option_c": "TypeError", "option_d": "['n','o','h','t','y','P']", "correct_option": "A"},
    # Q10 - correct: B
    {"question_text": "What does the walrus operator (:=) do in Python 3.8+?", "option_a": "Compares two values like ==", "option_b": "Assigns a value to a variable as part of an expression", "option_c": "Creates a generator expression", "option_d": "Defines a lambda function", "correct_option": "B"},
    # Q11 - correct: C
    {"question_text": "What is the output?\n\nprint(bool(''), bool(' '), bool(0), bool([]))", "option_a": "True True True True", "option_b": "False False False False", "option_c": "False True False False", "option_d": "False False True False", "correct_option": "C"},
    # Q12 - correct: D
    {"question_text": "What is the output?\n\nx = [i**2 for i in range(5) if i % 2 != 0]\nprint(x)", "option_a": "[0, 4, 16]", "option_b": "[1, 4, 9, 16]", "option_c": "[0, 1, 4, 9, 16]", "option_d": "[1, 9]", "correct_option": "D"},
    # Q13 - correct: A
    {"question_text": "What is the output?\n\nfrom collections import Counter\nprint(Counter('abracadabra').most_common(2))", "option_a": "[('a', 5), ('b', 2)]", "option_b": "[('a', 5), ('r', 2)]", "option_c": "{'a': 5, 'b': 2}", "option_d": "Counter({'a': 5, 'b': 2})", "correct_option": "A"},
    # Q14 - correct: B
    {"question_text": "What is the output?\n\ndef gen():\n    yield 1\n    yield 2\n    yield 3\n\ng = gen()\nprint(next(g), next(g))", "option_a": "1 1", "option_b": "1 2", "option_c": "(1, 2, 3)", "option_d": "StopIteration", "correct_option": "B"},
    # Q15 - correct: C
    {"question_text": "Which decorator makes a method accessible without creating an instance?", "option_a": "@classmethod", "option_b": "@property", "option_c": "@staticmethod", "option_d": "@abstractmethod", "correct_option": "C"},
    # Q16 - correct: D
    {"question_text": "What is the output?\n\ndef outer():\n    x = 'outer'\n    def inner():\n        nonlocal x\n        x = 'inner'\n    inner()\n    print(x)\nouter()", "option_a": "outer", "option_b": "None", "option_c": "UnboundLocalError", "option_d": "inner", "correct_option": "D"},
    # Q17 - correct: A
    {"question_text": "What is the output?\n\nprint({True: 'yes', 1: 'one', 1.0: 'float'})", "option_a": "{True: 'float'}", "option_b": "{True: 'yes', 1: 'one', 1.0: 'float'}", "option_c": "{1: 'one'}", "option_d": "TypeError", "correct_option": "A"},
    # Q18 - correct: B
    {"question_text": "What is the output?\n\nprint(all([True, True, False]))\nprint(any([False, False, True]))", "option_a": "True True", "option_b": "False True", "option_c": "True False", "option_d": "False False", "correct_option": "B"},
    # Q19 - correct: C
    {"question_text": "In Python, what does __slots__ do in a class?", "option_a": "Creates class constants", "option_b": "Defines abstract methods", "option_c": "Restricts allowed attributes and saves memory by avoiding __dict__", "option_d": "Makes the class immutable", "correct_option": "C"},
    # Q20 - correct: D
    {"question_text": "What is the output?\n\nprint(0.1 + 0.2 == 0.3)\nfrom math import isclose\nprint(isclose(0.1 + 0.2, 0.3))", "option_a": "True True", "option_b": "True False", "option_c": "False False", "option_d": "False True", "correct_option": "D"},
]
