"use client";
import { BIRTHDAY } from "@/data/content";

export default function Happy() {
  return (
    <section className="happy-section">
      <h2 className="section-title">🌟 Happy Birthday, {BIRTHDAY.name}! 🌟</h2>
      <p className="happy-message">
        {BIRTHDAY.age} years of being absolutely amazing.
        Here&apos;s to more adventures, more memories, and more reasons to celebrate.
        The universe is brighter because you&apos;re in it. ✨
      </p>
    </section>
  );
}
