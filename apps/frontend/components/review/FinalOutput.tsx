"use client";

import type { Document } from "@/lib/types";

export default function FinalOutput({ doc }: { doc: Document }) {
  const filename = doc.source.originalPath.split("/").pop() ?? doc.source.originalPath;

  const responses = doc.pages
    .filter((p) => p.question || p.answer)
    .map((p) => ({
      question: p.question?.text ?? "",
      response: (p.answer?.paragraphs ?? []).map((par) => par.text).join("\n\n"),
    }));

  const output = {
    results: [
      {
        filename,
        responses,
      },
    ],
  };

  return (
    <div>
      <h3 className="mb-2 font-semibold">Final output</h3>
      <pre className="whitespace-pre-wrap break-words text-xs bg-accent p-4">
        {JSON.stringify(output, null, 2)}
      </pre>
    </div>
  );
}
