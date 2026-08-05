"use client";
import { useState, useEffect } from "react";
import { BIRTHDAY } from "@/data/content";

function getNext() {
  const now = new Date();
  const thisYear = now.getFullYear();
  let target = new Date(thisYear, BIRTHDAY.birthMonth - 1, BIRTHDAY.birthDay);
  if (now > target) target = new Date(thisYear + 1, BIRTHDAY.birthMonth - 1, BIRTHDAY.birthDay);
  return target;
}

function calcDiff(target: Date) {
  const diff = target.getTime() - Date.now();
  if (diff <= 0) return { days: 0, hours: 0, minutes: 0, seconds: 0, isBirthday: true };
  return {
    days: Math.floor(diff / 86400000),
    hours: Math.floor((diff % 86400000) / 3600000),
    minutes: Math.floor((diff % 3600000) / 60000),
    seconds: Math.floor((diff % 60000) / 1000),
    isBirthday: false,
  };
}

export default function Countdown() {
  const [time, setTime] = useState(calcDiff(getNext()));

  useEffect(() => {
    const target = getNext();
    const id = setInterval(() => setTime(calcDiff(target)), 1000);
    return () => clearInterval(id);
  }, []);

  if (time.isBirthday) {
    return (
      <section>
        <h2 className="section-title">🎉 It&apos;s Your Birthday Today! 🎉</h2>
      </section>
    );
  }

  const boxes = [
    { value: time.days, label: "Days" },
    { value: time.hours, label: "Hours" },
    { value: time.minutes, label: "Minutes" },
    { value: time.seconds, label: "Seconds" },
  ];

  return (
    <section>
      <h2 className="section-title">⏰ Countdown to the Big Day</h2>
      <div className="countdown-grid">
        {boxes.map((b) => (
          <div key={b.label} className="countdown-box">
            <div className="number">{String(b.value).padStart(2, "0")}</div>
            <div className="label">{b.label}</div>
          </div>
        ))}
      </div>
    </section>
  );
}
