import { GraduationCap } from "lucide-react";
import type { ReactNode } from "react";

export function AuthLayout({ title, subtitle, children }: { title: string; subtitle?: string; children: ReactNode }) {
  return (
    <div className="grid min-h-screen lg:grid-cols-2">
      <div className="hidden flex-col justify-between bg-brand-800 p-10 text-white lg:flex">
        <div className="flex items-center gap-2 text-lg font-semibold">
          <GraduationCap className="h-6 w-6" /> Institute Management System
        </div>
        <div>
          <h2 className="text-3xl font-semibold leading-tight">Run every class, fee and follow-up from one place.</h2>
          <p className="mt-3 max-w-md text-indigo-100">
            Timetables, attendance, homework, examinations, billing, payroll and parent communication — connected through one secure record.
          </p>
        </div>
        <p className="text-xs text-indigo-200">Admin · Teacher · Student · Parent portals</p>
      </div>
      <div className="flex items-center justify-center p-6">
        <div className="w-full max-w-sm">
          <div className="mb-6 flex items-center gap-2 text-brand-800 lg:hidden">
            <GraduationCap className="h-6 w-6" /> <span className="font-semibold">Institute Management System</span>
          </div>
          <h1 className="text-2xl font-semibold text-slate-900">{title}</h1>
          {subtitle && <p className="mb-6 mt-1 text-sm text-slate-500">{subtitle}</p>}
          {children}
        </div>
      </div>
    </div>
  );
}
