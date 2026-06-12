import { api, type Artifact, type Job } from "../lib/api";
import { formatBytes, formatDuration, formatTimecode } from "../lib/format";

const sectionTitle = "mb-3 text-xs font-semibold uppercase tracking-wide text-gray-500 dark:text-gray-400";
const card = "rounded-xl border border-gray-200 bg-white dark:border-gray-800 dark:bg-gray-900";

function DownloadButton({ jobId, artifact }: { jobId: string; artifact: Artifact }) {
  return (
    <a
      href={api.artifactUrl(jobId, artifact.id)}
      download
      className="flex items-center justify-between gap-3 rounded-lg border border-gray-200 px-4 py-3 transition hover:border-gray-400 hover:bg-gray-50 dark:border-gray-800 dark:hover:border-gray-600 dark:hover:bg-gray-800"
    >
      <span className="text-sm font-medium text-gray-800 dark:text-gray-200">{artifact.label}</span>
      <span className="flex items-center gap-2 text-xs text-gray-400 dark:text-gray-500">
        {formatBytes(artifact.size)}
        <svg className="h-4 w-4 text-gray-500 dark:text-gray-400" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
          <path strokeLinecap="round" strokeLinejoin="round" d="M3 16.5v2.25A2.25 2.25 0 0 0 5.25 21h13.5A2.25 2.25 0 0 0 21 18.75V16.5M16.5 12 12 16.5m0 0L7.5 12m4.5 4.5V3" />
        </svg>
      </span>
    </a>
  );
}

export function JobResult({ job }: { job: Job }) {
  const r = job.result;
  if (!r) return null;

  return (
    <div className="space-y-6">
      {job.thumbnail && (
        <img
          src={api.thumbnailUrl(job.id)}
          alt=""
          className="max-h-40 rounded-xl border border-gray-200 dark:border-gray-800"
        />
      )}

      {r.warnings.length > 0 && (
        <div className="rounded-lg border border-amber-200 bg-amber-50 px-4 py-3 text-sm text-amber-800 dark:border-amber-500/30 dark:bg-amber-500/10 dark:text-amber-300">
          <ul className="list-disc space-y-0.5 pl-4">
            {r.warnings.map((w, i) => (
              <li key={i}>{w}</li>
            ))}
          </ul>
        </div>
      )}

      <div className={`flex flex-wrap items-center gap-x-8 gap-y-2 px-5 py-4 ${card}`}>
        <Stat label="Language" value={r.detected_language ?? "—"} />
        <Stat label="Duration" value={formatDuration(r.duration)} />
        <Stat label="Cues" value={String(r.cue_count)} />
      </div>

      {r.artifacts.length > 0 && (
        <section>
          <h3 className={sectionTitle}>Downloads</h3>
          <div className="grid gap-2 sm:grid-cols-2">
            {r.artifacts.map((a) => (
              <DownloadButton key={a.id} jobId={job.id} artifact={a} />
            ))}
          </div>
        </section>
      )}

      {r.chapters.length > 0 && (
        <section>
          <h3 className={sectionTitle}>Chapters</h3>
          <ul className={`divide-y divide-gray-100 overflow-hidden dark:divide-gray-800 ${card}`}>
            {r.chapters.map((c, i) => (
              <li key={i} className="flex items-center gap-3 px-4 py-2.5">
                <span className="w-16 shrink-0 font-mono text-xs text-gray-500 dark:text-gray-400">
                  {formatTimecode(c.start)}
                </span>
                <span className="text-sm text-gray-800 dark:text-gray-200">{c.title}</span>
              </li>
            ))}
          </ul>
        </section>
      )}

      {r.summary && (
        <section>
          <h3 className={sectionTitle}>Summary</h3>
          <p className={`p-4 text-sm leading-relaxed text-gray-700 dark:text-gray-300 ${card}`}>
            {r.summary}
          </p>
        </section>
      )}

      {r.preview_segments.length > 0 && (
        <section>
          <h3 className={sectionTitle}>Subtitle preview</h3>
          <div className={`max-h-72 space-y-1.5 overflow-y-auto p-4 ${card}`}>
            {r.preview_segments.map((s, i) => (
              <div key={i} className="flex gap-3 text-sm">
                <span className="w-12 shrink-0 font-mono text-xs text-gray-400 dark:text-gray-500">
                  {formatTimecode(s.start)}
                </span>
                <span className="text-gray-700 dark:text-gray-300">{s.text}</span>
              </div>
            ))}
          </div>
        </section>
      )}
    </div>
  );
}

function Stat({ label, value }: { label: string; value: string }) {
  return (
    <div>
      <p className="text-xs uppercase tracking-wide text-gray-400 dark:text-gray-500">{label}</p>
      <p className="font-medium text-gray-900 dark:text-gray-100">{value}</p>
    </div>
  );
}
