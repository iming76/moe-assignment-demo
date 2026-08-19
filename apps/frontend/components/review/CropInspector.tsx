"use client";

import type { BoundingBox, Document } from "@/lib/types";
import { artifactUrl } from "@/lib/api";
import { IoIosExpand } from "react-icons/io";
import {
  Dialog,
  DialogContent,
  DialogTitle,
  DialogTrigger,
} from "@/components/ui/dialog";
import { Label } from "@/components/ui/label";

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
  const labelClass = "text-xs text-gray-500 font-mono mr-2";

  if (!selected.label.includes("_line")) return null;

  const ocr = selected.cropId
    ? doc.pages.flatMap((p) => p.ocr).find((o) => o.cropId === selected.cropId)
    : undefined;

  const body = (
    <ul className="flex flex-col gap-4 text-xs">
      <li className="flex gap-4">
        <span>
          <Label className={labelClass}>position</Label>
          {selected.bbox.x}, {selected.bbox.y}
        </span>
        <span>
          <Label className={labelClass}>size</Label>
          {selected.bbox.width}×{selected.bbox.height}
        </span>
      </li>
      <li>
        {selected.cropId && (
          // eslint-disable-next-line @next/next/no-img-element
          <img
            src={artifactUrl(docId, cropPathFor(doc, selected.cropId))}
            alt={selected.label}
            className="max-w-full"
          />
        )}
      </li>
      {ocr && (
        <>
          <li>
            <Label className={labelClass}>ocr text:</Label>
            <p className="text-base">{ocr.text}</p>
          </li>
          {/* <li>
            <p>
              confidence: {ocr.confidence}{" "}
              {ocr.confidence < 0.7
                ? "⚑ review required"
                : ocr.confidence < 0.9
                  ? "⚑ review recommended"
                  : ""}
            </p>
          </li>
          <li>
            <p>
              validation: {ocr.validationState}; review: {ocr.reviewState}
            </p>
          </li> */}
          {ocr.uncertainty?.length ? (
            <li className="p-3 bg-gray-500/10 rounded-md overflow-auto">
              <pre className="text-xs">
                {JSON.stringify(ocr.uncertainty, null, 2)}
              </pre>
            </li>
          ) : null}
        </>
      )}
    </ul>
  );

  return (
    <Dialog>
      <div className="mt-3 bg-accent p-4 rounded-md">
        <div className="flex items-center justify-between gap-2 mb-2">
          <h3 className="font-semibold">Crop inspector — {selected.label}</h3>
          <DialogTrigger>
            <span>
              <IoIosExpand className="text-lg" />
            </span>
          </DialogTrigger>
        </div>
        {body}
      </div>
      <DialogContent className="sm:max-w-5xl">
        <DialogTitle>Crop inspector — {selected.label}</DialogTitle>
        {body}
      </DialogContent>
    </Dialog>
  );
}
