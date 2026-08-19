"use client";

import { Suspense, useCallback, useEffect, useRef, useState } from "react";
import { useSearchParams } from "next/navigation";
import type {
  BoundingBox,
  Document,
  DocumentPage,
  Paragraph,
} from "../../lib/types";
import {
  approveDocument,
  artifactUrl,
  fetchDocument,
  submitReviewDecision,
} from "@/lib/api";

type OverlayKey =
  | "question"
  | "answer"
  | "paragraphs"
  | "lines"
  | "highlights";

const OVERLAY_COLORS: Record<OverlayKey, string> = {
  question: "#4cc9f0",
  answer: "#80ed99",
  paragraphs: "#f9c74f",
  lines: "#90be6d",
  highlights: "#ffd60a",
};

const OVERLAY_TEXT_CLASSES: Record<OverlayKey, string> = {
  question: "text-[#4cc9f0]",
  answer: "text-[#80ed99]",
  paragraphs: "text-[#f9c74f]",
  lines: "text-[#90be6d]",
  highlights: "text-[#ffd60a]",
};

export default function ReviewPage() {
  return (
    <Suspense fallback={null}>
      <ReviewPageInner />
    </Suspense>
  );
}

function ReviewPageInner() {
  const searchParams = useSearchParams();
  const docId = searchParams.get("id") ?? "";
  const [doc, setDoc] = useState<Document | null>(null);
  const [error, setError] = useState("");
  const [pageIdx, setPageIdx] = useState(0);
  const [overlays, setOverlays] = useState<Record<OverlayKey, boolean>>({
    question: true,
    answer: true,
    paragraphs: true,
    lines: false,
    highlights: true,
  });
  const [selected, setSelected] = useState<{
    kind: string;
    bbox: BoundingBox;
    label: string;
    cropId?: string;
  } | null>(null);

  const load = useCallback(async (id: string) => {
    try {
      setError("");
      setDoc(await fetchDocument(id));
    } catch (e) {
      setError(String(e));
    }
  }, []);

  useEffect(() => {
    if (docId) load(docId);
  }, [docId, load]);

  const page: DocumentPage | undefined = doc?.pages[pageIdx];

  return (
    <main className="flex h-screen gap-4 p-4">
      <section className="flex flex-2 flex-col">
        <header className="mb-2 flex gap-2">
          {doc && <span>state: {doc.state}</span>}
          {doc && doc.pages.length > 1 && (
            <select
              value={pageIdx}
              onChange={(e) => setPageIdx(Number(e.target.value))}
            >
              {doc.pages.map((p, i) => (
                <option key={p.pageNumber} value={i}>
                  page {p.pageNumber}
                </option>
              ))}
            </select>
          )}
        </header>
        <div className="mb-2 flex gap-1.5">
          {(Object.keys(overlays) as OverlayKey[]).map((k) => (
            <label key={k} className={OVERLAY_TEXT_CLASSES[k]}>
              <input
                type="checkbox"
                checked={overlays[k]}
                onChange={() => setOverlays({ ...overlays, [k]: !overlays[k] })}
              />
              {k}
            </label>
          ))}
        </div>
        {page && doc && (
          <ImageViewer
            docId={doc.documentId}
            page={page}
            overlays={overlays}
            selected={selected}
            onSelect={setSelected}
          />
        )}
        {error && <p className="text-[#ef476f]">{error}</p>}
      </section>

      <aside className="flex-1 overflow-auto">
        {doc && page && (
          <ParagraphTree
            doc={doc}
            page={page}
            selected={selected}
            onSelect={setSelected}
            onCorrected={() => load(docId)}
            onApproved={() => load(docId)}
          />
        )}
        {selected && doc && (
          <CropInspector docId={doc.documentId} selected={selected} doc={doc} onChanged={() => load(docId)} />
        )}
      </aside>
    </main>
  );
}

function ImageViewer({
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
      className="relative flex-1 overflow-hidden border border-[#333]"
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
        <svg viewBox={`0 0 ${w} ${h}`} width={w} height={h} className="pointer-events-none absolute top-0 left-0">
          {boxes.map((b, i) => (
            <g key={i} className="pointer-events-auto cursor-pointer" onClick={() => onSelect({ kind: b.kind, bbox: b.bbox, label: b.label, cropId: b.cropId })}>
              <rect
                x={b.bbox.x}
                y={b.bbox.y}
                width={b.bbox.width}
                height={b.bbox.height}
                fill="transparent"
                stroke={OVERLAY_COLORS[b.key]}
                strokeWidth={selected?.label === b.label ? 4 : 2}
              />
            </g>
          ))}
          {selected && (
            <rect x={selected.bbox.x} y={selected.bbox.y} width={selected.bbox.width} height={selected.bbox.height} fill="none" stroke="#ffffff" strokeWidth={3} strokeDasharray="6 3" />
          )}
        </svg>
      </div>
    </div>
  );
}

function CropInspector({
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
  const cropPath = `crops/${""}`;
  void cropPath;
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
          <button onClick={async () => { await submitReviewDecision(docId, ocr.cropId, "ocr", "accept"); onChanged(); }}>accept</button>{" "}
          <button onClick={async () => { await submitReviewDecision(docId, ocr.cropId, "ocr", "reject"); onChanged(); }}>reject</button>
        </>
      )}
    </div>
  );
}

function cropPathFor(doc: Document, cropId: string): string {
  for (const p of doc.pages) {
    const c = p.crops.find((c) => c.id === cropId);
    if (c) return c.path;
  }
  return "";
}

function ParagraphTree({
  doc,
  page,
  selected,
  onSelect,
  onCorrected,
  onApproved,
}: {
  doc: Document;
  page: DocumentPage;
  selected: { kind: string; bbox: BoundingBox; label: string } | null;
  onSelect: (s: { kind: string; bbox: BoundingBox; label: string; cropId?: string }) => void;
  onCorrected: () => void;
  onApproved: () => void;
}) {
  const [edits, setEdits] = useState<Record<string, string>>({});
  return (
    <div>
      <h2>Paragraph navigation</h2>
      {page.question && (
        <p>
          <b>Question:</b> {page.question.text}
        </p>
      )}
      {page.answer?.paragraphs.map((p: Paragraph) => (
        <details key={p.id} open>
          <summary
            className="cursor-pointer text-[#f9c74f]"
            onClick={() => onSelect({ kind: "paragraph", bbox: p.bbox, label: p.id })}
          >
            {p.id} (order {p.order})
          </summary>
          <p>{p.text}</p>
          {p.lines.map((ln) => {
            const ocr = page.ocr.find((o) => o.cropId === ln.cropId);
            const low = ocr && ocr.confidence < 0.7;
            const mid = ocr && ocr.confidence >= 0.7 && ocr.confidence < 0.9;
            return (
              <div key={ln.id} className="mb-1.5 ml-3">
                <span
                  className={`cursor-pointer ${low ? "text-[#ef476f]" : mid ? "text-[#ffd60a]" : "text-[#90be6d]"}`}
                  onClick={() => onSelect({ kind: "line", bbox: ln.bbox, label: ln.id, cropId: ln.cropId })}
                >
                  {ln.id}
                </span>{" "}
                {ocr?.text} {ocr ? `(${ocr.confidence.toFixed(2)})` : ""}
                {low && " ⚑ review required"}
                {mid && " ⚑ review recommended"}
                <input
                  placeholder="correction"
                  value={edits[ln.id] ?? ""}
                  onChange={(e) => setEdits({ ...edits, [ln.id]: e.target.value })}
                  className="ml-2"
                />
                <button
                  onClick={async () => {
                    await submitReviewDecision(doc.documentId, ln.cropId, "ocr", "correct", edits[ln.id] ?? "");
                    onCorrected();
                  }}
                >
                  save
                </button>
              </div>
            );
          })}
        </details>
      ))}
      <button
        className="mt-3"
        onClick={async () => {
          await approveDocument(doc.documentId);
          onApproved();
        }}
      >
        Approve &amp; export
      </button>
    </div>
  );
}
