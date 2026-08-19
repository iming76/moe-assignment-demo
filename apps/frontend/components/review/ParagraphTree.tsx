"use client";

import type { BoundingBox, Document, DocumentPage, Paragraph } from "@/lib/types";
import ParagraphDetails from "@/components/review/ParagraphDetails"

export default function ParagraphTree({
  docId,
  doc,
  page,
  selected,
  onSelect,
  onChanged,
}: {
  docId: string;
  doc: Document;
  page: DocumentPage;
  selected: { kind: string; bbox: BoundingBox; label: string; cropId?: string } | null;
  onSelect: (s: { kind: string; bbox: BoundingBox; label: string; cropId?: string }) => void;
  onChanged: () => void;
}) {
  return (
    <>
      <div>
        {page.question && (
          <p>
            <b>Question:</b> {page.question.text}
          </p>
        )}
      </div>
      {page.answer?.paragraphs.map((p: Paragraph) => (
        <ParagraphDetails
          key={p.id}
          docId={docId}
          doc={doc}
          paragraph={p}
          ocr={page.ocr}
          selected={selected}
          onSelect={onSelect}
          onChanged={onChanged}
        />
      ))}
    </>
  );
}
