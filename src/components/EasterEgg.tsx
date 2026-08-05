"use client";
import { useEffect, useRef } from "react";

export default function EasterEgg() {
  const bufferRef = useRef("");

  useEffect(() => {
    const handleKey = (e: KeyboardEvent) => {
      // Don't trigger while typing in inputs
      if (e.target instanceof HTMLInputElement || e.target instanceof HTMLTextAreaElement) return;
      if ((e.target as HTMLElement)?.isContentEditable) return;

      bufferRef.current += e.key.toLowerCase();
      if (bufferRef.current.length > 20) {
        bufferRef.current = bufferRef.current.slice(-20);
      }

      if (bufferRef.current.includes("birthday")) {
        bufferRef.current = "";
        const addFw = (window as unknown as Record<string, unknown>).__addFireworks as
          ((x: number, y: number) => void) | undefined;
        if (addFw) {
          // Launch fireworks at random positions
          for (let i = 0; i < 5; i++) {
            setTimeout(() => {
              addFw(
                100 + Math.random() * (window.innerWidth - 200),
                100 + Math.random() * (window.innerHeight / 2)
              );
            }, i * 300);
          }
        }
      }

      if (bufferRef.current.includes("2005")) {
        bufferRef.current = "";
        const addFw = (window as unknown as Record<string, unknown>).__addFireworks as
          ((x: number, y: number) => void) | undefined;
        if (addFw) {
          for (let i = 0; i < 8; i++) {
            setTimeout(() => {
              addFw(
                100 + Math.random() * (window.innerWidth - 200),
                80 + Math.random() * (window.innerHeight / 3)
              );
            }, i * 200);
          }
        }
      }
    };

    window.addEventListener("keydown", handleKey);
    return () => window.removeEventListener("keydown", handleKey);
  }, []);

  return null;
}
