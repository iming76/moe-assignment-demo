"use client";

import type { BoundingBox, Document, OCRResult, Paragraph } from "@/lib/types";
import { Badge } from "@/components/ui/badge";
import CropInspector from "@/components/review/CropInspector";

export default function ParagraphDetails({
  docId,
  doc,
  paragraph,
  ocr,
  selected,
  onSelect,
  onChanged,
}: {
  docId: string;
  doc: Document;
  paragraph: Paragraph;
  ocr: OCRResult[];
  selected: { kind: string; bbox: BoundingBox; label: string; cropId?: string } | null;
  onSelect: (s: {
    kind: string;
    bbox: BoundingBox;
    label: string;
    cropId?: string;
  }) => void;
  onChanged: () => void;
}) {
  const isSelected =
    !!selected &&
    (selected.label === paragraph.id || paragraph.lines.some((ln) => ln.id === selected.label));
  return (
    <details open={false} className="border-b border-gray-300 border-dotted pb-2">
      <summary
        className="cursor-pointer mb-2 font-semibold"
        onClick={() =>
          onSelect({
            kind: "paragraph",
            bbox: paragraph.bbox,
            label: paragraph.id,
          })
        }
      >
        {paragraph.id} (order {paragraph.order})
      </summary>
      <div className="flex flex-col gap-4 ml-4">
        <div
          onClick={() =>
            onSelect({
              kind: "paragraph",
              bbox: paragraph.bbox,
              label: paragraph.id,
            })
          }
          className="cursor-pointer"
        >
          <p className="leading-loose">{paragraph.text}</p>
        </div>
        <ul className="bg-accent p-4 rounded-md flex flex-col gap-4">
          {paragraph.lines.map((ln) => {
            const o = ocr.find((o) => o.cropId === ln.cropId);
            const low = o && o.confidence < 0.7;
            const mid = o && o.confidence >= 0.7 && o.confidence < 0.9;
            return (
              <li
                key={ln.id}
                onClick={() =>
                  onSelect({
                    kind: "line",
                    bbox: ln.bbox,
                    label: ln.id,
                    cropId: ln.cropId,
                  })
                }
                className="cursor-pointer"
              >
                <div className="flex items-center justify-between gap-2 mb-2">
                  <h4 className={"inline-block font-semibold text-xs"}>
                    {ln.id}
                    <span className="ml-2">
                      {o ? `- ${o.confidence.toFixed(2)}` : ""}
                    </span>
                  </h4>
                  {low && <Badge className="bg-red-500 uppercase">review required</Badge>}
                  {mid && (
                    <Badge className="bg-cyan-500 uppercase">review recommended</Badge>
                  )}
                </div>
                <div className="text-muted-foreground/80 text-sm">
                  {o?.text ? (
                    o.text
                  ) : (
                    <span className="text-muted-foreground italic">
                      No result
                    </span>
                  )}
                </div>
              </li>
            );
          })}
        </ul>
        <div className="mb-4">
          {isSelected && selected && (
            <CropInspector
              docId={docId}
              selected={selected}
              doc={doc}
              onChanged={onChanged}
            />
          )}
        </div>
      </div>
    </details>
  );
}
