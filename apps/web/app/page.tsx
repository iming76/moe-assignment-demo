"use client";

import { useState } from "react";
import { useRouter } from "next/navigation";
import { uploadDocument } from "@/lib/api";

export default function Home() {
  const [isDragging, setIsDragging] = useState(false);
  const [isUploading, setIsUploading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const router = useRouter();

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
    if (file) handleUpload(file);
  };

  const handleFileSelect = (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (file) handleUpload(file);
  };

  const handleUpload = async (file: File) => {
    // Validate file type
    const allowedTypes = ["image/png", "image/jpeg", "image/jpg", "application/pdf"];
    if (!allowedTypes.includes(file.type)) {
      setError("Invalid file type. Please upload a PNG, JPG, or PDF file.");
      return;
    }

    setIsUploading(true);
    setError(null);

    try {
      const result = await uploadDocument(file);
      router.push(`/review/${result.documentId}`);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Upload failed. Please try again.");
    } finally {
      setIsUploading(false);
    }
  };

  return (
    <main style={{ padding: "2rem", maxWidth: "600px", margin: "0 auto" }}>
      <h1>Handwritten Script OCR</h1>
      <p style={{ color: "var(--muted)", marginBottom: "2rem" }}>
        Upload an image or PDF to start the pipeline
      </p>

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
          <div
            style={{
              width: "80px",
              height: "80px",
              borderRadius: "50%",
              backgroundColor: "var(--muted)",
              display: "flex",
              alignItems: "center",
              justifyContent: "center",
              fontSize: "2rem",
            }}
          >
            📤
          </div>
          <div>
            <p style={{ fontSize: "1.25rem", fontWeight: "bold", margin: "0 0 0.5rem 0" }}>
              {isDragging ? "Drop your file here" : "Drag & drop or click to upload"}
            </p>
            <p style={{ color: "var(--muted)", margin: 0, fontSize: "0.875rem" }}>
              Support for PNG, JPG, and PDF files
            </p>
          </div>
        </label>
      </div>

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
        <p style={{ color: "var(--muted)", marginTop: "1rem" }}>
          Processing document...
        </p>
      )}
    </main>
  );
}