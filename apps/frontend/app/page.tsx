"use client";

import { useState } from "react";
import { useRouter } from "next/navigation";
import {
  subscribeProgress,
  uploadDocument,
  type ProgressEvent,
} from "@/lib/api";
import UploadDropzone from "@/components/home/UploadDropzone";
import ProgressStages from "@/components/home/ProgressStages";
import { Button } from "@/components/ui/button";
import { Card, CardContent } from "@/components/ui/card";

export default function Home() {
  const [isUploading, setIsUploading] = useState(false);
  const [selectedFile, setSelectedFile] = useState<File | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [currentStage, setCurrentStage] = useState<string | null>(null);
  const [ocrProgress, setOcrProgress] = useState<{
    completed: number;
    total: number;
  } | null>(null);
  const router = useRouter();

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
        const unsubscribe = subscribeProgress(
          result.documentId,
          (event: ProgressEvent) => {
            if (event.state === "ERROR") {
              unsubscribe();
              reject(new Error(event.detail || "Processing failed."));
              return;
            }
            setCurrentStage(event.state);
            setOcrProgress(
              event.completed != null && event.total != null
                ? { completed: event.completed, total: event.total }
                : null,
            );
            if (event.state === "REVIEW_REQUIRED") {
              unsubscribe();
              resolve();
            }
          },
        );
      });
      setSelectedFile(null);
      router.push(`/review?id=${result.documentId}`);
    } catch (err) {
      setError(
        err instanceof Error ? err.message : "Upload failed. Please try again.",
      );
      setIsUploading(false);
    }
  };

  return (
    <div className="flex flex-col items-center justify-center gap-4 p-4 w-full">
      <Card className="w-full max-w-lg">
        <CardContent className="p-12 text-center">
          {!isUploading && (
            <UploadDropzone
              selectedFile={selectedFile}
              onFileSelected={(file) => {
                setError(null);
                setSelectedFile(file);
              }}
              onError={setError}
            />
          )}
          {error && <p className="mt-4 rounded p-4 text-[#ef476f]">{error}</p>}
          {isUploading && (
            <ProgressStages
              currentStage={currentStage}
              ocrProgress={ocrProgress}
            />
          )}
          {!isUploading && (
            <Button
              type="button"
              onClick={handleSubmit}
              className="mt-6 w-full"
              disabled={isUploading || !selectedFile}
            >
              Submit
            </Button>
          )}
        </CardContent>
      </Card>
    </div>
  );
}
