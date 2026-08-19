"use client";

import { useEffect, useState } from "react";
import { CgDarkMode } from "react-icons/cg";
import Link from "next/link";

export default function Navbar() {
  const [isDark, setIsDark] = useState(false);

  useEffect(() => {
    setIsDark(document.documentElement.classList.contains("dark"));
  }, []);

  function toggleDarkMode() {
    const next = !isDark;
    document.documentElement.classList.toggle("dark", next);
    localStorage.setItem("theme", next ? "dark" : "light");
    setIsDark(next);
  }

  return (
    <nav className="flex items-center justify-between p-4 fixed top-0 left-0 right-0 z-50 bg-background/80 backdrop-blur-md border-b border-border">
      <Link href="/" className="text-lg font-bold">
        <span className="text-lg font-semibold">Handwritten OCR</span>
      </Link>
      <button
        type="button"
        onClick={toggleDarkMode}
        aria-label="Toggle dark mode"
        aria-pressed={isDark}
        className="text-xl"
      >
        <CgDarkMode />
      </button>
    </nav>
  );
}
