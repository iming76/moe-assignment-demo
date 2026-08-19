export const STAGES = [
  "NORMALIZED",
  "QUESTION_DETECTED",
  "ANSWER_DETECTED",
  "PARAGRAPHS_DETECTED",
  "CROPS_GENERATED",
  "OCR_PROCESSING",
  "MARKUP_RECONSTRUCTION",
] as const;

export default function ProgressStages({
  currentStage,
  ocrProgress,
}: {
  currentStage: string | null;
  ocrProgress: { completed: number; total: number } | null;
}) {
  return (
    <ul className="mt-6 list-none p-0">
      {STAGES.map((stage) => {
        const reachedIndex = currentStage ? STAGES.indexOf(currentStage as (typeof STAGES)[number]) : -1;
        const done = reachedIndex >= STAGES.indexOf(stage);
        return (
          <li
            key={stage}
            className={`flex items-center gap-3 py-1.5 ${done ? "text-fg" : "text-muted"}`}
          >
            <span
              aria-hidden
              className={`inline-block h-4 w-4 shrink-0 rounded-[3px] border border-muted ${
                done ? "bg-fg" : "bg-transparent"
              }`}
            />
            {stage.replace(/_/g, " ")}
            {stage === "OCR_PROCESSING" && currentStage === "OCR_PROCESSING" && ocrProgress && (
              <span className="text-[0.8125rem] text-muted">
                ({ocrProgress.completed}/{ocrProgress.total})
              </span>
            )}
          </li>
        );
      })}
    </ul>
  );
}
