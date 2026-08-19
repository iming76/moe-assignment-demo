"use client";

import { useState } from "react";
import { useRouter } from "next/navigation";
import { subscribeProgress, uploadDocument, type ProgressEvent } from "@/lib/api";

const STAGES = [
  "NORMALIZED",
  "QUESTION_DETECTED",
  "ANSWER_DETECTED",
  "PARAGRAPHS_DETECTED",
  "CROPS_GENERATED",
  "OCR_PROCESSING",
  "MARKUP_RECONSTRUCTION",
] as const;

export default function Home() {
  const [isDragging, setIsDragging] = useState(false);
  const [isUploading, setIsUploading] = useState(false);
  const [selectedFile, setSelectedFile] = useState<File | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [currentStage, setCurrentStage] = useState<string | null>(null);
  const [ocrProgress, setOcrProgress] = useState<{ completed: number; total: number } | null>(null);
  const router = useRouter();

  const allowedTypes = ["image/png", "image/jpeg", "image/jpg", "application/pdf"];

  const selectFile = (file: File) => {
    if (!allowedTypes.includes(file.type)) {
      setError("Invalid file type. Please upload a PNG, JPG, or PDF file.");
      return;
    }
    setError(null);
    setSelectedFile(file);
  };

  const handleDragOver = (e: React.DragEvent) => {
    e.preventDefault();
    setIsDragging(true);
  };

  const handleDragLeave = (e: React.DragEvent) => {
    e.preventDefault();
    setIsDragging(false);
  };

  const handleDrop = (e: React.DragEvent) => {
    e.preventDefault();
    setIsDragging(false);
    const file = e.dataTransfer.files[0];
    if (file) selectFile(file);
  };

  const handleFileSelect = (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (file) selectFile(file);
  };

  const handleSubmit = () => {
    if (selectedFile) handleUpload(selectedFile);
  };

  const handleUpload = async (file: File) => {
    setIsUploading(true);
    setError(null);
    setCurrentStage(null);
    setOcrProgress(null);

    try {
      const result = await uploadDocument(file);
      await new Promise<void>((resolve, reject) => {
        const unsubscribe = subscribeProgress(result.documentId, (event: ProgressEvent) => {
          if (event.state === "ERROR") {
            unsubscribe();
            reject(new Error(event.detail || "Processing failed."));
            return;
          }
          setCurrentStage(event.state);
          setOcrProgress(
            event.completed != null && event.total != null
              ? { completed: event.completed, total: event.total }
              : null
          );
          if (event.state === "REVIEW_REQUIRED") {
            unsubscribe();
            resolve();
          }
        });
      });
      setSelectedFile(null);
      router.push(`/review?id=${result.documentId}`);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Upload failed. Please try again.");
      setIsUploading(false);
    }
  };

  return (
    <main className="mx-auto max-w-[600px] p-8">
      <h1>Handwritten OCR</h1>
      <p className="mb-8 text-muted">Upload an image or PDF to start the pipeline</p>

      {!isUploading && (
        <div
          onDragOver={handleDragOver}
          onDragLeave={handleDragLeave}
          onDrop={handleDrop}
          className={`cursor-pointer rounded-lg border-2 border-dashed p-12 text-center transition-colors ${
            isDragging ? "border-fg bg-white/5" : "border-muted bg-transparent"
          }`}
        >
          <input
            type="file"
            id="file-upload"
            accept="image/png,image/jpeg,application/pdf"
            onChange={handleFileSelect}
            className="hidden"
          />
          <label
            htmlFor="file-upload"
            className="flex cursor-pointer flex-col items-center gap-4"
          >
            <div>
              <p className="m-0 mb-2 text-xl font-bold">
                {selectedFile
                  ? selectedFile.name
                  : isDragging
                    ? "Drop your file here"
                    : "Drag & drop or click to upload"}
              </p>
              <p className="m-0 text-sm text-muted">
                Support for PNG, JPG, and PDF files
              </p>
            </div>
          </label>
        </div>
      )}

      {!isUploading && selectedFile && (
        <button
          type="button"
          onClick={handleSubmit}
          className="mt-6 w-full cursor-pointer rounded-lg border-none bg-fg p-3.5 text-base font-bold text-bg"
        >
          Submit
        </button>
      )}

      {error && (
        <p className="mt-4 rounded bg-[#ef476f]/10 p-4 text-[#ef476f]">{error}</p>
      )}

      {isUploading && (
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
      )}
    </main>
  );
}
