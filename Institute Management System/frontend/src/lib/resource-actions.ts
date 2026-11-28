import type { Row } from "@/types";
import { todayISO } from "@/lib/utils";

export interface PromptField {
  name: string;
  label: string;
  type: "text" | "textarea" | "date" | "datetime" | "number" | "select" | "email" | "ref" | "checkbox";
  options?: string[];
  ref?: string;
  required?: boolean;
  default?: string | number | boolean;
}

export interface ResourceAction {
  label: string;
  kind: "link" | "post" | "pdf" | "signed" | "external";
  path: (row: Row) => string;
  perms?: string[];
  when?: (row: Row) => boolean;
  fields?: PromptField[];
  body?: (row: Row, values: Record<string, unknown>) => unknown;
  confirm?: string;
  danger?: boolean;
  method?: "POST" | "PUT";
}

const s = (r: Row, k: string) => String(r[k] ?? "");
const decision = (path: (r: Row) => string, perm: string, statusKey = "status", remarksKey = "remarks"): ResourceAction[] => [
  { label: "Approve", kind: "post", path, perms: [perm], when: (r) => ["pending", "submitted", "draft"].includes(s(r, "status")), body: () => ({ [statusKey]: "approved" }), confirm: "Approve this request?" },
  {
    label: "Reject", kind: "post", path, perms: [perm], danger: true, when: (r) => ["pending", "submitted", "draft"].includes(s(r, "status")),
    fields: [{ name: remarksKey, label: "Remarks", type: "textarea", required: true }], body: (_r, v) => ({ [statusKey]: "rejected", [remarksKey]: v[remarksKey] }),
  },
];

export const RESOURCE_ACTIONS: Record<string, ResourceAction[]> = {
  students: [
    { label: "ID card", kind: "pdf", path: (r) => `/students/${r.id}/id-card.pdf` },
    { label: "Bonafide certificate", kind: "pdf", path: (r) => `/students/${r.id}/certificate.pdf?kind=bonafide`, perms: ["students.write"] },
    { label: "Create login", kind: "post", path: (r) => `/students/${r.id}/create-login`, perms: ["users.write"], when: (r) => !r.user_id,
      fields: [{ name: "email", label: "Login email", type: "email", required: true }] },
    { label: "Withdraw", kind: "post", path: (r) => `/students/${r.id}/withdraw`, perms: ["students.archive"], danger: true, when: (r) => s(r, "status") === "active",
      fields: [{ name: "withdrawal_date", label: "Withdrawal date", type: "date", required: true, default: todayISO() }, { name: "reason", label: "Reason", type: "textarea", required: true }] },
    { label: "Re-admit", kind: "post", path: (r) => `/students/${r.id}/readmit`, perms: ["students.write"], when: (r) => s(r, "status") !== "active",
      fields: [{ name: "start_date", label: "Re-admission date", type: "date", required: true, default: todayISO() }, { name: "batch_id", label: "Batch (optional)", type: "ref", ref: "batches" }, { name: "reason", label: "Reason", type: "textarea" }] },
  ],
  teachers: [
    { label: "Create login", kind: "post", path: (r) => `/teachers/${r.id}/create-login`, perms: ["users.write"], when: (r) => !r.user_id,
      fields: [{ name: "email", label: "Login email", type: "email", required: true }] },
    { label: "Exit / offboard", kind: "post", path: (r) => `/teachers/${r.id}/exit`, perms: ["hr.write", "teachers.write"], danger: true,
      when: (r) => !["resigned", "terminated"].includes(s(r, "employment_status")),
      fields: [{ name: "exit_date", label: "Exit date", type: "date", required: true, default: todayISO() }, { name: "status", label: "Status", type: "select", options: ["resigned", "terminated"], required: true },
        { name: "reason", label: "Reason", type: "textarea", required: true }] },
  ],
  parents: [
    { label: "Create login", kind: "post", path: (r) => `/parents/${r.id}/create-login`, perms: ["users.write"], when: (r) => !r.user_id,
      fields: [{ name: "email", label: "Login email", type: "email", required: true }] },
  ],
  "webhook-endpoints": [
    { label: "Set signing secret", kind: "post", method: "PUT", path: (r) => `/webhook-endpoints/${r.id}/secret`, perms: ["webhooks.write"],
      fields: [{ name: "secret", label: "Signing secret (min 16 characters)", type: "text", required: true }] },
  ],
  "teacher-leaves": [
    ...decision((r) => `/teacher-leaves/${r.id}/decide`, "leaves.write"),
    { label: "Cancel request", kind: "post", path: (r) => `/teacher-leaves/${r.id}/cancel`, when: (r) => s(r, "status") === "pending", danger: true, confirm: "Cancel this leave request?" },
  ],
  "attendance-corrections": decision((r) => `/attendance/corrections/${r.id}/decide`, "attendance.correct_approve"),
  refunds: [
    { label: "Approve", kind: "post", path: (r) => `/refunds/${r.id}/approve`, perms: ["refunds.approve"], when: (r) => s(r, "status") === "pending", confirm: "Approve this refund?" },
    { label: "Reject", kind: "post", path: (r) => `/refunds/${r.id}/reject`, perms: ["refunds.approve"], danger: true, when: (r) => ["pending", "approved"].includes(s(r, "status")),
      fields: [{ name: "reason", label: "Reason", type: "textarea", required: true }] },
    { label: "Mark processed", kind: "post", path: (r) => `/refunds/${r.id}/process`, perms: ["refunds.approve"], when: (r) => s(r, "status") === "approved",
      fields: [{ name: "reference_number", label: "Transaction reference", type: "text" }] },
  ],
  payments: [
    { label: "Receipt PDF", kind: "pdf", path: (r) => `/payments/${r.id}/receipt.pdf` },
    { label: "Reverse / bounce", kind: "post", path: (r) => `/payments/${r.id}/reverse`, perms: ["payments.reverse"], danger: true, when: (r) => s(r, "status") === "completed",
      fields: [{ name: "reason", label: "Reason", type: "textarea", required: true }, { name: "bounced", label: "Cheque bounced", type: "checkbox" }] },
    { label: "Request refund", kind: "post", path: () => `/refunds`, perms: ["refunds.write"], when: (r) => s(r, "status") === "completed" && Number(r.unallocated_amount) > 0,
      fields: [{ name: "amount", label: "Amount", type: "number", required: true }, { name: "method", label: "Method", type: "select", options: ["bank_transfer", "upi", "cash", "cheque"], required: true },
        { name: "reason", label: "Reason", type: "textarea", required: true }],
      body: (r, v) => ({ payment_id: r.id, ...v }) },
  ],
  invoices: [{ label: "Invoice PDF", kind: "pdf", path: (r) => `/invoices/${r.id}/pdf` }],
  expenses: [
    ...decision((r) => `/expenses/${r.id}/decide`, "expenses.write"),
    { label: "Mark paid", kind: "post", path: (r) => `/expenses/${r.id}/mark-paid`, perms: ["expenses.write"], when: (r) => s(r, "status") === "approved",
      fields: [{ name: "paid_on", label: "Paid on", type: "date", required: true, default: todayISO() },
        { name: "payment_method", label: "Method", type: "select", options: ["cash", "upi", "bank_transfer", "cheque", "card"], required: true },
        { name: "reference_number", label: "Reference", type: "text" }, { name: "bank_account_name", label: "Bank account (non-cash)", type: "text" }] },
  ],
  "purchase-records": [
    { label: "Approve", kind: "post", path: (r) => `/purchase-records/${r.id}/status`, perms: ["vendors.write"], when: (r) => s(r, "status") === "requested", body: () => ({ status: "approved" }) },
    { label: "Reject", kind: "post", path: (r) => `/purchase-records/${r.id}/status`, perms: ["vendors.write"], danger: true, when: (r) => s(r, "status") === "requested",
      fields: [{ name: "remarks", label: "Remarks", type: "textarea", required: true }], body: (_r, v) => ({ status: "rejected", ...v }) },
    { label: "Mark ordered", kind: "post", path: (r) => `/purchase-records/${r.id}/status`, perms: ["vendors.write"], when: (r) => s(r, "status") === "approved", body: () => ({ status: "ordered" }) },
    { label: "Mark received", kind: "post", path: (r) => `/purchase-records/${r.id}/status`, perms: ["vendors.write"], when: (r) => ["approved", "ordered"].includes(s(r, "status")),
      fields: [{ name: "create_expense_category_id", label: "Create expense in category (optional)", type: "ref", ref: "expense-categories" }], body: (_r, v) => ({ status: "received", ...v }) },
  ],
  payslips: [
    { label: "Payslip PDF", kind: "pdf", path: (r) => `/payslips/${r.id}/pdf` },
    { label: "Record payout", kind: "post", path: (r) => `/payslips/${r.id}/pay`, perms: ["payroll.approve"], when: (r) => s(r, "status") === "approved",
      fields: [{ name: "method", label: "Method", type: "select", options: ["bank_transfer", "upi", "cash", "cheque"], required: true }, { name: "reference_number", label: "Reference", type: "text" }] },
  ],
  "teacher-payables": decision((r) => `/teacher-payables/${r.id}/decide`, "payroll.approve"),
  "financial-years": [
    { label: "Close year", kind: "post", path: (r) => `/financial-years/${r.id}/close`, perms: ["finance.close_year"], danger: true, when: (r) => s(r, "status") === "open",
      confirm: "Closing locks all postings dated in this financial year. Continue?" },
  ],
  "book-loans": [
    { label: "Return / close", kind: "post", path: (r) => `/library/loans/${r.id}/return`, perms: ["library.write"], when: (r) => ["issued", "overdue"].includes(s(r, "status")),
      fields: [{ name: "outcome", label: "Outcome", type: "select", options: ["returned", "lost", "damaged"], required: true, default: "returned" },
        { name: "fine_amount", label: "Fine", type: "number", default: 0 }, { name: "remarks", label: "Remarks", type: "textarea" }] },
  ],
  books: [
    { label: "Issue book", kind: "post", path: () => `/library/issue`, perms: ["library.write"], when: (r) => Number(r.copies_available) > 0 && !r.is_digital,
      fields: [{ name: "member_id", label: "Member", type: "ref", ref: "library-members", required: true }, { name: "due_date", label: "Due date", type: "date", required: true }, { name: "remarks", label: "Remarks", type: "textarea" }],
      body: (r, v) => ({ book_id: r.id, ...v }) },
  ],
  announcements: [
    { label: "Publish", kind: "post", path: (r) => `/announcements/${r.id}/publish`, when: (r) => s(r, "status") === "draft", confirm: "Publish and notify the audience?" },
    { label: "Archive", kind: "post", path: (r) => `/announcements/${r.id}/archive`, when: (r) => s(r, "status") === "published", danger: true, confirm: "Archive this announcement?" },
  ],
  "follow-ups": [
    { label: "Complete", kind: "post", path: (r) => `/admissions/follow-ups/${r.id}/complete`, perms: ["admissions.write"], when: (r) => s(r, "status") === "pending",
      fields: [{ name: "status", label: "Result", type: "select", options: ["done", "missed", "cancelled"], required: true, default: "done" },
        { name: "outcome", label: "Outcome", type: "textarea", required: true }, { name: "next_follow_up_at", label: "Next follow-up", type: "datetime" }] },
  ],
  "re-evaluation-requests": [
    { label: "Decide", kind: "post", path: (r) => `/re-evaluation-requests/${r.id}/decide`, perms: ["results.approve"], when: (r) => ["pending", "accepted"].includes(s(r, "status")),
      fields: [{ name: "status", label: "Decision", type: "select", options: ["accepted", "rejected", "completed"], required: true },
        { name: "new_marks", label: "New marks (when completed)", type: "number" }, { name: "remarks", label: "Remarks", type: "textarea" }] },
  ],
  "exam-results": [
    { label: "Request re-evaluation", kind: "post", path: (r) => `/exam-results/${r.id}/re-evaluation`, when: (r) => s(r, "status") === "published",
      fields: [{ name: "reason", label: "Reason", type: "textarea", required: true }] },
  ],
  "notification-deliveries": [
    { label: "Retry", kind: "post", path: (r) => `/notification-deliveries/${r.id}/retry`, perms: ["notifications.write"], when: (r) => ["failed", "cancelled"].includes(s(r, "status")) },
  ],
  questions: [{ label: "Approve question", kind: "post", path: (r) => `/questions/${r.id}/approve`, when: (r) => r.is_approved === false }],
  schedules: [
    { label: "Generate sessions", kind: "post", path: () => `/schedules/generate-sessions`, perms: ["schedules.write"],
      fields: [{ name: "start_date", label: "From", type: "date", required: true, default: todayISO() }, { name: "end_date", label: "To", type: "date", required: true }],
      body: (r, v) => ({ ...v, schedule_ids: [r.id] }) },
  ],
  documents: [{ label: "Download", kind: "signed", path: (r) => `/documents/${r.id}/download-link` }],
  surveys: [
    { label: "Open survey", kind: "post", path: (r) => `/surveys/${r.id}/status`, when: (r) => s(r, "status") !== "open", body: () => ({ status: "open" }) },
    { label: "Close survey", kind: "post", path: (r) => `/surveys/${r.id}/status`, when: (r) => s(r, "status") === "open", body: () => ({ status: "closed" }) },
  ],
  "online-meetings": [{ label: "Join meeting", kind: "external", path: (r) => s(r, "join_url"), when: (r) => !!r.join_url }],
  "billable-charges": [
    { label: "Approve charge", kind: "post", path: () => `/billing/per-class/review`, perms: ["invoices.write"], when: (r) => s(r, "status") === "pending_review",
      body: (r) => ({ charge_ids: [r.id], action: "approve" }) },
    { label: "Waive charge", kind: "post", path: () => `/billing/per-class/review`, perms: ["invoices.write"], danger: true, when: (r) => s(r, "status") === "pending_review",
      fields: [{ name: "note", label: "Reason", type: "textarea", required: true }], body: (r, v) => ({ charge_ids: [r.id], action: "waive", note: v.note }) },
  ],
  jobs: [{ label: "Open", kind: "link", path: (r) => `/jobs/${r.id}` }],
  "payroll-periods": [{ label: "Open in payroll", kind: "link", path: () => `/payroll` }],
  enquiries: [{ label: "Open pipeline", kind: "link", path: () => `/admissions` }],
};
