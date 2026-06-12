import type { JobStatus } from "../lib/api";

const STATUS_META: Record<JobStatus, { label: string; cls: string }> = {
  queued: { label: "Queued", cls: "bg-gray-100 text-gray-600 dark:bg-gray-800 dark:text-gray-400" },
  extracting: {
    label: "Extracting",
    cls: "bg-blue-50 text-blue-700 dark:bg-blue-500/15 dark:text-blue-300",
  },
  transcribing: {
    label: "Transcribing",
    cls: "bg-blue-50 text-blue-700 dark:bg-blue-500/15 dark:text-blue-300",
  },
  enhancing: {
    label: "Enhancing",
    cls: "bg-blue-50 text-blue-700 dark:bg-blue-500/15 dark:text-blue-300",
  },
  completed: {
    label: "Completed",
    cls: "bg-green-50 text-green-700 dark:bg-green-500/15 dark:text-green-300",
  },
  failed: { label: "Failed", cls: "bg-red-50 text-red-700 dark:bg-red-500/15 dark:text-red-300" },
};

export function StatusBadge({ status }: { status: JobStatus }) {
  const m = STATUS_META[status];
  return (
    <span className={`rounded-full px-2 py-0.5 text-xs font-medium ${m.cls}`}>{m.label}</span>
  );
}
