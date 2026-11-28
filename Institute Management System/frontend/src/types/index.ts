export interface Me {
  user: {
    id: string;
    email: string;
    full_name: string;
    phone?: string | null;
    is_superuser: boolean;
    must_change_password: boolean;
    last_login_at?: string | null;
  };
  institute: {
    id: string;
    name: string;
    code: string;
    has_logo: boolean;
    primary_color: string;
    secondary_color: string;
    accent_color: string;
    timezone: string;
    currency: string;
    date_format: string;
    locale: string;
  } | null;
  institutes?: { id: string; name: string }[];
  portal: "admin" | "teacher" | "student" | "parent" | "platform";
  roles: string[];
  permissions: string[];
  branch_scoped?: boolean;
  branches: { id: string; name: string; code: string }[];
  student_id?: string | null;
  teacher_id?: string | null;
  parent_id?: string | null;
  linked_students?: { id: string; full_name: string; student_code: string }[];
  batch_ids?: string[];
  features: Record<string, boolean>;
}

export interface FieldMeta {
  name: string;
  label: string;
  type: "string" | "text" | "enum" | "ref" | "uuid" | "boolean" | "date" | "datetime" | "time" | "integer" | "decimal" | "money" | "json";
  widget?: string | null;
  required: boolean;
  nullable: boolean;
  enum?: string[] | null;
  ref?: string | null;
  max_length?: number | null;
  creatable: boolean;
  updatable: boolean;
  system: boolean;
}

export interface ResourceMeta {
  name: string;
  label: string;
  group: string;
  perm: string;
  feature?: string | null;
  title_field: string;
  search: boolean;
  list_columns: string[];
  default_sort: string;
  archive: boolean;
  read_mode: "all" | "own";
  can: { create: boolean; update: boolean; delete: boolean };
  fields: FieldMeta[];
}

export type Row = Record<string, unknown> & { id: string; display?: Record<string, string | null> };
