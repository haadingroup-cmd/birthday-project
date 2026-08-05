"use client";
import { useEffect, useRef, useState } from "react";

export default function AmbientSound() {
  const [playing, setPlaying] = useState(false);
  const ctxRef = useRef<AudioContext | null>(null);
  const nodesRef = useRef<OscillatorNode[]>([]);

  const toggle = () => {
    if (playing) {
      nodesRef.current.forEach((n) => { try { n.stop(); } catch {} });
      nodesRef.current = [];
      ctxRef.current?.close();
      ctxRef.current = null;
      setPlaying(false);
    } else {
      const ctx = new AudioContext();
      ctxRef.current = ctx;

      // Soft ambient chord
      const freqs = [130.81, 164.81, 196.0, 261.63]; // C major
      freqs.forEach((f) => {
        const osc = ctx.createOscillator();
        const gain = ctx.createGain();
        osc.type = "sine";
        osc.frequency.value = f;
        gain.gain.value = 0.03;
        osc.connect(gain);
        gain.connect(ctx.destination);
        osc.start();
        nodesRef.current.push(osc);
      });
      setPlaying(true);
    }
  };

  useEffect(() => {
    return () => {
      nodesRef.current.forEach((n) => { try { n.stop(); } catch {} });
      ctxRef.current?.close();
    };
  }, []);

  return (
    <button
      onClick={toggle}
      style={{
        position: "fixed",
        bottom: 20,
        right: 20,
        zIndex: 100,
        width: 48,
        height: 48,
        borderRadius: "50%",
        border: "1px solid rgba(168, 85, 247, 0.4)",
        background: "rgba(18, 18, 42, 0.8)",
        backdropFilter: "blur(10px)",
        color: "#e2e8f0",
        fontSize: "1.3rem",
        cursor: "pointer",
        display: "flex",
        alignItems: "center",
        justifyContent: "center",
        transition: "transform 0.2s",
      }}
      title={playing ? "Mute" : "Play ambient"}
    >
      {playing ? "🔊" : "🔇"}
    </button>
  );
}
