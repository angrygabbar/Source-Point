import {
  BarChart3,
  Bell,
  BookOpen,
  Boxes,
  Briefcase,
  Building2,
  CalendarClock,
  CalendarDays,
  ClipboardCheck,
  ClipboardList,
  CreditCard,
  FileSpreadsheet,
  FileText,
  FolderOpen,
  GraduationCap,
  HandCoins,
  Home,
  Landmark,
  Library,
  ListChecks,
  type LucideIcon,
  Megaphone,
  MessageSquare,
  MessagesSquare,
  Receipt,
  School,
  ScrollText,
  Search,
  Settings,
  ShieldCheck,
  UserCog,
  UserPlus,
  Users,
  Video,
  Wallet,
} from "lucide-react";

export interface NavItem {
  label: string;
  href: string;
  icon: LucideIcon;
  module?: string; // permission module (read or read_own)
  perms?: string[]; // any of
  feature?: string;
  portals?: string[];
}

export interface NavGroup {
  label: string;
  items: NavItem[];
}

const ALL = ["admin", "teacher", "student", "parent"];

export const NAV: NavGroup[] = [
  {
    label: "Overview",
    items: [
      { label: "Dashboard", href: "/dashboard", icon: Home, portals: ALL },
      { label: "Search", href: "/search", icon: Search, portals: ["admin", "teacher"] },
      { label: "Timetable", href: "/timetable", icon: CalendarDays, module: "sessions" },
    ],
  },
  {
    label: "People",
    items: [
      { label: "Students", href: "/r/students", icon: GraduationCap, module: "students", portals: ["admin", "teacher"] },
      { label: "Teachers", href: "/r/teachers", icon: Briefcase, module: "teachers", portals: ["admin"] },
      { label: "Parents", href: "/r/parents", icon: Users, module: "parents", portals: ["admin", "teacher"], feature: "parent_portal" },
      { label: "Enrollments", href: "/r/enrollments", icon: ClipboardList, module: "enrollments", portals: ["admin"] },
      { label: "Counselling", href: "/r/counselling-records", icon: ShieldCheck, module: "counselling", portals: ["admin"] },
    ],
  },
  {
    label: "Academics",
    items: [
      { label: "Courses", href: "/r/courses", icon: School, module: "courses", portals: ["admin"] },
      { label: "Subjects", href: "/r/subjects", icon: BookOpen, module: "subjects", portals: ["admin"] },
      { label: "Batches", href: "/r/batches", icon: Boxes, module: "batches", portals: ["admin", "teacher"] },
      { label: "Teacher assignments", href: "/r/teacher-assignments", icon: UserCog, module: "teacher_assignments", portals: ["admin"] },
      { label: "Academic years", href: "/r/academic-years", icon: CalendarClock, module: "academic_years", portals: ["admin"] },
      { label: "Classrooms", href: "/r/classrooms", icon: Building2, module: "classrooms", portals: ["admin"] },
      { label: "Syllabus", href: "/syllabus", icon: ListChecks, module: "syllabus", portals: ["admin", "teacher"] },
      { label: "Lesson plans", href: "/r/lesson-plans", icon: ScrollText, module: "lesson_plans", portals: ["admin", "teacher"] },
    ],
  },
  {
    label: "Class operations",
    items: [
      { label: "Class sessions", href: "/r/class-sessions", icon: CalendarClock, module: "sessions", portals: ["admin", "teacher"] },
      { label: "Schedules", href: "/r/schedules", icon: CalendarDays, module: "schedules", portals: ["admin"] },
      { label: "Holidays", href: "/r/holidays", icon: CalendarDays, module: "schedules", portals: ["admin"] },
      { label: "Attendance corrections", href: "/r/attendance-corrections", icon: ClipboardCheck, module: "attendance", feature: "attendance", portals: ["admin", "teacher"] },
      { label: "Teacher attendance", href: "/r/teacher-attendance", icon: ClipboardCheck, module: "teacher_attendance", feature: "attendance", portals: ["admin"] },
    ],
  },
  {
    label: "Learning",
    items: [
      { label: "Study materials", href: "/materials", icon: FolderOpen, module: "materials", feature: "materials", portals: ["admin", "teacher", "student"] },
      { label: "Homework", href: "/r/assignments", icon: FileText, module: "assignments", feature: "homework" },
      { label: "Examinations", href: "/r/examinations", icon: ClipboardList, module: "exams", feature: "examinations" },
      { label: "Question bank", href: "/r/questions", icon: BookOpen, module: "questions", feature: "examinations", portals: ["admin", "teacher"] },
      { label: "Results", href: "/r/exam-results", icon: BarChart3, module: "results", feature: "examinations" },
      { label: "Online learning", href: "/lms", icon: Video, module: "lms", feature: "lms", portals: ["admin", "teacher", "student"] },
      { label: "Discussions", href: "/discussions", icon: MessagesSquare, module: "discussions", feature: "lms", portals: ["admin", "teacher", "student"] },
      { label: "Online meetings", href: "/r/online-meetings", icon: Video, module: "lms", feature: "lms", portals: ["admin", "teacher"] },
    ],
  },
  {
    label: "Admissions",
    items: [
      { label: "Pipeline", href: "/admissions", icon: UserPlus, module: "admissions", feature: "admissions", portals: ["admin"] },
      { label: "Leads", href: "/r/leads", icon: Users, module: "admissions", feature: "admissions", portals: ["admin"] },
      { label: "Follow-ups", href: "/r/follow-ups", icon: CalendarClock, module: "admissions", feature: "admissions", portals: ["admin"] },
      { label: "Demo classes", href: "/r/demo-classes", icon: School, module: "admissions", feature: "admissions", portals: ["admin"] },
      { label: "Campaigns", href: "/r/campaigns", icon: Megaphone, module: "admissions", feature: "admissions", portals: ["admin"] },
    ],
  },
  {
    label: "Fees & billing",
    items: [
      { label: "Collect payment", href: "/finance/collect", icon: HandCoins, perms: ["payments.write"], feature: "billing", portals: ["admin"] },
      { label: "Invoices", href: "/r/invoices", icon: Receipt, module: "invoices", feature: "billing", portals: ["admin", "student", "parent"] },
      { label: "Payments", href: "/r/payments", icon: CreditCard, module: "payments", feature: "billing", portals: ["admin", "student", "parent"] },
      { label: "Billing runs", href: "/finance/billing", icon: FileSpreadsheet, perms: ["invoices.write"], feature: "billing", portals: ["admin"] },
      { label: "Fee plans", href: "/r/fee-plans", icon: Wallet, module: "fees", feature: "billing", portals: ["admin"] },
      { label: "Fee agreements", href: "/r/fee-agreements", icon: ScrollText, module: "fees", feature: "billing", portals: ["admin"] },
      { label: "Refunds", href: "/r/refunds", icon: Receipt, module: "refunds", feature: "billing", portals: ["admin"] },
      { label: "Credit notes", href: "/r/credit-notes", icon: Receipt, module: "refunds", feature: "billing", portals: ["admin"] },
    ],
  },
  {
    label: "Accounting",
    items: [
      { label: "Expenses", href: "/r/expenses", icon: Wallet, module: "expenses", feature: "accounting", portals: ["admin"] },
      { label: "Vendors", href: "/r/vendors", icon: Building2, module: "vendors", feature: "accounting", portals: ["admin"] },
      { label: "Purchases", href: "/r/purchase-records", icon: Boxes, module: "vendors", feature: "accounting", portals: ["admin"] },
      { label: "Cashbook", href: "/accounting/cashbook", icon: Landmark, module: "accounting", feature: "accounting", portals: ["admin"] },
      { label: "Bank register", href: "/r/bank-transactions", icon: Landmark, module: "accounting", feature: "accounting", portals: ["admin"] },
      { label: "Budgets", href: "/r/budgets", icon: BarChart3, module: "accounting", feature: "accounting", portals: ["admin"] },
      { label: "Financial years", href: "/r/financial-years", icon: CalendarDays, module: "accounting", feature: "accounting", portals: ["admin"] },
    ],
  },
  {
    label: "HR & payroll",
    items: [
      { label: "Leave", href: "/r/teacher-leaves", icon: CalendarClock, module: "leaves", feature: "hr_payroll", portals: ["admin", "teacher"] },
      { label: "Payroll", href: "/payroll", icon: HandCoins, module: "payroll", feature: "teacher_compensation", portals: ["admin"] },
      { label: "Payslips", href: "/r/payslips", icon: Receipt, module: "payroll", feature: "teacher_compensation", portals: ["teacher"] },
      { label: "Compensation rules", href: "/r/compensation-rules", icon: ScrollText, module: "payroll", feature: "teacher_compensation", portals: ["admin"] },
      { label: "Employment records", href: "/r/employment-records", icon: Briefcase, module: "hr", feature: "hr_payroll", portals: ["admin"] },
      { label: "Performance reviews", href: "/r/performance-reviews", icon: ClipboardCheck, module: "hr", feature: "hr_payroll", portals: ["admin"] },
    ],
  },
  {
    label: "Communication",
    items: [
      { label: "Announcements", href: "/announcements", icon: Megaphone, module: "announcements", feature: "communication" },
      { label: "Messages", href: "/messages", icon: MessageSquare, module: "messages", feature: "communication" },
      { label: "Parent meetings", href: "/r/parent-meetings", icon: Users, module: "meetings", feature: "communication", portals: ["admin", "teacher", "parent"] },
      { label: "Surveys & feedback", href: "/surveys", icon: ClipboardList, module: "surveys", feature: "communication" },
      { label: "Notifications", href: "/notifications", icon: Bell, portals: ALL },
    ],
  },
  {
    label: "Resources",
    items: [
      { label: "Library", href: "/r/books", icon: Library, module: "library", feature: "library", portals: ["admin"] },
      { label: "Book loans", href: "/r/book-loans", icon: Library, module: "library", feature: "library", portals: ["admin"] },
      { label: "Library members", href: "/r/library-members", icon: Users, module: "library", feature: "library", portals: ["admin"] },
      { label: "Inventory", href: "/r/inventory-items", icon: Boxes, module: "inventory", feature: "inventory", portals: ["admin"] },
      { label: "Stock movements", href: "/r/inventory-transactions", icon: Boxes, module: "inventory", feature: "inventory", portals: ["admin"] },
      { label: "Assets", href: "/r/assets", icon: Building2, module: "assets", feature: "inventory", portals: ["admin"] },
    ],
  },
  {
    label: "Insights",
    items: [{ label: "Reports", href: "/reports", icon: BarChart3, perms: ["reports.read", "reports.read_own"], portals: ["admin", "teacher"] }],
  },
  {
    label: "Administration",
    items: [
      { label: "Users & roles", href: "/users", icon: UserCog, perms: ["users.read"], portals: ["admin"] },
      { label: "Settings", href: "/settings", icon: Settings, perms: ["settings.read", "institutes.write", "integrations.read"], portals: ["admin"] },
      { label: "Branches", href: "/r/branches", icon: Building2, module: "branches", feature: "multi_branch", portals: ["admin"] },
      { label: "Import / export", href: "/imports", icon: FileSpreadsheet, perms: ["imports.write"], portals: ["admin"] },
      { label: "Audit log", href: "/r/audit-logs", icon: ShieldCheck, module: "audit", portals: ["admin"] },
    ],
  },
];

/** Where list rows link to, for resources that have dedicated pages. */
export const DETAIL_ROUTES: Record<string, (id: string) => string> = {
  students: (id) => `/students/${id}`,
  teachers: (id) => `/teachers/${id}`,
  "class-sessions": (id) => `/sessions/${id}`,
  assignments: (id) => `/assignments/${id}`,
  examinations: (id) => `/exams/${id}`,
  invoices: (id) => `/finance/invoices/${id}`,
  "discussion-threads": (id) => `/discussions/${id}`,
  surveys: (id) => `/surveys?open=${id}`,
  materials: (id) => `/materials/${id}`,
};

export function detailHref(resource: string, id: string): string {
  return DETAIL_ROUTES[resource]?.(id) ?? `/r/${resource}/${id}`;
}
