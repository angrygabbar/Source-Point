NEW_BA_QUESTIONS = [
    # Q1 - correct: A
    {"question_text": "A stakeholder says 'I want the system to be fast.' How should a Business Analyst handle this requirement?", "option_a": "Quantify it with measurable criteria (e.g., page load < 2 seconds, 99.9% uptime)", "option_b": "Document it as-is since the stakeholder knows best", "option_c": "Ignore it as it's too vague to implement", "option_d": "Forward it directly to the development team", "correct_option": "A"},
    # Q2 - correct: B
    {"question_text": "Which technique is BEST for identifying gaps in requirements between current state and desired future state?", "option_a": "SWOT Analysis", "option_b": "Gap Analysis", "option_c": "Root Cause Analysis", "option_d": "Risk Assessment", "correct_option": "B"},
    # Q3 - correct: C
    {"question_text": "What is the primary difference between a Business Requirement Document (BRD) and a Functional Requirement Document (FRD)?", "option_a": "BRD is written by developers, FRD by BAs", "option_b": "BRD is more detailed than FRD", "option_c": "BRD focuses on business needs; FRD describes how the system fulfills those needs", "option_d": "They are the same document with different names", "correct_option": "C"},
    # Q4 - correct: D
    {"question_text": "In RACI matrix, what does the 'A' stand for?", "option_a": "Approved", "option_b": "Assessed", "option_c": "Authorized", "option_d": "Accountable", "correct_option": "D"},
    # Q5 - correct: A
    {"question_text": "A project has 8 stakeholders. How many potential communication channels exist?", "option_a": "28 [n(n-1)/2]", "option_b": "56", "option_c": "64", "option_d": "16", "correct_option": "A"},
    # Q6 - correct: B
    {"question_text": "Which elicitation technique involves observing users in their actual work environment?", "option_a": "Brainstorming", "option_b": "Job Shadowing / Observation", "option_c": "Survey", "option_d": "Document Analysis", "correct_option": "B"},
    # Q7 - correct: C
    {"question_text": "In Agile, who is the primary author of user stories?", "option_a": "Scrum Master", "option_b": "Development Team", "option_c": "Product Owner", "option_d": "Business Analyst", "correct_option": "C"},
    # Q8 - correct: D
    {"question_text": "What does the acronym INVEST stand for in user story writing?", "option_a": "Independent, Negotiable, Validated, Estimated, Sized, Tracked", "option_b": "Integrated, New, Verified, Estimated, Scoped, Tested", "option_c": "Independent, Necessary, Validated, Estimated, Small, Tracked", "option_d": "Independent, Negotiable, Valuable, Estimable, Small, Testable", "correct_option": "D"},
    # Q9 - correct: A
    {"question_text": "In SQL, which JOIN returns all records from both tables, matching where possible and NULLs where not?", "option_a": "FULL OUTER JOIN", "option_b": "INNER JOIN", "option_c": "LEFT JOIN", "option_d": "CROSS JOIN", "correct_option": "A"},
    # Q10 - correct: B
    {"question_text": "What is the result of this SQL?\n\nSELECT COUNT(*) FROM employees WHERE salary > 50000 AND department = 'IT' OR department = 'HR';", "option_a": "Counts employees in IT with salary > 50000, and all HR employees (AND binds tighter)", "option_b": "Counts IT employees with salary > 50000 PLUS all HR employees (AND has higher precedence than OR)", "option_c": "Counts employees in IT or HR with salary > 50000", "option_d": "Syntax error", "correct_option": "B"},
    # Q11 - correct: C
    {"question_text": "What is the purpose of a traceability matrix in requirements management?", "option_a": "To track project budget", "option_b": "To measure team velocity", "option_c": "To map requirements to their source, test cases, and deliverables for complete coverage", "option_d": "To trace software bugs to their root cause", "correct_option": "C"},
    # Q12 - correct: D
    {"question_text": "In a UML Use Case diagram, what does the 'include' relationship represent?", "option_a": "An optional behavior extension", "option_b": "A generalization of actors", "option_c": "A conditional flow", "option_d": "A mandatory behavior that is always included when the base use case executes", "correct_option": "D"},
    # Q13 - correct: A
    {"question_text": "Which requirements prioritization technique uses Must have, Should have, Could have, Won't have?", "option_a": "MoSCoW", "option_b": "Kano Model", "option_c": "Value vs. Complexity Matrix", "option_d": "Weighted Scoring", "correct_option": "A"},
    # Q14 - correct: B
    {"question_text": "A stakeholder wants a feature that conflicts with another stakeholder's requirement. What should the BA do FIRST?", "option_a": "Choose the requirement from the more senior stakeholder", "option_b": "Facilitate a discussion between stakeholders to find consensus", "option_c": "Remove both conflicting requirements", "option_d": "Escalate to project sponsor immediately", "correct_option": "B"},
    # Q15 - correct: C
    {"question_text": "What is 'scope creep' in project management?", "option_a": "A planned increase in project scope", "option_b": "A reduction in project deliverables", "option_c": "Uncontrolled changes or growth in project scope without adjusting time, cost, or resources", "option_d": "A technique for managing project risks", "correct_option": "C"},
    # Q16 - correct: D
    {"question_text": "In Agile, what is the purpose of a Sprint Retrospective?", "option_a": "To demonstrate completed work to stakeholders", "option_b": "To plan the next sprint's work", "option_c": "To refine the product backlog", "option_d": "To inspect the team's process and identify improvements", "correct_option": "D"},
    # Q17 - correct: A
    {"question_text": "What is the output of this SQL?\n\nSELECT COALESCE(NULL, NULL, 'Hello', 'World');", "option_a": "Hello", "option_b": "World", "option_c": "NULL", "option_d": "Error", "correct_option": "A"},
    # Q18 - correct: B
    {"question_text": "Which diagram is BEST for showing the sequence of interactions between objects over time?", "option_a": "Class Diagram", "option_b": "Sequence Diagram", "option_c": "State Machine Diagram", "option_d": "Component Diagram", "correct_option": "B"},
    # Q19 - correct: C
    {"question_text": "A client says 'We need a report that shows monthly revenue.' What follow-up question is MOST important?", "option_a": "What color should the report be?", "option_b": "Can we use an existing report tool?", "option_c": "Who will access this report, how often, and what decisions will it drive?", "option_d": "Should we build it in Excel?", "correct_option": "C"},
    # Q20 - correct: D
    {"question_text": "What is a 'non-functional requirement'?", "option_a": "A requirement that doesn't work properly", "option_b": "A requirement without a function name", "option_c": "A requirement that can be skipped", "option_d": "A quality attribute like performance, security, scalability, or usability", "correct_option": "D"},
    # Q21 - correct: A
    {"question_text": "In SQL, what is the difference between WHERE and HAVING?", "option_a": "WHERE filters rows before grouping; HAVING filters groups after aggregation", "option_b": "WHERE is for SELECT; HAVING is for INSERT", "option_c": "They are interchangeable", "option_d": "HAVING filters rows before grouping; WHERE filters after", "correct_option": "A"},
    # Q22 - correct: B
    {"question_text": "What is the Kano Model used for in requirements analysis?", "option_a": "Estimating project costs", "option_b": "Categorizing requirements by customer satisfaction (Basic, Performance, Excitement)", "option_c": "Creating database schemas", "option_d": "Measuring team performance", "correct_option": "B"},
    # Q23 - correct: C
    {"question_text": "Which Agile artifact represents an ordered list of everything needed in the product?", "option_a": "Sprint Backlog", "option_b": "Burndown Chart", "option_c": "Product Backlog", "option_d": "Definition of Done", "correct_option": "C"},
    # Q24 - correct: D
    {"question_text": "In a process flow, what does a diamond shape represent?", "option_a": "A process/activity", "option_b": "A data store", "option_c": "A start/end point", "option_d": "A decision point", "correct_option": "D"},
    # Q25 - correct: A
    {"question_text": "What is the result of this SQL?\n\nSELECT department, COUNT(*) as cnt\nFROM employees\nGROUP BY department\nHAVING cnt > 5\nORDER BY cnt DESC;", "option_a": "Departments with more than 5 employees, sorted by count descending", "option_b": "All departments sorted by name", "option_c": "Only the top 5 departments", "option_d": "Syntax error - cannot use alias in HAVING", "correct_option": "A"},
    # Q26 - correct: B
    {"question_text": "What technique is BEST for understanding the root cause of a problem by asking 'Why' repeatedly?", "option_a": "Pareto Analysis", "option_b": "5 Whys Analysis", "option_c": "PESTLE Analysis", "option_d": "Fishbone Diagram", "correct_option": "B"},
    # Q27 - correct: C
    {"question_text": "In the context of data modeling, what is a 'foreign key'?", "option_a": "A unique identifier for each row", "option_b": "An encrypted field for security", "option_c": "A field that references the primary key of another table to establish a relationship", "option_d": "A key from a foreign database", "correct_option": "C"},
    # Q28 - correct: D
    {"question_text": "A user story reads: 'As a customer, I want to sort products by price so that I can find affordable items.' What is this statement lacking?", "option_a": "The user role", "option_b": "The feature description", "option_c": "The story format", "option_d": "Acceptance criteria defining sort behavior (ascending, descending, price ranges, etc.)", "correct_option": "D"},
    # Q29 - correct: A
    {"question_text": "What is the primary purpose of a wireframe?", "option_a": "To show layout structure and user flow without detailed visual design", "option_b": "To finalize color schemes and fonts", "option_c": "To create functional code prototypes", "option_d": "To document database relationships", "correct_option": "A"},
    # Q30 - correct: B
    {"question_text": "In SQL, what does this return?\n\nSELECT DISTINCT department FROM employees ORDER BY department;", "option_a": "All employee records sorted by department", "option_b": "Unique department names in alphabetical order", "option_c": "The count of distinct departments", "option_d": "Syntax error", "correct_option": "B"},
    # Q31 - correct: C
    {"question_text": "What is 'technical debt' in software development?", "option_a": "Money owed to technology vendors", "option_b": "The cost of hardware maintenance", "option_c": "The implied cost of future rework caused by choosing quick solutions over proper ones", "option_d": "Budget allocated for technical training", "correct_option": "C"},
    # Q32 - correct: D
    {"question_text": "Which type of testing validates that the system meets business requirements from the end user's perspective?", "option_a": "Unit Testing", "option_b": "Integration Testing", "option_c": "System Testing", "option_d": "User Acceptance Testing (UAT)", "correct_option": "D"},
    # Q33 - correct: A
    {"question_text": "What is the output of this SQL?\n\nSELECT name FROM employees WHERE name LIKE '_a%';", "option_a": "Names where the second character is 'a' (e.g., Jack, Maria)", "option_b": "Names starting with 'a'", "option_c": "Names ending with 'a'", "option_d": "Names containing 'a' anywhere", "correct_option": "A"},
    # Q34 - correct: B
    {"question_text": "In a Data Flow Diagram (DFD), what does an external entity represent?", "option_a": "A data storage within the system", "option_b": "A source or destination of data outside the system boundary", "option_c": "A process that transforms data", "option_d": "A data flow between processes", "correct_option": "B"},
    # Q35 - correct: C
    {"question_text": "During requirements gathering, two stakeholders have opposite views on a feature's priority. The BA should:", "option_a": "Side with the higher-ranking stakeholder", "option_b": "Remove the feature to avoid conflict", "option_c": "Document both perspectives and use a structured prioritization technique (like MoSCoW) to resolve it", "option_d": "Ask the development team to decide", "correct_option": "C"},
]
