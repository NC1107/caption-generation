import type { Job, UploadProgress } from "../lib/api";
import { formatBytes, formatEta, formatEtaShort, formatSpeed } from "../lib/format";

export function JobProgress({ job, upload }: { job: Job | null; upload: UploadProgress | null }) {
  const isUploading = !job;
  const pct = isUploading ? (upload?.fraction ?? 0) : job.progress;
  const message = isUploading
    ? upload && upload.fraction < 1
      ? `Uploading… ${Math.round(upload.fraction * 100)}%`
      : "Finishing upload…"
    : job.stage_message;

  // Rough remaining estimate from elapsed wall time ÷ progress.
  const remainingSec =
    job && job.progress > 0.04 && job.progress < 0.99
      ? ((Date.now() - new Date(job.created_at).getTime()) / 1000) *
        ((1 - job.progress) / job.progress)
      : null;

  return (
    <div className="rounded-xl border border-gray-200 bg-white p-6 dark:border-gray-800 dark:bg-gray-900">
      <p className="mb-3 font-medium text-gray-900 dark:text-gray-100">
        {message}
        {remainingSec ? (
          <span className="font-normal text-gray-500 dark:text-gray-400">
            {" "}
            · {formatEtaShort(remainingSec)} left
          </span>
        ) : null}
      </p>
      <div className="h-2 w-full overflow-hidden rounded-full bg-gray-100 dark:bg-gray-800">
        <div
          className="h-full rounded-full bg-gray-900 transition-all duration-500 dark:bg-gray-100"
          style={{ width: `${Math.max(4, Math.round(pct * 100))}%` }}
        />
      </div>

      {isUploading && upload && upload.total > 0 && (
        <div className="mt-3 flex flex-wrap gap-x-3 gap-y-1 text-sm text-gray-500 dark:text-gray-400">
          <span>
            {formatBytes(upload.loaded)} / {formatBytes(upload.total)}
          </span>
          <span>· {formatSpeed(upload.speed)}</span>
          {upload.fraction < 1 && <span>· {formatEta(upload.eta)} left</span>}
        </div>
      )}

      {!isUploading && (
        <p className="mt-3 text-sm text-gray-500 dark:text-gray-400">
          You can leave this page — the job keeps running and shows up under “Recent”.
        </p>
      )}
    </div>
  );
}
