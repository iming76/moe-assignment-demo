import { MdCheckBoxOutlineBlank, MdCheckBox } from "react-icons/md";


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
    <ul className="list-none p-0">
      {STAGES.map((stage) => {
        const reachedIndex = currentStage ? STAGES.indexOf(currentStage as (typeof STAGES)[number]) : -1;
        const done = reachedIndex >= STAGES.indexOf(stage);
        return (
          <li
            key={stage}
            className={`flex items-center gap-3 py-1.5 ${done ? "opacity-90" : "opacity-50"}`}
          >
            {done ? (
              <MdCheckBox className="text-green-500" />
            ) : (
              <MdCheckBoxOutlineBlank className="text-gray-400" />
            )}
            {stage.replace(/_/g, " ")}
            {stage === "OCR_PROCESSING" && currentStage === "OCR_PROCESSING" && ocrProgress && (
              <span className="text-[0.8125rem]">
                ({ocrProgress.completed}/{ocrProgress.total})
              </span>
            )}
          </li>
        );
      })}
    </ul>
  );
}
