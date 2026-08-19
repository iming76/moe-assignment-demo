"use client";

import { Suspense, useCallback, useEffect, useState } from "react";
import { useRouter, useSearchParams } from "next/navigation";
import type { BoundingBox, Document, DocumentPage } from "@/lib/types";
import type { OverlayKey } from "@/constant/overlay";
import { fetchDocument } from "@/lib/api";
import ImageViewer from "@/components/review/ImageViewer";
import ParagraphTree from "@/components/review/ParagraphTree";
import FinalOutput from "@/components/review/FinalOutput";
import { Checkbox } from "@/components/ui/checkbox";
import { Label } from "@/components/ui/label";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import { Card, CardContent } from "@/components/ui/card";

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

  if (!page) {
    return <RedirectHomeCountdown seconds={5} />;
  }
  return (
    <div className="grid grid-cols-3 gap-4">
      <Card className="flex col-span-2 flex-col mb-4">
        <CardContent className="flex flex-col gap-4">
          <div className="flex gap-2">
            {doc && doc.pages.length > 1 && (
              <Select
                value={String(pageIdx)}
                onValueChange={(value) => setPageIdx(Number(value))}
              >
                <SelectTrigger size="sm">
                  <SelectValue />
                </SelectTrigger>
                <SelectContent>
                  {doc.pages.map((p, i) => (
                    <SelectItem key={p.pageNumber} value={String(i)}>
                      page {p.pageNumber}
                    </SelectItem>
                  ))}
                </SelectContent>
              </Select>
            )}
          </div>
          <div className="mb-2 flex gap-3">
            {(Object.keys(overlays) as OverlayKey[]).map((k) => (
              <Label key={k}>
                <Checkbox
                  checked={overlays[k]}
                  onCheckedChange={() =>
                    setOverlays({ ...overlays, [k]: !overlays[k] })
                  }
                />
                {k}
              </Label>
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
        </CardContent>
      </Card>

      <aside className="flex flex-col gap-4">
        <Card className="mb-4">
          <CardContent className="flex flex-col gap-4">
            <div className="flex flex-col">
              <h2 className="text-lg font-semibold">Extraction Output</h2>
              <p className="text-xs">
                Click a paragraph or text to view its extracted region.
              </p>
            </div>
            <div className="flex flex-col max-h-[calc(100vh-12rem)] overflow-auto py-4 px-2">
              {doc && page && (
                <div className="flex flex-col gap-4">
                  <ParagraphTree
                    docId={doc.documentId}
                    doc={doc}
                    page={page}
                    selected={selected}
                    onSelect={setSelected}
                    onChanged={() => load(docId)}
                  />
                  <FinalOutput doc={doc} />
                </div>
              )}
            </div>
          </CardContent>
        </Card>
      </aside>
    </div>
  );
}

function RedirectHomeCountdown({ seconds }: { seconds: number }) {
  const router = useRouter();
  const [remaining, setRemaining] = useState(seconds);

  useEffect(() => {
    if (remaining <= 0) {
      router.push("/");
      return;
    }
    const timer = setTimeout(() => setRemaining((s) => s - 1), 1000);
    return () => clearTimeout(timer);
  }, [remaining, router]);

  return (
    <p>
      Document not found. Redirecting to home in {remaining}s...
    </p>
  );
}
