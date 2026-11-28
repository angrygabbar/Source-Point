"use client";

import { useParams } from "next/navigation";
import { PageHeader } from "@/components/ui";
import { ResourceList } from "@/components/data/resource-list";
import { useMeta } from "@/hooks/use-meta";

export default function ResourcePage() {
  const { resource } = useParams<{ resource: string }>();
  const meta = useMeta(resource);
  return (
    <>
      <PageHeader title={meta.data?.label ?? "Loading…"} description={meta.data ? `${meta.data.group}${meta.data.read_mode === "own" ? " · showing records you can access" : ""}` : undefined} />
      <ResourceList resource={resource} />
    </>
  );
}
