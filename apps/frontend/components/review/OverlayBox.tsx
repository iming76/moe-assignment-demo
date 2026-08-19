import type { BoundingBox } from "@/lib/types";

export default function OverlayBox({
  bbox,
  fill,
  fillOpacity,
  onClick,
}: {
  bbox: BoundingBox;
  fill: string;
  fillOpacity: number;
  onClick?: () => void;
}) {
  const rect = (
    <rect x={bbox.x} y={bbox.y} width={bbox.width} height={bbox.height} fill={fill} fillOpacity={fillOpacity} stroke="none" />
  );

  if (!onClick) return rect;

  return (
    <g className="pointer-events-auto cursor-pointer" onClick={onClick}>
      {rect}
    </g>
  );
}
