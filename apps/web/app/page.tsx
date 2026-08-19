import type { PageImage } from "@moe-research/types";

export default function Home() {
  // Smoke-test the shared contract at build time: if packages/types drifts,
  // this import fails the web build.
  const placeholder: PageImage = {
    pageNumber: 1,
    path: "rendered/page_001.png",
    width: 0,
    height: 0,
    dpi: 0,
  };

  return (
    <main style={{ padding: "2rem" }}>
      <h1>Handwritten Script Review</h1>
      <p style={{ color: "var(--muted)" }}>
        Review frontend coming soon. Shared contract loaded:{" "}
        <code>{placeholder.path}</code>
      </p>
    </main>
  );
}
