import { useCallback, useEffect, useRef, useState } from "react";
import {
  api,
  type AppConfig,
  type Job,
  type JobOptions,
  TERMINAL,
  type UploadProgress,
} from "./lib/api";
import { Dropzone } from "./components/Dropzone";
import { OptionsForm } from "./components/OptionsForm";
import { JobProgress } from "./components/JobProgress";
import { JobResult } from "./components/JobResult";
import { RecentJobs } from "./components/RecentJobs";

const DEFAULT_OPTIONS: JobOptions = {
  source_language: null,
  generate_chapters: false,
  chapter_count: null,
  generate_summary: false,
  translate_to: null,
  whisper_model: null,
  whisper_compute_type: null,
  llm_model: null,
};

export default function App() {
  const [config, setConfig] = useState<AppConfig | null>(null);
  const [configError, setConfigError] = useState<string | null>(null);

  const [file, setFile] = useState<File | null>(null);
  const [mediaDuration, setMediaDuration] = useState<number | null>(null);
  const [options, setOptions] = useState<JobOptions>(DEFAULT_OPTIONS);

  const [view, setView] = useState<"new" | "job">("new");
  const [activeJobId, setActiveJobId] = useState<string | null>(null);
  const [activeJob, setActiveJob] = useState<Job | null>(null);
  const [upload, setUpload] = useState<UploadProgress | null>(null);
  const [submitting, setSubmitting] = useState(false);
  const [submitError, setSubmitError] = useState<string | null>(null);

  const [recent, setRecent] = useState<Job[]>([]);
  const [dark, setDark] = useState(() => document.documentElement.classList.contains("dark"));

  const toggleTheme = () => {
    const next = !dark;
    setDark(next);
    document.documentElement.classList.toggle("dark", next);
    localStorage.setItem("theme", next ? "dark" : "light");
  };

  const loadRecent = useCallback(() => {
    api.listJobs().then(setRecent).catch(() => {});
  }, []);

  useEffect(() => {
    api
      .getConfig()
      .then(setConfig)
      .catch((e) => setConfigError(e.message));
    loadRecent();
  }, [loadRecent]);

  useEffect(() => {
    const t = setInterval(loadRecent, 4000);
    return () => clearInterval(t);
  }, [loadRecent]);

  // Poll the active job until it reaches a terminal state.
  const pollTimer = useRef<number | null>(null);
  useEffect(() => {
    if (!activeJobId) return;
    if (activeJob && TERMINAL.includes(activeJob.status)) return;
    pollTimer.current = window.setTimeout(() => {
      api
        .getJob(activeJobId)
        .then((j) => {
          setActiveJob(j);
          if (TERMINAL.includes(j.status)) loadRecent();
        })
        .catch(() => {});
    }, 1200);
    return () => {
      if (pollTimer.current) window.clearTimeout(pollTimer.current);
    };
  }, [activeJobId, activeJob, loadRecent]);

  const submit = async () => {
    if (!file) return;
    setSubmitting(true);
    setSubmitError(null);
    setUpload(null);
    setActiveJob(null);
    setActiveJobId(null);
    setView("job");
    try {
      const { id } = await api.createJob(file, options, setUpload);
      setActiveJobId(id);
      loadRecent();
    } catch (e) {
      setSubmitError((e as Error).message);
      setView("new");
    } finally {
      setSubmitting(false);
    }
  };

  const startNew = () => {
    setFile(null);
    setActiveJob(null);
    setActiveJobId(null);
    setSubmitError(null);
    setView("new");
  };

  const selectJob = (job: Job) => {
    setActiveJob(job);
    setActiveJobId(job.id);
    setView("job");
  };

  const deleteJob = async (job: Job) => {
    await api.deleteJob(job.id).catch(() => {});
    if (job.id === activeJobId) startNew();
    loadRecent();
  };

  return (
    <div className="mx-auto flex min-h-full max-w-6xl flex-col gap-8 px-4 py-10 sm:px-6">
      <Header config={config} dark={dark} onToggleTheme={toggleTheme} />

      {configError && (
        <div className="rounded-lg border border-red-200 bg-red-50 px-4 py-3 text-sm text-red-700 dark:border-red-500/30 dark:bg-red-500/10 dark:text-red-300">
          Couldn’t reach the API: {configError}
        </div>
      )}

      <div className="grid flex-1 gap-8 lg:grid-cols-[1fr_260px]">
        <main className="min-w-0">
          {view === "new" && config && (
            <div className="space-y-6 rounded-xl border border-gray-200 bg-white p-7 dark:border-gray-800 dark:bg-gray-900">
              <Dropzone
                file={file}
                onSelect={setFile}
                onMeta={setMediaDuration}
                maxMb={config.max_upload_mb}
              />
              <OptionsForm
                config={config}
                options={options}
                onChange={setOptions}
                mediaDuration={mediaDuration}
              />
              {submitError && <p className="text-sm text-red-600 dark:text-red-400">{submitError}</p>}
              <button
                disabled={!file || submitting}
                onClick={submit}
                className="w-full rounded-md bg-gray-900 px-4 py-2.5 font-medium text-white transition enabled:hover:bg-gray-800 disabled:cursor-not-allowed disabled:opacity-40 dark:bg-gray-100 dark:text-gray-900 dark:enabled:hover:bg-gray-200"
              >
                {submitting ? "Starting…" : "Generate subtitles"}
              </button>
            </div>
          )}

          {view === "job" && (
            <div className="space-y-6">
              <div className="flex items-center justify-between gap-3">
                <h2 className="truncate text-lg font-semibold text-gray-900 dark:text-gray-100">
                  {activeJob?.filename ?? file?.name ?? "Processing…"}
                </h2>
                <button
                  onClick={startNew}
                  className="shrink-0 rounded-md border border-gray-300 px-3 py-1.5 text-sm text-gray-700 hover:bg-gray-100 dark:border-gray-700 dark:text-gray-300 dark:hover:bg-gray-800"
                >
                  + New
                </button>
              </div>

              {(!activeJob || !TERMINAL.includes(activeJob.status)) && (
                <JobProgress job={activeJob} upload={upload} />
              )}

              {activeJob?.status === "failed" && (
                <div className="rounded-lg border border-red-200 bg-red-50 px-5 py-4 text-red-700 dark:border-red-500/30 dark:bg-red-500/10 dark:text-red-300">
                  <p className="font-medium">This job failed.</p>
                  <p className="mt-1 text-sm opacity-80">{activeJob.error}</p>
                </div>
              )}

              {activeJob?.status === "completed" && <JobResult job={activeJob} />}
            </div>
          )}
        </main>

        <aside className="lg:sticky lg:top-8 lg:self-start">
          <h2 className="mb-3 text-xs font-semibold uppercase tracking-wide text-gray-500 dark:text-gray-400">
            Recent
          </h2>
          <RecentJobs jobs={recent} activeId={activeJobId} onSelect={selectJob} onDelete={deleteJob} />
        </aside>
      </div>

      <Footer config={config} />
    </div>
  );
}

function Header({
  config,
  dark,
  onToggleTheme,
}: {
  config: AppConfig | null;
  dark: boolean;
  onToggleTheme: () => void;
}) {
  return (
    <header className="flex flex-wrap items-center justify-between gap-4 border-b border-gray-200 pb-5 dark:border-gray-800">
      <div>
        <h1 className="text-xl font-semibold tracking-tight text-gray-900 dark:text-gray-100">
          Caption Generation
        </h1>
        <p className="text-sm text-gray-500 dark:text-gray-400">
          Subtitles, chapters, summaries &amp; translation.
        </p>
      </div>
      <div className="flex flex-wrap items-center gap-2 text-xs">
        {config && (
          <>
            <Pill>
              {config.transcribe_engine === "local" ? "Local Whisper" : "Whisper API"} ·{" "}
              {config.whisper_model}
            </Pill>
            <Pill>{config.llm_enabled ? `LLM · ${config.llm_model}` : "LLM off"}</Pill>
          </>
        )}
        <button
          onClick={onToggleTheme}
          title={dark ? "Switch to light" : "Switch to dark"}
          aria-label="Toggle theme"
          className="rounded-md border border-gray-200 p-1.5 text-gray-600 hover:bg-gray-100 dark:border-gray-700 dark:text-gray-300 dark:hover:bg-gray-800"
        >
          {dark ? (
            <svg className="h-4 w-4" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={1.8}>
              <circle cx="12" cy="12" r="4" />
              <path strokeLinecap="round" d="M12 2v2m0 16v2M4.9 4.9l1.4 1.4m11.4 11.4 1.4 1.4M2 12h2m16 0h2M4.9 19.1l1.4-1.4m11.4-11.4 1.4-1.4" />
            </svg>
          ) : (
            <svg className="h-4 w-4" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={1.8}>
              <path strokeLinecap="round" strokeLinejoin="round" d="M21 12.8A9 9 0 1 1 11.2 3a7 7 0 0 0 9.8 9.8Z" />
            </svg>
          )}
        </button>
      </div>
    </header>
  );
}

function Pill({ children }: { children: React.ReactNode }) {
  return (
    <span className="rounded-full border border-gray-200 bg-white px-2.5 py-1 font-medium text-gray-600 dark:border-gray-700 dark:bg-gray-900 dark:text-gray-400">
      {children}
    </span>
  );
}

function Footer({ config }: { config: AppConfig | null }) {
  return (
    <footer className="border-t border-gray-200 pt-4 text-center text-xs text-gray-400 dark:border-gray-800 dark:text-gray-500">
      Caption Generation{config ? ` v${config.version}` : ""} · MIT licensed
    </footer>
  );
}
