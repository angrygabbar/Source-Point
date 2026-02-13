NEW_NODEJS_QUESTIONS = [
    # Q1 - correct: A
    {"question_text": "What is the output?\n\nconsole.log(typeof null);", "option_a": "object", "option_b": "null", "option_c": "undefined", "option_d": "NullType", "correct_option": "A"},
    # Q2 - correct: B
    {"question_text": "What is the output?\n\nconst arr = [1, 2, 3];\narr.push(4);\nconsole.log(arr.length);", "option_a": "3", "option_b": "4", "option_c": "TypeError (const)", "option_d": "undefined", "correct_option": "B"},
    # Q3 - correct: C
    {"question_text": "Which method converts a JavaScript object to a JSON string?", "option_a": "JSON.parse()", "option_b": "Object.toString()", "option_c": "JSON.stringify()", "option_d": "String(object)", "correct_option": "C"},
    # Q4 - correct: D
    {"question_text": "What is the output?\n\nconsole.log([] == false);\nconsole.log([] === false);", "option_a": "false false", "option_b": "true true", "option_c": "false true", "option_d": "true false", "correct_option": "D"},
    # Q5 - correct: A
    {"question_text": "What is the output?\n\nconst obj = { a: 1, b: 2, a: 3 };\nconsole.log(obj.a);", "option_a": "3", "option_b": "1", "option_c": "SyntaxError", "option_d": "undefined", "correct_option": "A"},
    # Q6 - correct: B
    {"question_text": "In Node.js, which module is used to create an HTTP server?", "option_a": "fs", "option_b": "http", "option_c": "url", "option_d": "net", "correct_option": "B"},
    # Q7 - correct: C
    {"question_text": "What is the output?\n\nlet x = 1;\n{\n    let x = 2;\n}\nconsole.log(x);", "option_a": "2", "option_b": "undefined", "option_c": "1", "option_d": "ReferenceError", "correct_option": "C"},
    # Q8 - correct: D
    {"question_text": "What is the output?\n\nPromise.resolve(1)\n    .then(x => x + 1)\n    .then(x => { throw new Error('oops') })\n    .catch(e => 3)\n    .then(x => console.log(x));", "option_a": "1", "option_b": "2", "option_c": "Error: oops", "option_d": "3", "correct_option": "D"},
    # Q9 - correct: A
    {"question_text": "What is the output?\n\nconsole.log('5' - 3);\nconsole.log('5' + 3);", "option_a": "2 and 53", "option_b": "53 and 53", "option_c": "2 and 8", "option_d": "NaN and 53", "correct_option": "A"},
    # Q10 - correct: B
    {"question_text": "What is the purpose of the Node.js 'cluster' module?", "option_a": "To manage database connections", "option_b": "To create child processes that share the same server port for load balancing", "option_c": "To manage file system clusters", "option_d": "To handle WebSocket connections", "correct_option": "B"},
    # Q11 - correct: C
    {"question_text": "What is the output?\n\nconst set = new Set([1, 2, 2, 3, 3, 3]);\nconsole.log(set.size);", "option_a": "6", "option_b": "1", "option_c": "3", "option_d": "TypeError", "correct_option": "C"},
    # Q12 - correct: D
    {"question_text": "What is the output?\n\nasync function foo() {\n    return 'hello';\n}\nconsole.log(typeof foo());", "option_a": "string", "option_b": "undefined", "option_c": "function", "option_d": "object (Promise)", "correct_option": "D"},
    # Q13 - correct: A
    {"question_text": "What is the output?\n\nconst map = new Map();\nmap.set({}, 'a');\nmap.set({}, 'b');\nconsole.log(map.size);", "option_a": "2 (different object references)", "option_b": "1 (same structure)", "option_c": "TypeError", "option_d": "0", "correct_option": "A"},
    # Q14 - correct: B
    {"question_text": "In Express.js, what is middleware?", "option_a": "A database driver", "option_b": "A function that has access to req, res, and next in the request-response cycle", "option_c": "A template engine", "option_d": "A routing protocol", "correct_option": "B"},
    # Q15 - correct: C
    {"question_text": "What is the output?\n\nconst [a, , b] = [1, 2, 3, 4];\nconsole.log(a, b);", "option_a": "1 2", "option_b": "1 4", "option_c": "1 3", "option_d": "1 undefined", "correct_option": "C"},
    # Q16 - correct: D
    {"question_text": "What does 'process.nextTick()' do in Node.js?", "option_a": "Runs the callback after the next event loop iteration", "option_b": "Runs the callback synchronously", "option_c": "Runs the callback after all I/O events", "option_d": "Runs the callback before any additional I/O in the current iteration", "correct_option": "D"},
    # Q17 - correct: A
    {"question_text": "What is the output?\n\nconsole.log(Number.isNaN('hello'));\nconsole.log(isNaN('hello'));", "option_a": "false true", "option_b": "true true", "option_c": "false false", "option_d": "true false", "correct_option": "A"},
    # Q18 - correct: B
    {"question_text": "What is the output?\n\nconst obj = Object.freeze({ a: 1, b: { c: 2 } });\nobj.b.c = 99;\nconsole.log(obj.b.c);", "option_a": "2 (freeze is deep)", "option_b": "99 (freeze is shallow, nested objects are mutable)", "option_c": "TypeError", "option_d": "undefined", "correct_option": "B"},
    # Q19 - correct: C
    {"question_text": "Which HTTP status code means 'Created'?", "option_a": "200", "option_b": "204", "option_c": "201", "option_d": "202", "correct_option": "C"},
    # Q20 - correct: D
    {"question_text": "What is the output?\n\nconst sym1 = Symbol('foo');\nconst sym2 = Symbol('foo');\nconsole.log(sym1 === sym2);", "option_a": "true", "option_b": "TypeError", "option_c": "null", "option_d": "false", "correct_option": "D"},
]
