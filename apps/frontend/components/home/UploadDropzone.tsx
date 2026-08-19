"use client";

import { useState } from "react";
import { FaUpload } from "react-icons/fa";


const ALLOWED_TYPES = ["image/png", "image/jpeg", "image/jpg", "application/pdf"];

export default function UploadDropzone({
  selectedFile,
  onFileSelected,
  onError,
}: {
  selectedFile: File | null;
  onFileSelected: (file: File) => void;
  onError: (message: string) => void;
}) {
  const [isDragging, setIsDragging] = useState(false);

  const selectFile = (file: File) => {
    if (!ALLOWED_TYPES.includes(file.type)) {
      onError("Invalid file type. Please upload a PNG, JPG, or PDF file.");
      return;
    }
    onFileSelected(file);
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

  return (
    <div
      onDragOver={handleDragOver}
      onDragLeave={handleDragLeave}
      onDrop={handleDrop}
      className={`cursor-pointer rounded-lg border-2 border-dashed shadow-none transition-colors max-w-md w-full ${
        isDragging ? "border-fg bg-white/5" : "border-muted"
      }`}
    >
        <input
          type="file"
          id="file-upload"
          accept="image/png,image/jpeg,application/pdf"
          onChange={handleFileSelect}
          className="hidden"
        />
        <label htmlFor="file-upload" className="flex cursor-pointer flex-col items-center gap-4">
          <div className="flex flex-col items-center border border-dashed border-gray-500 p-8 rounded-lg w-full">
            <FaUpload className="text-4xl text-muted-foreground mb-4" />
            <p className="m-0 mb-2 text-lg font-semibold opacity-70">
              {selectedFile
                ? selectedFile.name
                : isDragging
                  ? "Drop your file here"
                  : "Drag & drop or click to upload"}
            </p>
            <p className="m-0 text-sm">Support for PNG, JPG, and PDF files</p>
          </div>
        </label>
    </div>
  );
}
