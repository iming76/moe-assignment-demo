"use client";

import type { BoundingBox, DocumentPage, Paragraph } from "@/lib/types";
import ParagraphDetails from "@/components/review/ParagraphDetails"

export default function ParagraphTree({
  page,
  onSelect,
}: {
  page: DocumentPage;
  selected: { kind: string; bbox: BoundingBox; label: string } | null;
  onSelect: (s: { kind: string; bbox: BoundingBox; label: string; cropId?: string }) => void;
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
        <ParagraphDetails key={p.id} paragraph={p} ocr={page.ocr} onSelect={onSelect} />
      ))}
    </>
  );
}
