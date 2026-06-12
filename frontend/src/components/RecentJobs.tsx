import { api, type Job } from "../lib/api";
import { relativeTime } from "../lib/format";
import { StatusBadge } from "./ui";

interface Props {
  jobs: Job[];
  activeId: string | null;
  onSelect: (job: Job) => void;
  onDelete: (job: Job) => void;
}

function Thumb({ job }: { job: Job }) {
  if (job.thumbnail) {
    return (
      <img
        src={api.thumbnailUrl(job.id)}
        alt=""
        className="h-10 w-16 shrink-0 rounded object-cover"
      />
    );
  }
  return (
    <div className="flex h-10 w-16 shrink-0 items-center justify-center rounded bg-gray-100 text-gray-400 dark:bg-gray-800 dark:text-gray-500">
      <svg className="h-4 w-4" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={1.5}>
        <path strokeLinecap="round" strokeLinejoin="round" d="M9 9V5l-2 1m8 12v-1m-9-3 3 3 7-7" />
        <path strokeLinecap="round" d="M3 6h4M3 18h6" />
      </svg>
    </div>
  );
}

export function RecentJobs({ jobs, activeId, onSelect, onDelete }: Props) {
  if (jobs.length === 0) {
    return <p className="text-sm text-gray-400 dark:text-gray-500">No jobs yet.</p>;
  }
  return (
    <ul className="space-y-2">
      {jobs.map((job) => (
        <li
          key={job.id}
          onClick={() => onSelect(job)}
          className={[
            "group flex cursor-pointer items-center gap-3 rounded-lg border px-3 py-2.5 transition",
            job.id === activeId
              ? "border-gray-900 bg-gray-50 dark:border-gray-300 dark:bg-gray-800"
              : "border-gray-200 bg-white hover:border-gray-300 dark:border-gray-800 dark:bg-gray-900 dark:hover:border-gray-700",
          ].join(" ")}
        >
          <Thumb job={job} />
          <div className="min-w-0 flex-1">
            <div className="flex items-center justify-between gap-2">
              <span className="truncate text-sm font-medium text-gray-800 dark:text-gray-200">
                {job.filename}
              </span>
              <button
                onClick={(e) => {
                  e.stopPropagation();
                  onDelete(job);
                }}
                title="Delete job"
                className="text-gray-300 opacity-0 transition group-hover:opacity-100 hover:text-red-500 dark:text-gray-600"
              >
                <svg className="h-4 w-4" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
                  <path strokeLinecap="round" strokeLinejoin="round" d="M6 18 18 6M6 6l12 12" />
                </svg>
              </button>
            </div>
            <div className="mt-1.5 flex items-center justify-between">
              <StatusBadge status={job.status} />
              <span className="text-xs text-gray-400 dark:text-gray-500">
                {relativeTime(job.created_at)}
              </span>
            </div>
          </div>
        </li>
      ))}
    </ul>
  );
}
