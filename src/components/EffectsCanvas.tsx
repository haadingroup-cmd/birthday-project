"use client";
import { useEffect, useRef } from "react";
import { createHeart, createFirework, updateParticle, drawParticle, type Particle } from "@/lib/effects";

export default function EffectsCanvas() {
  const canvasRef = useRef<HTMLCanvasElement>(null);
  const particlesRef = useRef<Particle[]>([]);

  useEffect(() => {
    const canvas = canvasRef.current;
    if (!canvas) return;
    const ctx = canvas.getContext("2d");
    if (!ctx) return;

    const resize = () => {
      canvas.width = window.innerWidth;
      canvas.height = window.innerHeight;
    };
    resize();
    window.addEventListener("resize", resize);

    const handleClick = (e: MouseEvent) => {
      // Add hearts
      for (let i = 0; i < 3; i++) {
        particlesRef.current.push(createHeart(e.clientX, e.clientY));
      }
    };
    window.addEventListener("click", handleClick);

    let raf: number;
    const loop = () => {
      ctx.clearRect(0, 0, canvas.width, canvas.height);
      particlesRef.current = particlesRef.current.filter((p) => {
        const alive = updateParticle(p);
        if (alive) drawParticle(ctx, p);
        return alive;
      });
      raf = requestAnimationFrame(loop);
    };
    raf = requestAnimationFrame(loop);

    // Expose for easter egg
    (window as unknown as Record<string, unknown>).__addFireworks = (x: number, y: number) => {
      particlesRef.current.push(...createFirework(x, y));
    };

    return () => {
      window.removeEventListener("resize", resize);
      window.removeEventListener("click", handleClick);
      cancelAnimationFrame(raf);
    };
  }, []);

  return <canvas ref={canvasRef} className="effects-canvas" />;
}
