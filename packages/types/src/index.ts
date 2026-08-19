/**
 * @moe-research/types
 *
 * Single shared contract between the Python backend and the Next.js
 * frontend. Mirrors backend/schemas.py 1:1 — any JSON shape change must
 * land here first.
 */

export interface BoundingBox {
  x: number;
  y: number;
  width: number;
  height: number;
}

export interface PageImage {
  pageNumber: number;
  path: string;
  width: number;
  height: number;
  dpi: number;
}
