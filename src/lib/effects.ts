// ═══════════════════════════════════════════════════════
//  SHARED EFFECTS ENGINE — Fireworks + Confetti/Hearts
// ═══════════════════════════════════════════════════════

export interface Particle {
  x: number; y: number;
  vx: number; vy: number;
  life: number; maxLife: number;
  color: string; size: number;
  type: "spark" | "heart" | "confetti";
  rotation?: number; rotationSpeed?: number;
}

const COLORS = ["#00d4ff", "#a855f7", "#ec4899", "#fbbf24", "#34d399", "#f97316", "#fff"];

export function createFirework(x: number, y: number): Particle[] {
  const count = 30 + Math.random() * 30;
  const color = COLORS[Math.floor(Math.random() * COLORS.length)];
  const particles: Particle[] = [];
  for (let i = 0; i < count; i++) {
    const angle = (Math.PI * 2 * i) / count + (Math.random() - 0.5) * 0.5;
    const speed = 2 + Math.random() * 4;
    particles.push({
      x, y,
      vx: Math.cos(angle) * speed,
      vy: Math.sin(angle) * speed,
      life: 1,
      maxLife: 60 + Math.random() * 30,
      color,
      size: 2 + Math.random() * 2,
      type: "spark",
    });
  }
  return particles;
}

export function createHeart(x: number, y: number): Particle {
  return {
    x, y,
    vx: (Math.random() - 0.5) * 2,
    vy: -2 - Math.random() * 3,
    life: 1,
    maxLife: 80 + Math.random() * 40,
    color: Math.random() > 0.5 ? "#ec4899" : "#f43f5e",
    size: 12 + Math.random() * 12,
    type: "heart",
    rotation: Math.random() * Math.PI * 2,
    rotationSpeed: (Math.random() - 0.5) * 0.1,
  };
}

export function createConfetti(x: number, y: number): Particle {
  return {
    x, y,
    vx: (Math.random() - 0.5) * 6,
    vy: -4 - Math.random() * 4,
    life: 1,
    maxLife: 100 + Math.random() * 60,
    color: COLORS[Math.floor(Math.random() * COLORS.length)],
    size: 6 + Math.random() * 6,
    type: "confetti",
    rotation: Math.random() * Math.PI * 2,
    rotationSpeed: (Math.random() - 0.5) * 0.15,
  };
}

export function updateParticle(p: Particle): boolean {
  p.x += p.vx;
  p.y += p.vy;
  p.vy += 0.04; // gravity
  p.vx *= 0.99;
  p.life -= 1 / p.maxLife;
  if (p.rotation !== undefined && p.rotationSpeed !== undefined) {
    p.rotation += p.rotationSpeed;
  }
  return p.life > 0;
}

export function drawParticle(ctx: CanvasRenderingContext2D, p: Particle) {
  ctx.globalAlpha = Math.max(0, p.life);
  if (p.type === "heart") {
    drawHeart(ctx, p.x, p.y, p.size, p.color, p.rotation || 0);
  } else if (p.type === "confetti") {
    ctx.save();
    ctx.translate(p.x, p.y);
    ctx.rotate(p.rotation || 0);
    ctx.fillStyle = p.color;
    ctx.fillRect(-p.size / 2, -p.size / 4, p.size, p.size / 2);
    ctx.restore();
  } else {
    ctx.beginPath();
    ctx.arc(p.x, p.y, p.size * p.life, 0, Math.PI * 2);
    ctx.fillStyle = p.color;
    ctx.fill();
    // glow
    ctx.shadowBlur = 8;
    ctx.shadowColor = p.color;
    ctx.fill();
    ctx.shadowBlur = 0;
  }
  ctx.globalAlpha = 1;
}

function drawHeart(ctx: CanvasRenderingContext2D, x: number, y: number, size: number, color: string, rotation: number) {
  ctx.save();
  ctx.translate(x, y);
  ctx.rotate(rotation);
  ctx.fillStyle = color;
  ctx.beginPath();
  const s = size / 2;
  ctx.moveTo(0, s * 0.4);
  ctx.bezierCurveTo(-s, -s * 0.2, -s, -s, 0, -s * 0.4);
  ctx.bezierCurveTo(s, -s, s, -s * 0.2, 0, s * 0.4);
  ctx.fill();
  ctx.restore();
}
