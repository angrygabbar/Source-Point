NEW_ANGULAR_QUESTIONS = [
    # Q1 - correct: A
    {"question_text": "What is the purpose of Angular's 'trackBy' function in *ngFor?", "option_a": "Improves rendering performance by tracking items by a unique identifier instead of object reference", "option_b": "Tracks user interactions with list items", "option_c": "Enables two-way binding on list items", "option_d": "Adds analytics tracking to list items", "correct_option": "A"},
    # Q2 - correct: B
    {"question_text": "What is the output of {{ 'Angular' | slice:0:3 }} in an Angular template?", "option_a": "Angular", "option_b": "Ang", "option_c": "lar", "option_d": "Angu", "correct_option": "B"},
    # Q3 - correct: C
    {"question_text": "Which lifecycle hook is called after Angular has fully initialized a component's view?", "option_a": "ngOnInit", "option_b": "ngOnChanges", "option_c": "ngAfterViewInit", "option_d": "ngDoCheck", "correct_option": "C"},
    # Q4 - correct: D
    {"question_text": "What does the 'async' pipe do in Angular?", "option_a": "Makes HTTP requests asynchronous", "option_b": "Converts synchronous operations to async", "option_c": "Delays template rendering", "option_d": "Subscribes to an Observable/Promise and returns the latest emitted value", "correct_option": "D"},
    # Q5 - correct: A
    {"question_text": "Which Angular decorator is used to listen for host element events?", "option_a": "@HostListener", "option_b": "@EventListener", "option_c": "@OnEvent", "option_d": "@HostBinding", "correct_option": "A"},
    # Q6 - correct: B
    {"question_text": "What is the difference between 'declarations' and 'imports' in an NgModule?", "option_a": "declarations is for services, imports is for components", "option_b": "declarations is for components/directives/pipes, imports is for other modules", "option_c": "declarations is for modules, imports is for components", "option_d": "They are interchangeable", "correct_option": "B"},
    # Q7 - correct: C
    {"question_text": "In Angular reactive forms, which class represents a single input element?", "option_a": "FormGroup", "option_b": "FormArray", "option_c": "FormControl", "option_d": "FormBuilder", "correct_option": "C"},
    # Q8 - correct: D
    {"question_text": "What does Angular's 'providedIn: root' do for a service?", "option_a": "Makes the service available only in the root component", "option_b": "Creates a new instance for each component", "option_c": "Makes the service lazy-loaded", "option_d": "Registers the service as a singleton available application-wide", "correct_option": "D"},
    # Q9 - correct: A
    {"question_text": "What is the purpose of Angular's ChangeDetectionStrategy.OnPush?", "option_a": "Only runs change detection when @Input references change or events occur in the component", "option_b": "Disables change detection entirely", "option_c": "Runs change detection on every browser event", "option_d": "Manually triggers change detection on each push", "correct_option": "A"},
    # Q10 - correct: B
    {"question_text": "In Angular, what is a resolver?", "option_a": "A service that handles HTTP errors", "option_b": "A service that pre-fetches data before a route is activated", "option_c": "A component that resolves dependencies", "option_d": "A pipe that resolves template expressions", "correct_option": "B"},
    # Q11 - correct: C
    {"question_text": "Which RxJS operator transforms each emitted value and flattens the result, cancelling previous inner subscriptions?", "option_a": "mergeMap", "option_b": "concatMap", "option_c": "switchMap", "option_d": "exhaustMap", "correct_option": "C"},
    # Q12 - correct: D
    {"question_text": "What is the purpose of Angular's ng-content?", "option_a": "Dynamically creates components", "option_b": "Renders conditionally based on content", "option_c": "Replaces component templates", "option_d": "Enables content projection (transclusion) from parent to child component", "correct_option": "D"},
    # Q13 - correct: A
    {"question_text": "What is the output if ViewEncapsulation.None is used on a component?", "option_a": "Component styles become global and affect the entire application", "option_b": "Component styles are completely removed", "option_c": "Component styles are scoped using Shadow DOM", "option_d": "Component styles only apply to child components", "correct_option": "A"},
    # Q14 - correct: B
    {"question_text": "In Angular, what is the purpose of the 'forRoot()' pattern?", "option_a": "To lazy-load root modules", "option_b": "To ensure a module's providers are registered only once as singletons", "option_c": "To define the root component", "option_d": "To configure root-level routes only", "correct_option": "B"},
    # Q15 - correct: C
    {"question_text": "What is Angular Universal used for?", "option_a": "Cross-platform mobile development", "option_b": "Internationalization (i18n)", "option_c": "Server-side rendering (SSR) of Angular applications", "option_d": "Universal component styling", "correct_option": "C"},
    # Q16 - correct: D
    {"question_text": "Which Angular testing utility is used to create a test host for a component?", "option_a": "TestHost", "option_b": "ComponentFixture", "option_c": "MockComponent", "option_d": "TestBed", "correct_option": "D"},
    # Q17 - correct: A
    {"question_text": "What is the difference between Subject and BehaviorSubject in RxJS?", "option_a": "BehaviorSubject requires an initial value and emits the current value to new subscribers", "option_b": "Subject always emits the last value to new subscribers", "option_c": "BehaviorSubject can only emit once", "option_d": "They are identical in functionality", "correct_option": "A"},
    # Q18 - correct: B
    {"question_text": "How do you access a child component's methods from a parent in Angular?", "option_a": "@Input decorator", "option_b": "@ViewChild decorator", "option_c": "@Output decorator", "option_d": "@HostBinding decorator", "correct_option": "B"},
    # Q19 - correct: C
    {"question_text": "What does the Angular 'canActivate' guard return?", "option_a": "Only a boolean", "option_b": "Only an Observable", "option_c": "A boolean, Promise<boolean>, or Observable<boolean>", "option_d": "A redirect URL only", "correct_option": "C"},
    # Q20 - correct: D
    {"question_text": "In Angular signals (v16+), what does the 'computed()' function do?", "option_a": "Creates a writable signal", "option_b": "Creates an HTTP request", "option_c": "Creates a mutable state", "option_d": "Creates a read-only signal derived from other signals that updates automatically", "correct_option": "D"},
]
