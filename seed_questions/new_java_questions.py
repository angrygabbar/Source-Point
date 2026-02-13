NEW_JAVA_QUESTIONS = [
    # Q1 - correct: A
    {"question_text": "What is the output?\n\nString s = \"Java\";\ns.concat(\" Rocks\");\nSystem.out.println(s);", "option_a": "Java", "option_b": "Java Rocks", "option_c": "Compilation error", "option_d": "null", "correct_option": "A"},
    # Q2 - correct: B
    {"question_text": "Which collection maintains insertion order and allows duplicates?", "option_a": "HashSet", "option_b": "ArrayList", "option_c": "TreeSet", "option_d": "HashMap", "correct_option": "B"},
    # Q3 - correct: C
    {"question_text": "What is the output?\n\nint a = 10;\nint b = a++ + ++a;\nSystem.out.println(b);", "option_a": "20", "option_b": "21", "option_c": "22", "option_d": "Compilation error", "correct_option": "C"},
    # Q4 - correct: D
    {"question_text": "Which method in Thread class is used to start a thread but is NOT recommended to call directly?", "option_a": "start()", "option_b": "join()", "option_c": "sleep()", "option_d": "run()", "correct_option": "D"},
    # Q5 - correct: A
    {"question_text": "What happens if you put a return statement in a finally block?", "option_a": "It overrides the return value from try/catch blocks", "option_b": "It causes a compilation error", "option_c": "The finally block is skipped", "option_d": "It throws a RuntimeException", "correct_option": "A"},
    # Q6 - correct: B
    {"question_text": "What is the output?\n\nSystem.out.println(\"A\" + \"B\" + 1 + 2);\nSystem.out.println(1 + 2 + \"A\" + \"B\");", "option_a": "AB3 and 3AB", "option_b": "AB12 and 3AB", "option_c": "AB12 and 12AB", "option_d": "AB3 and 12AB", "correct_option": "B"},
    # Q7 - correct: C
    {"question_text": "Which access modifier allows access only within the same package and subclasses in other packages?", "option_a": "private", "option_b": "default (package-private)", "option_c": "protected", "option_d": "public", "correct_option": "C"},
    # Q8 - correct: D
    {"question_text": "What is the output?\n\nInteger x = null;\nint y = x;\nSystem.out.println(y);", "option_a": "0", "option_b": "null", "option_c": "Compilation error", "option_d": "NullPointerException (auto-unboxing null)", "correct_option": "D"},
    # Q9 - correct: A
    {"question_text": "What is the output?\n\nMap<String, String> map = new LinkedHashMap<>();\nmap.put(\"c\", \"3\");\nmap.put(\"a\", \"1\");\nmap.put(\"b\", \"2\");\nSystem.out.println(map.keySet());", "option_a": "[c, a, b]", "option_b": "[a, b, c]", "option_c": "[a, c, b]", "option_d": "Undefined order", "correct_option": "A"},
    # Q10 - correct: B
    {"question_text": "What is the output?\n\nString s1 = \"Hello\" + \" World\";\nString s2 = \"Hello World\";\nSystem.out.println(s1 == s2);", "option_a": "false", "option_b": "true (compile-time constant folding)", "option_c": "Depends on JVM", "option_d": "Compilation error", "correct_option": "B"},
    # Q11 - correct: C
    {"question_text": "Which of the following is NOT a valid state of a Java thread?", "option_a": "BLOCKED", "option_b": "WAITING", "option_c": "STOPPED", "option_d": "TIMED_WAITING", "correct_option": "C"},
    # Q12 - correct: D
    {"question_text": "What is the output?\n\nList<String> list = Arrays.asList(\"X\", \"Y\", \"Z\");\nCollections.reverse(list);\nSystem.out.println(list);", "option_a": "[X, Y, Z]", "option_b": "UnsupportedOperationException", "option_c": "Compilation error", "option_d": "[Z, Y, X]", "correct_option": "D"},
    # Q13 - correct: A
    {"question_text": "What is the difference between abstract class and interface in Java 8+?", "option_a": "Abstract class can have constructors and instance state; interface cannot have constructors", "option_b": "Interfaces can have constructors in Java 8+", "option_c": "Abstract classes cannot have abstract methods", "option_d": "There is no difference since Java 8", "correct_option": "A"},
    # Q14 - correct: B
    {"question_text": "What is the output?\n\nbyte b = 127;\nb++;\nSystem.out.println(b);", "option_a": "128", "option_b": "-128", "option_c": "Compilation error", "option_d": "ArithmeticException", "correct_option": "B"},
    # Q15 - correct: C
    {"question_text": "What is the output?\n\nString[] arr = {\"one\", \"two\", \"three\"};\nList<String> list = Arrays.asList(arr);\narr[0] = \"ONE\";\nSystem.out.println(list.get(0));", "option_a": "one", "option_b": "Compilation error", "option_c": "ONE", "option_d": "null", "correct_option": "C"},
    # Q16 - correct: D
    {"question_text": "In Java, which method must be overridden if you override equals()?", "option_a": "toString()", "option_b": "compareTo()", "option_c": "clone()", "option_d": "hashCode()", "correct_option": "D"},
    # Q17 - correct: A
    {"question_text": "What is the output?\n\nAtomicInteger ai = new AtomicInteger(5);\nint old = ai.getAndAdd(3);\nSystem.out.println(old + \" \" + ai.get());", "option_a": "5 8", "option_b": "8 8", "option_c": "5 5", "option_d": "3 8", "correct_option": "A"},
    # Q18 - correct: B
    {"question_text": "Which statement about Java sealed classes (Java 17) is TRUE?", "option_a": "Sealed classes cannot have any subclasses", "option_b": "Sealed classes restrict which classes can extend them using permits", "option_c": "Sealed classes must be abstract", "option_d": "Sealed classes cannot implement interfaces", "correct_option": "B"},
    # Q19 - correct: C
    {"question_text": "What is the output?\n\nPredicate<Integer> isEven = n -> n % 2 == 0;\nPredicate<Integer> isPositive = n -> n > 0;\nSystem.out.println(isEven.and(isPositive).test(-4));", "option_a": "true", "option_b": "Compilation error", "option_c": "false", "option_d": "NullPointerException", "correct_option": "C"},
    # Q20 - correct: D
    {"question_text": "What annotation marks a method that should run before each test method in JUnit 5?", "option_a": "@Before", "option_b": "@BeforeAll", "option_c": "@Setup", "option_d": "@BeforeEach", "correct_option": "D"},
]
