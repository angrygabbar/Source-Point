"use client";

import { AdminDashboard } from "@/features/dashboard/admin-dashboard";
import { ParentDashboard, StudentDashboard, TeacherDashboard } from "@/features/dashboard/portal-dashboards";
import { useSession } from "@/hooks/use-session";

export default function DashboardPage() {
  const { me } = useSession();
  if (!me) return null;
  if (me.portal === "teacher" && me.teacher_id) return <TeacherDashboard />;
  if (me.portal === "student" && me.student_id) return <StudentDashboard />;
  if (me.portal === "parent" && me.parent_id) return <ParentDashboard />;
  return <AdminDashboard />;
}
