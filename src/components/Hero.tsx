"use client";
import { BIRTHDAY } from "@/data/content";

export default function Hero() {
  return (
    <section className="hero">
      <div className="portal">
        <div style={{
          position: "absolute",
          inset: 0,
          display: "flex",
          alignItems: "center",
          justifyContent: "center",
          fontSize: "4rem",
        }}>
          🎂
        </div>
      </div>
      <h1>Happy Birthday {BIRTHDAY.name}!</h1>
      <p>{BIRTHDAY.subtitle}</p>
      <div className="scroll-hint">↓</div>
    </section>
  );
}
