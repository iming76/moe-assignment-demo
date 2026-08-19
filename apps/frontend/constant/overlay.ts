export type OverlayKey = "question" | "answer" | "paragraphs" | "lines" | "highlights";

export const OVERLAY_COLORS: Record<OverlayKey, string> = {
  question: "#4cc9f0",
  answer: "#80ed99",
  paragraphs: "#f9c74f",
  lines: "#90be6d",
  highlights: "#ffd60a",
};

export const OVERLAY_TEXT_CLASSES: Record<OverlayKey, string> = {
  question: "text-[#4cc9f0]",
  answer: "text-[#80ed99]",
  paragraphs: "text-[#f9c74f]",
  lines: "text-[#90be6d]",
  highlights: "text-[#ffd60a]",
};
