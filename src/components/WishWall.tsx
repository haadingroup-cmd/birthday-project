"use client";
import { useState, useEffect } from "react";

interface Wish {
  name: string;
  message: string;
  time: number;
}

export default function WishWall() {
  const [wishes, setWishes] = useState<Wish[]>([]);
  const [name, setName] = useState("");
  const [message, setMessage] = useState("");

  useEffect(() => {
    try {
      const stored = localStorage.getItem("birthday-wishes");
      if (stored) setWishes(JSON.parse(stored));
    } catch {}
  }, []);

  const addWish = () => {
    if (!message.trim()) return;
    const newWish: Wish = {
      name: name.trim() || "Anonymous",
      message: message.trim(),
      time: Date.now(),
    };
    const updated = [newWish, ...wishes];
    setWishes(updated);
    try { localStorage.setItem("birthday-wishes", JSON.stringify(updated)); } catch {}
    setName("");
    setMessage("");
  };

  return (
    <section>
      <h2 className="section-title">💌 Wish Wall</h2>
      <div className="wish-wall">
        <div className="wish-form">
          <input
            className="wish-input"
            placeholder="Your name"
            value={name}
            onChange={(e) => setName(e.target.value)}
          />
          <input
            className="wish-input"
            placeholder="Write your birthday wish..."
            value={message}
            onChange={(e) => setMessage(e.target.value)}
            onKeyDown={(e) => e.key === "Enter" && addWish()}
          />
          <button className="wish-btn" onClick={addWish}>Send 🎉</button>
        </div>
        <div className="wishes-list">
          {wishes.map((w) => (
            <div key={w.time} className="wish-card">
              <div className="wish-name">{w.name}</div>
              <div>{w.message}</div>
            </div>
          ))}
        </div>
      </div>
    </section>
  );
}
