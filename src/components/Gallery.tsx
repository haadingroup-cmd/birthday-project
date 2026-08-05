"use client";
import { useState, useCallback } from "react";
import { PHOTOS } from "@/data/content";

export default function Gallery() {
  const [lightbox, setLightbox] = useState<number | null>(null);

  const handleMouseMove = useCallback((e: React.MouseEvent<HTMLDivElement>) => {
    const card = e.currentTarget;
    const rect = card.getBoundingClientRect();
    const x = (e.clientX - rect.left) / rect.width - 0.5;
    const y = (e.clientY - rect.top) / rect.height - 0.5;
    card.style.transform = `perspective(600px) rotateY(${x * 15}deg) rotateX(${-y * 15}deg) scale(1.02)`;
  }, []);

  const handleMouseLeave = useCallback((e: React.MouseEvent<HTMLDivElement>) => {
    e.currentTarget.style.transform = "";
  }, []);

  return (
    <section>
      <h2 className="section-title">📸 Memories</h2>
      <div className="gallery-grid">
        {PHOTOS.map((photo, i) => (
          <div
            key={i}
            className="gallery-card"
            onMouseMove={handleMouseMove}
            onMouseLeave={handleMouseLeave}
            onClick={() => setLightbox(i)}
          >
            {/* eslint-disable-next-line @next/next/no-img-element */}
            <img src={photo.src} alt={photo.caption} loading="lazy" />
            <div className="gallery-caption">{photo.caption}</div>
          </div>
        ))}
      </div>

      {lightbox !== null && (
        <div className="lightbox" onClick={() => setLightbox(null)}>
          {/* eslint-disable-next-line @next/next/no-img-element */}
          <img src={PHOTOS[lightbox].src} alt={PHOTOS[lightbox].caption} />
        </div>
      )}
    </section>
  );
}
