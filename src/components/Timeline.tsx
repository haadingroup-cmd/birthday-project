"use client";
import { MILESTONES } from "@/data/content";

export default function Timeline() {
  return (
    <section>
      <h2 className="section-title">🕰️ The Journey</h2>
      <div className="timeline">
        {MILESTONES.map((m, i) => (
          <div key={i} className="timeline-item" style={{ animationDelay: `${i * 0.15}s` }}>
            <div className="timeline-year">{m.year}</div>
            <div
              className="timeline-text"
              contentEditable
              suppressContentEditableWarning
            >
              {m.text}
            </div>
          </div>
        ))}
      </div>
    </section>
  );
}
