import { useCallback, useEffect, useRef, useState } from "react";
import { formatBytes, formatDuration } from "../lib/format";

interface Props {
  file: File | null;
  onSelect: (file: File | null) => void;
  onMeta?: (duration: number | null) => void;
  maxMb: number;
  disabled?: boolean;
}

interface MediaMeta {
  duration?: number;
  width?: number;
  height?: number;
}

export function Dropzone({ file, onSelect, onMeta, maxMb, disabled }: Props) {
  const inputRef = useRef<HTMLInputElement>(null);
  const [dragging, setDragging] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [meta, setMeta] = useState<MediaMeta | null>(null);

  // Read media metadata (duration / resolution) client-side once a file is picked.
  useEffect(() => {
    setMeta(null);
    if (!file) {
      onMeta?.(null);
      return;
    }
    const url = URL.createObjectURL(file);
    const el = document.createElement("video");
    el.preload = "metadata";
    el.onloadedmetadata = () => {
      setMeta({ duration: el.duration, width: el.videoWidth, height: el.videoHeight });
      onMeta?.(Number.isFinite(el.duration) ? el.duration : null);
      URL.revokeObjectURL(url);
    };
    el.onerror = () => {
      setMeta({}); // format the browser can't probe — still show type/size
      onMeta?.(null);
      URL.revokeObjectURL(url);
    };
    el.src = url;
  }, [file, onMeta]);

  const pick = useCallback(
    (f: File | null) => {
      setError(null);
      if (f && maxMb > 0 && f.size > maxMb * 1024 * 1024) {
        setError(`That file is ${formatBytes(f.size)} — over the ${maxMb} MB limit.`);
        return;
      }
      onSelect(f);
    },
    [maxMb, onSelect],
  );

  const sizeLabel =
    maxMb <= 0
      ? "any size"
      : maxMb >= 1024
        ? `up to ${Math.round(maxMb / 1024)} GB`
        : `up to ${maxMb} MB`;

  return (
    <div>
      <div
        onClick={() => !disabled && inputRef.current?.click()}
        onDragOver={(e) => {
          e.preventDefault();
          if (!disabled) setDragging(true);
        }}
        onDragLeave={() => setDragging(false)}
        onDrop={(e) => {
          e.preventDefault();
          setDragging(false);
          if (!disabled) pick(e.dataTransfer.files?.[0] ?? null);
        }}
        className={[
          "flex cursor-pointer flex-col items-center justify-center rounded-lg border border-dashed px-6 py-10 text-center transition",
          dragging
            ? "border-gray-900 bg-gray-50 dark:border-gray-300 dark:bg-gray-800"
            : "border-gray-300 hover:border-gray-400 dark:border-gray-700 dark:hover:border-gray-600",
          disabled ? "pointer-events-none opacity-50" : "",
        ].join(" ")}
      >
        <input
          ref={inputRef}
          type="file"
          accept="audio/*,video/*,.mkv,.mka,.m4a,.webm"
          className="hidden"
          onChange={(e) => pick(e.target.files?.[0] ?? null)}
        />
        <svg
          className="mb-3 h-8 w-8 text-gray-400 dark:text-gray-500"
          fill="none"
          viewBox="0 0 24 24"
          stroke="currentColor"
          strokeWidth={1.5}
        >
          <path
            strokeLinecap="round"
            strokeLinejoin="round"
            d="M3 16.5v2.25A2.25 2.25 0 0 0 5.25 21h13.5A2.25 2.25 0 0 0 21 18.75V16.5M16.5 12 12 16.5m0 0L7.5 12m4.5 4.5V3"
          />
        </svg>
        {file ? (
          <p className="font-medium text-gray-900 dark:text-gray-100">{file.name}</p>
        ) : (
          <div>
            <p className="font-medium text-gray-700 dark:text-gray-300">
              Drop a video or audio file, or click to browse
            </p>
            <p className="mt-1 text-sm text-gray-400 dark:text-gray-500">
              MP4, MKV, MOV, MP3, WAV, M4A… {sizeLabel}
            </p>
          </div>
        )}
      </div>

      {file && (
        <div className="mt-2 flex flex-wrap items-center gap-x-3 gap-y-1 text-xs text-gray-500 dark:text-gray-400">
          <span className="font-medium text-gray-600 dark:text-gray-300">
            {file.type || file.name.split(".").pop()?.toUpperCase() || "file"}
          </span>
          <span>{formatBytes(file.size)}</span>
          {meta?.duration ? <span>· {formatDuration(meta.duration)}</span> : null}
          {meta?.width ? (
            <span>
              · {meta.width}×{meta.height}
            </span>
          ) : null}
          {!disabled && (
            <button
              onClick={() => onSelect(null)}
              className="ml-auto text-gray-500 hover:text-gray-900 dark:hover:text-gray-200"
            >
              Choose a different file
            </button>
          )}
        </div>
      )}
      {error && <p className="mt-2 text-sm text-red-600 dark:text-red-400">{error}</p>}
    </div>
  );
}
