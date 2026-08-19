"use client";

import { useRef, useState } from "react";
import type { BoundingBox, DocumentPage } from "@/lib/types";
import { artifactUrl } from "@/lib/api";
import { OVERLAY_COLORS, type OverlayKey } from "../../constant/overlay";
import OverlayBox from "./OverlayBox";

export default function ImageViewer({
  docId,
  page,
  overlays,
  selected,
  onSelect,
}: {
  docId: string;
  page: DocumentPage;
  overlays: Record<OverlayKey, boolean>;
  selected: { bbox: BoundingBox; label: string } | null;
  onSelect: (s: { kind: string; bbox: BoundingBox; label: string; cropId?: string }) => void;
}) {
  const [scale, setScale] = useState(0.6);
  const [offset, setOffset] = useState({ x: 0, y: 0 });
  const drag = useRef<{ x: number; y: number } | null>(null);

  const w = page.image.width;
  const h = page.image.height;

  const boxes: { key: OverlayKey; bbox: BoundingBox; label: string; kind: string; cropId?: string }[] = [];
  if (overlays.question && page.question)
    boxes.push({ key: "question", bbox: page.question.bbox, label: page.question.id, kind: "question", cropId: page.question.id });
  if (overlays.answer && page.answer)
    boxes.push({ key: "answer", bbox: page.answer.bbox, label: "answer", kind: "answer" });
  if (page.answer) {
    for (const p of page.answer.paragraphs) {
      if (overlays.paragraphs)
        boxes.push({ key: "paragraphs", bbox: p.bbox, label: p.id, kind: "paragraph", cropId: p.id });
      if (overlays.lines)
        for (const ln of p.lines)
          boxes.push({ key: "lines", bbox: ln.bbox, label: ln.id, kind: "line", cropId: ln.cropId });
    }
  }
  if (overlays.highlights)
    for (const hl of page.highlights)
      if (hl.bbox) boxes.push({ key: "highlights", bbox: hl.bbox, label: hl.id, kind: "highlight" });

  return (
    <div
      className="relative bg-accent max-h-[calc(100vh-12rem)] overflow-hidden"
      onWheel={(e) => setScale((s) => Math.min(3, Math.max(0.2, s - e.deltaY / 1000)))}
      onMouseDown={(e) => (drag.current = { x: e.clientX - offset.x, y: e.clientY - offset.y })}
      onMouseMove={(e) => {
        if (drag.current)
          setOffset({ x: e.clientX - drag.current.x, y: e.clientY - drag.current.y });
      }}
      onMouseUp={() => (drag.current = null)}
      onMouseLeave={() => (drag.current = null)}
    >
      <div
        className="origin-top-left"
        style={{ transform: `translate(${offset.x}px, ${offset.y}px) scale(${scale})`, width: w, height: h }}
      >
        {/* eslint-disable-next-line @next/next/no-img-element */}
        <img src={artifactUrl(docId, page.image.path)} alt="rendered page" width={w} height={h} draggable={false} />
        <svg
          viewBox={`0 0 ${w} ${h}`}
          width={w}
          height={h}
          className="pointer-events-none absolute top-0 left-0"
          style={{ mixBlendMode: "multiply" }}
        >
          {boxes.map((b, i) => (
            <OverlayBox
              key={i}
              bbox={b.bbox}
              fill={OVERLAY_COLORS[b.key]}
              fillOpacity={selected?.label === b.label ? 0.6 : 0.35}
              onClick={() => onSelect({ kind: b.kind, bbox: b.bbox, label: b.label, cropId: b.cropId })}
            />
          ))}
          {selected && <OverlayBox bbox={selected.bbox} fill="#000000" fillOpacity={0.3} />}
        </svg>
      </div>
    </div>
  );
}
