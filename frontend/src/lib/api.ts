export type JobStatus =
  | "queued"
  | "extracting"
  | "transcribing"
  | "enhancing"
  | "completed"
  | "failed";

export interface Segment {
  start: number;
  end: number;
  text: string;
}

export interface Chapter {
  start: number;
  title: string;
}

export interface Artifact {
  id: string;
  kind: string;
  label: string;
  filename: string;
  content_type: string;
  size: number;
}

export interface JobResult {
  detected_language: string | null;
  duration: number | null;
  cue_count: number;
  artifacts: Artifact[];
  chapters: Chapter[];
  summary: string | null;
  preview_segments: Segment[];
  warnings: string[];
}

export interface JobOptions {
  source_language: string | null;
  generate_chapters: boolean;
  chapter_count: number | null;
  generate_summary: boolean;
  translate_to: string | null;
  whisper_model: string | null;
  whisper_compute_type: string | null;
  llm_model: string | null;
}

export interface Job {
  id: string;
  status: JobStatus;
  progress: number;
  stage_message: string;
  filename: string;
  size: number;
  thumbnail: boolean;
  created_at: string;
  updated_at: string;
  options: JobOptions;
  result: JobResult | null;
  error: string | null;
}

export interface AppConfig {
  name: string;
  version: string;
  transcribe_engine: string;
  whisper_model: string;
  whisper_device: string;
  whisper_compute_type: string;
  llm_enabled: boolean;
  llm_model: string | null;
  translation_enabled: boolean;
  translation_english_only: boolean;
  max_upload_mb: number;
}

export interface UploadProgress {
  fraction: number;
  loaded: number;
  total: number;
  speed: number; // bytes per second
  eta: number; // seconds remaining
}

async function json<T>(res: Response): Promise<T> {
  if (!res.ok) {
    let detail = res.statusText;
    try {
      detail = (await res.json()).detail ?? detail;
    } catch {
      /* ignore */
    }
    throw new Error(detail);
  }
  return res.json() as Promise<T>;
}

export const api = {
  getConfig: () => fetch("/api/config").then((r) => json<AppConfig>(r)),

  llmModels: () =>
    fetch("/api/llm/models").then((r) => json<{ models: string[]; current: string | null }>(r)),

  listJobs: () => fetch("/api/jobs").then((r) => json<Job[]>(r)),

  getJob: (id: string) => fetch(`/api/jobs/${id}`).then((r) => json<Job>(r)),

  deleteJob: (id: string) =>
    fetch(`/api/jobs/${id}`, { method: "DELETE" }).then((r) => {
      if (!r.ok && r.status !== 204) throw new Error("Failed to delete job");
    }),

  artifactUrl: (jobId: string, artifactId: string) =>
    `/api/jobs/${jobId}/artifacts/${artifactId}`,

  thumbnailUrl: (jobId: string) => `/api/jobs/${jobId}/thumbnail`,

  /** Upload with progress (size / speed / ETA) via XHR. */
  createJob(
    file: File,
    options: JobOptions,
    onProgress?: (p: UploadProgress) => void,
  ): Promise<{ id: string }> {
    return new Promise((resolve, reject) => {
      const form = new FormData();
      form.append("file", file);
      if (options.source_language) form.append("source_language", options.source_language);
      form.append("generate_chapters", String(options.generate_chapters));
      if (options.chapter_count != null) form.append("chapter_count", String(options.chapter_count));
      form.append("generate_summary", String(options.generate_summary));
      if (options.translate_to) form.append("translate_to", options.translate_to);
      if (options.whisper_model) form.append("whisper_model", options.whisper_model);
      if (options.whisper_compute_type)
        form.append("whisper_compute_type", options.whisper_compute_type);
      if (options.llm_model) form.append("llm_model", options.llm_model);

      const xhr = new XMLHttpRequest();
      const startedAt = performance.now();
      xhr.open("POST", "/api/jobs");
      xhr.upload.onprogress = (e) => {
        if (!e.lengthComputable || !onProgress) return;
        const elapsed = (performance.now() - startedAt) / 1000;
        const speed = elapsed > 0 ? e.loaded / elapsed : 0;
        const eta = speed > 0 ? (e.total - e.loaded) / speed : Infinity;
        onProgress({ fraction: e.loaded / e.total, loaded: e.loaded, total: e.total, speed, eta });
      };
      xhr.onload = () => {
        if (xhr.status >= 200 && xhr.status < 300) {
          resolve(JSON.parse(xhr.responseText));
        } else {
          let msg = `Upload failed (${xhr.status})`;
          try {
            msg = JSON.parse(xhr.responseText).detail ?? msg;
          } catch {
            /* ignore */
          }
          reject(new Error(msg));
        }
      };
      xhr.onerror = () => reject(new Error("Network error during upload"));
      xhr.send(form);
    });
  },
};

export const TERMINAL: JobStatus[] = ["completed", "failed"];
