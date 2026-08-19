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
    <main style={{ padding: "2rem", maxWidth: "600px", margin: "0 auto" }}>
      <h1>Handwritten Script OCR</h1>
      <p style={{ color: "var(--muted)", marginBottom: "2rem" }}>
        Upload an image or PDF to start the pipeline
      </p>

      {!isUploading && (
        <div
          onDragOver={handleDragOver}
          onDragLeave={handleDragLeave}
          onDrop={handleDrop}
          style={{
            border: isDragging ? "2px dashed var(--fg)" : "2px dashed var(--muted)",
            borderRadius: "8px",
            padding: "3rem 2rem",
            textAlign: "center",
            backgroundColor: isDragging ? "rgba(255, 255, 255, 0.05)" : "transparent",
            transition: "border-color 0.2s, background-color 0.2s",
            cursor: "pointer",
          }}
        >
          <input
            type="file"
            id="file-upload"
            accept="image/png,image/jpeg,application/pdf"
            onChange={handleFileSelect}
            style={{ display: "none" }}
          />
          <label
            htmlFor="file-upload"
            style={{
              cursor: "pointer",
              display: "flex",
              flexDirection: "column",
              alignItems: "center",
              gap: "1rem",
            }}
          >
            <div>
              <p style={{ fontSize: "1.25rem", fontWeight: "bold", margin: "0 0 0.5rem 0" }}>
                {selectedFile
                  ? selectedFile.name
                  : isDragging
                    ? "Drop your file here"
                    : "Drag & drop or click to upload"}
              </p>
              <p style={{ color: "var(--muted)", margin: 0, fontSize: "0.875rem" }}>
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
          style={{
            marginTop: "1.5rem",
            width: "100%",
            padding: "0.875rem",
            borderRadius: "8px",
            border: "none",
            backgroundColor: "var(--fg)",
            color: "var(--bg)",
            fontSize: "1rem",
            fontWeight: "bold",
            cursor: "pointer",
          }}
        >
          Submit
        </button>
      )}

      {error && (
        <p
          style={{
            color: "#ef476f",
            backgroundColor: "rgba(239, 71, 111, 0.1)",
            padding: "1rem",
            borderRadius: "4px",
            marginTop: "1rem",
          }}
        >
          {error}
        </p>
      )}

      {isUploading && (
        <ul style={{ listStyle: "none", padding: 0, marginTop: "1.5rem" }}>
          {STAGES.map((stage) => {
            const reachedIndex = currentStage ? STAGES.indexOf(currentStage as (typeof STAGES)[number]) : -1;
            const done = reachedIndex >= STAGES.indexOf(stage);
            return (
              <li
                key={stage}
                style={{
                  display: "flex",
                  alignItems: "center",
                  gap: "0.75rem",
                  padding: "0.375rem 0",
                  color: done ? "var(--fg)" : "var(--muted)",
                }}
              >
                <span
                  aria-hidden
                  style={{
                    display: "inline-block",
                    width: "1rem",
                    height: "1rem",
                    borderRadius: "3px",
                    border: "1px solid var(--muted)",
                    backgroundColor: done ? "var(--fg)" : "transparent",
                    flexShrink: 0,
                  }}
                />
                {stage.replace(/_/g, " ")}
                {stage === "OCR_PROCESSING" && currentStage === "OCR_PROCESSING" && ocrProgress && (
                  <span style={{ color: "var(--muted)", fontSize: "0.8125rem" }}>
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