import { useEffect, useRef, useState } from "react";
import { api, type AppConfig, type JobOptions } from "../lib/api";
import {
  CHAPTER_COUNTS,
  SOURCE_LANGUAGES,
  TARGET_LANGUAGES,
  WHISPER_COMPUTE_TYPES,
  WHISPER_MODELS,
  WHISPER_REALTIME_CPU,
} from "../lib/constants";
import { formatEta } from "../lib/format";

interface Props {
  config: AppConfig;
  options: JobOptions;
  onChange: (next: JobOptions) => void;
  mediaDuration: number | null;
}

const inputCls =
  "w-full rounded-md border border-gray-300 bg-white px-3 py-2 text-gray-900 outline-none focus:border-gray-900 dark:border-gray-700 dark:bg-gray-900 dark:text-gray-100 dark:focus:border-gray-300";
const labelCls = "mb-1 block text-sm font-medium text-gray-700 dark:text-gray-300";
const sublabelCls = "mb-1 block text-xs font-medium text-gray-500 dark:text-gray-400";
const sectionTitle = "mb-3 text-xs font-semibold uppercase tracking-wide text-gray-500 dark:text-gray-400";
const hintCls = "text-xs text-gray-500 dark:text-gray-400";

function Toggle({
  checked,
  onChange,
  disabled,
  title,
  children,
}: {
  checked: boolean;
  onChange: (v: boolean) => void;
  disabled?: boolean;
  title?: string;
  children: React.ReactNode;
}) {
  return (
    <label
      title={title}
      className={[
        "flex items-center gap-3 rounded-lg border border-gray-200 px-4 py-2.5 transition dark:border-gray-800",
        disabled ? "opacity-50" : "cursor-pointer hover:border-gray-300 dark:hover:border-gray-700",
      ].join(" ")}
    >
      <input
        type="checkbox"
        className="h-4 w-4 accent-gray-900 dark:accent-gray-100"
        checked={checked}
        disabled={disabled}
        onChange={(e) => onChange(e.target.checked)}
      />
      <span className="text-sm text-gray-700 dark:text-gray-300">{children}</span>
    </label>
  );
}

/** A combobox with a dropdown caret: type to filter, click an option, or enter a custom value. */
function SearchableSelect({
  value,
  onChange,
  options,
  placeholder,
}: {
  value: string;
  onChange: (v: string) => void;
  options: string[];
  placeholder?: string;
}) {
  const [open, setOpen] = useState(false);
  const [query, setQuery] = useState(value);
  const ref = useRef<HTMLDivElement>(null);

  useEffect(() => setQuery(value), [value]);
  useEffect(() => {
    function onDoc(e: MouseEvent) {
      if (ref.current && !ref.current.contains(e.target as Node)) setOpen(false);
    }
    document.addEventListener("mousedown", onDoc);
    return () => document.removeEventListener("mousedown", onDoc);
  }, []);

  const filtered = options.filter((o) => o.toLowerCase().includes(query.toLowerCase()));
  return (
    <div ref={ref} className="relative">
      <input
        value={query}
        placeholder={placeholder}
        onFocus={() => setOpen(true)}
        onClick={() => setOpen(true)}
        onChange={(e) => {
          setQuery(e.target.value);
          onChange(e.target.value);
          setOpen(true);
        }}
        className={`${inputCls} pr-9`}
      />
      <svg
        className="pointer-events-none absolute right-3 top-1/2 h-4 w-4 -translate-y-1/2 text-gray-400"
        fill="none"
        viewBox="0 0 24 24"
        stroke="currentColor"
        strokeWidth={2}
      >
        <path strokeLinecap="round" strokeLinejoin="round" d="m6 9 6 6 6-6" />
      </svg>
      {open && (
        <ul className="absolute z-20 mt-1 max-h-52 w-full overflow-auto rounded-md border border-gray-200 bg-white shadow-lg dark:border-gray-700 dark:bg-gray-900">
          {(filtered.length ? filtered : options).map((o) => (
            <li
              key={o}
              onMouseDown={() => {
                onChange(o);
                setQuery(o);
                setOpen(false);
              }}
              className="cursor-pointer px-3 py-2 text-sm text-gray-700 hover:bg-gray-100 dark:text-gray-300 dark:hover:bg-gray-800"
            >
              {o}
            </li>
          ))}
        </ul>
      )}
    </div>
  );
}

function estimateEtaSeconds(durationSec: number, model: string, device: string): number {
  const rt = WHISPER_REALTIME_CPU[model] ?? 5;
  const factor = device === "cuda" ? rt * 10 : rt;
  return durationSec / factor + 5; // + a little fixed overhead
}

export function OptionsForm({ config, options, onChange, mediaDuration }: Props) {
  const set = (patch: Partial<JobOptions>) => onChange({ ...options, ...patch });
  const llmOn = config.llm_enabled;
  const llmHint = llmOn ? undefined : "Requires an LLM — set LLM_BASE_URL to enable.";

  const [models, setModels] = useState<string[]>([]);
  useEffect(() => {
    if (llmOn) api.llmModels().then((r) => setModels(r.models)).catch(() => {});
  }, [llmOn]);

  const translateOn = options.translate_to != null;
  const englishOnly = config.translation_english_only;

  const currentModel = options.llm_model ?? config.llm_model ?? "";
  const modelOptions = (() => {
    const base = models.length ? models : config.llm_model ? [config.llm_model] : [];
    return currentModel && !base.includes(currentModel) ? [currentModel, ...base] : base;
  })();

  const effWhisperModel = options.whisper_model ?? config.whisper_model;
  const eta =
    mediaDuration != null
      ? estimateEtaSeconds(mediaDuration, effWhisperModel, config.whisper_device)
      : null;
  const hasExtras =
    options.generate_chapters || options.generate_summary || options.translate_to != null;

  return (
    <div className="space-y-5">
      <div>
        <label className={labelCls}>Spoken language</label>
        <select
          value={options.source_language ?? "auto"}
          onChange={(e) =>
            set({ source_language: e.target.value === "auto" ? null : e.target.value })
          }
          className={inputCls}
        >
          {SOURCE_LANGUAGES.map((l) => (
            <option key={l.code} value={l.code}>
              {l.label}
            </option>
          ))}
        </select>
      </div>

      <div className="grid gap-3 sm:grid-cols-2">
        <Toggle
          checked={options.generate_chapters}
          onChange={(v) => set({ generate_chapters: v })}
          disabled={!llmOn}
          title={llmHint}
        >
          Generate chapters
        </Toggle>
        <Toggle
          checked={options.generate_summary}
          onChange={(v) => set({ generate_summary: v })}
          disabled={!llmOn}
          title={llmHint}
        >
          Write a summary
        </Toggle>
      </div>

      {options.generate_chapters && llmOn && (
        <div className="pl-1">
          <label className={sublabelCls}>How many chapters?</label>
          <select
            value={options.chapter_count == null ? "auto" : String(options.chapter_count)}
            onChange={(e) =>
              set({ chapter_count: e.target.value === "auto" ? null : Number(e.target.value) })
            }
            className={`${inputCls} sm:max-w-xs`}
          >
            {CHAPTER_COUNTS.map((c) => (
              <option key={c.label} value={c.value == null ? "auto" : String(c.value)}>
                {c.label}
              </option>
            ))}
          </select>
        </div>
      )}

      {/* Translation — independent of the LLM (Whisper handles English locally). */}
      <div
        className={[
          "rounded-lg border border-gray-200 p-4 dark:border-gray-800",
          config.translation_enabled ? "" : "opacity-50",
        ].join(" ")}
      >
        <label className="flex cursor-pointer items-center gap-3">
          <input
            type="checkbox"
            className="h-4 w-4 accent-gray-900 dark:accent-gray-100"
            disabled={!config.translation_enabled}
            checked={translateOn}
            onChange={(e) =>
              set({ translate_to: e.target.checked ? (englishOnly ? "English" : "") : null })
            }
          />
          <span className="text-sm text-gray-700 dark:text-gray-300">Translate subtitles</span>
        </label>
        {translateOn && !englishOnly && (
          <div className="mt-3 pl-7">
            <SearchableSelect
              value={options.translate_to ?? ""}
              onChange={(v) => set({ translate_to: v })}
              options={TARGET_LANGUAGES}
              placeholder="Search or pick a language…"
            />
            {!options.translate_to && (
              <p className="mt-1.5 text-xs text-gray-500 dark:text-gray-400">
                Pick a target language.
              </p>
            )}
          </div>
        )}
        {translateOn && englishOnly && (
          <p className="mt-2 pl-7 text-xs text-gray-500 dark:text-gray-400">
            → English. Your setup translates to English only — add LibreTranslate
            (<code className="rounded bg-gray-100 px-1 dark:bg-gray-800">LIBRETRANSLATE_URL</code>)
            or an LLM for other languages.
          </p>
        )}
      </div>

      {/* AI model dropdown — only when an LLM is configured. */}
      {llmOn && (
        <div>
          <label className={labelCls}>AI model</label>
          <select
            value={currentModel}
            onChange={(e) => set({ llm_model: e.target.value || null })}
            className={inputCls}
          >
            {modelOptions.map((m) => (
              <option key={m} value={m}>
                {m}
              </option>
            ))}
          </select>
          <p className={`mt-1 ${hintCls}`}>
            Models come from your LLM server. Add more with e.g.{" "}
            <code className="rounded bg-gray-100 px-1 dark:bg-gray-800">ollama pull llama3.1:8b</code>.
          </p>
        </div>
      )}

      {/* Transcription settings — visible, with defaults called out. */}
      {config.transcribe_engine === "local" && (
        <div className="rounded-lg border border-gray-200 p-4 dark:border-gray-800">
          <h3 className={sectionTitle}>Transcription</h3>
          <div className="grid gap-3 sm:grid-cols-2">
            <div>
              <label className={sublabelCls}>Model size</label>
              <select
                value={effWhisperModel}
                onChange={(e) => set({ whisper_model: e.target.value })}
                className={inputCls}
              >
                {WHISPER_MODELS.map((m) => (
                  <option key={m} value={m}>
                    {m}
                    {m === config.whisper_model ? " (default)" : ""}
                  </option>
                ))}
              </select>
            </div>
            <div>
              <label className={sublabelCls}>Precision</label>
              <select
                value={options.whisper_compute_type ?? config.whisper_compute_type}
                onChange={(e) => set({ whisper_compute_type: e.target.value })}
                className={inputCls}
              >
                {WHISPER_COMPUTE_TYPES.map((c) => (
                  <option key={c} value={c}>
                    {c}
                    {c === config.whisper_compute_type ? " (default)" : ""}
                  </option>
                ))}
              </select>
            </div>
          </div>
          <p className={`mt-3 ${hintCls}`}>
            Defaults: <strong>{config.whisper_model}</strong> · {config.whisper_compute_type} on{" "}
            {config.whisper_device}. Bigger models are more accurate but slower.
          </p>
          {eta != null && (
            <p className="mt-1 text-xs text-gray-600 dark:text-gray-300">
              Estimated transcription: <strong>~{formatEta(eta)}</strong>
              {config.whisper_device !== "cuda" ? " (CPU estimate — faster on a GPU)" : ""}
              {hasExtras ? " · plus time for the AI steps" : ""}
            </p>
          )}
        </div>
      )}

      {!llmOn && (
        <p className={hintCls}>
          Chapters and summaries need an LLM. Point{" "}
          <code className="rounded bg-gray-100 px-1 dark:bg-gray-800">LLM_BASE_URL</code> at Ollama
          or any OpenAI-compatible server. Subtitles and English translation work without it.
        </p>
      )}
    </div>
  );
}
