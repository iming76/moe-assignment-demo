"use client";

import type { BoundingBox, Document } from "@/lib/types";
import { artifactUrl, submitReviewDecision } from "@/lib/api";
import { Button } from "@/components/ui/button";

function cropPathFor(doc: Document, cropId: string): string {
  for (const p of doc.pages) {
    const c = p.crops.find((c) => c.id === cropId);
    if (c) return c.path;
  }
  return "";
}

export default function CropInspector({
  docId,
  selected,
  doc,
  onChanged,
}: {
  docId: string;
  selected: { kind: string; bbox: BoundingBox; label: string; cropId?: string };
  doc: Document;
  onChanged: () => void;
}) {
  const ocr = selected.cropId
    ? doc.pages.flatMap((p) => p.ocr).find((o) => o.cropId === selected.cropId)
    : undefined;
  return (
    <div className="mt-3 border border-[#333] p-2">
      <h3>Crop inspector — {selected.label}</h3>
      <p>
        {selected.kind} @ ({selected.bbox.x}, {selected.bbox.y}) {selected.bbox.width}×{selected.bbox.height}
      </p>
      {selected.cropId && (
        // eslint-disable-next-line @next/next/no-img-element
        <img src={artifactUrl(docId, cropPathFor(doc, selected.cropId))} alt={selected.label} className="max-w-full" />
      )}
      {ocr && (
        <>
          <p>OCR: {ocr.text}</p>
          <p>
            confidence: {ocr.confidence}{" "}
            {ocr.confidence < 0.7 ? "⚑ review required" : ocr.confidence < 0.9 ? "⚑ review recommended" : ""}
          </p>
          <p>validation: {ocr.validationState}; review: {ocr.reviewState}</p>
          {ocr.uncertainty?.length ? <pre>{JSON.stringify(ocr.uncertainty, null, 2)}</pre> : null}
          <div className="mt-2 flex gap-2">
            <Button
              size="sm"
              onClick={async () => { await submitReviewDecision(docId, ocr.cropId, "ocr", "accept"); onChanged(); }}
            >
              accept
            </Button>
            <Button
              size="sm"
              variant="destructive"
              onClick={async () => { await submitReviewDecision(docId, ocr.cropId, "ocr", "reject"); onChanged(); }}
            >
              reject
            </Button>
          </div>
        </>
      )}
    </div>
  );
}
