export const SOURCE_LANGUAGES: { code: string; label: string }[] = [
  { code: "auto", label: "Auto-detect" },
  { code: "en", label: "English" },
  { code: "es", label: "Spanish" },
  { code: "fr", label: "French" },
  { code: "de", label: "German" },
  { code: "it", label: "Italian" },
  { code: "pt", label: "Portuguese" },
  { code: "nl", label: "Dutch" },
  { code: "ru", label: "Russian" },
  { code: "ja", label: "Japanese" },
  { code: "ko", label: "Korean" },
  { code: "zh", label: "Chinese" },
  { code: "ar", label: "Arabic" },
  { code: "hi", label: "Hindi" },
];

export const WHISPER_MODELS: string[] = ["tiny", "base", "small", "medium", "large-v3"];

export const WHISPER_COMPUTE_TYPES: string[] = [
  "auto",
  "int8",
  "int8_float16",
  "float16",
  "float32",
];

// Rough audio-seconds processed per wall-clock second on CPU (int8). GPU is far faster.
export const WHISPER_REALTIME_CPU: Record<string, number> = {
  tiny: 12,
  base: 7,
  small: 3.5,
  medium: 1.7,
  "large-v3": 0.9,
};

export function estimateTranscriptionSeconds(
  durationSec: number,
  model: string,
  device: string,
): number {
  const rt = WHISPER_REALTIME_CPU[model] ?? 5;
  const factor = device === "cuda" ? rt * 10 : rt;
  return durationSec / factor + 5; // + a little fixed overhead
}

export const CHAPTER_COUNTS: { label: string; value: number | null }[] = [
  { label: "Auto", value: null },
  { label: "~5", value: 5 },
  { label: "~8", value: 8 },
  { label: "~12", value: 12 },
  { label: "~20", value: 20 },
];

export const TARGET_LANGUAGES: string[] = [
  "English",
  "Spanish",
  "French",
  "German",
  "Italian",
  "Portuguese",
  "Dutch",
  "Russian",
  "Japanese",
  "Korean",
  "Chinese (Simplified)",
  "Arabic",
  "Hindi",
];
