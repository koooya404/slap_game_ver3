import streamlit as st
import streamlit.components.v1 as components

st.set_page_config(page_title="尋問室ビンタ", page_icon="🖐️", layout="centered")
st.markdown("<style>.block-container{padding-top:1.2rem;max-width:1000px}</style>", unsafe_allow_html=True)
st.title("🖐️ 尋問室ビンタ")
st.caption("首の据わらない男の頭をひっぱたけ。命中 +30pt、制限時間30秒。手はマウス(指)より遅れてついてきます。")

GAME_HTML = r"""<!doctype html>
<html lang="ja">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<style>
  html,body{margin:0;padding:0;background:#111;overflow:hidden}
  canvas{display:block;width:100%;height:auto;touch-action:none;user-select:none;-webkit-user-select:none}
</style>
</head>
<body>
<canvas id="c" width="960" height="640"></canvas>
<script>
"use strict";
const W = 960, H = 640, DESK_Y = 470;
const GAME_TIME = 30, HIT_POINTS = 30, SWING_TIME = 0.22, IMPACT_AT = 0.10, HIT_RADIUS = 78;
const GRAVITY = 1400, SUBSTEPS = 8, ITER = 6, DAMPING = 0.995;
const FONT = "'Meiryo','Hiragino Sans','Noto Sans JP','Yu Gothic',sans-serif";

const C = {
  WALL:"#4a4e52", WALL_DARK:"#363a3e", FLOOR:"#26262a", DESK:"#604630", DESK_EDGE:"#422e1e",
  CHAIR:"#1c1c20", SKIN:"#deb898", SKIN_SHADE:"#b0866c", HAIR:"#181414",
  SHIRT:"#f0f0ec", SHIRT_SHADE:"#cdcdc8", VEST:"#1a1a1e", EYE_SHADOW:"#5c3c32"
};

const canvas = document.getElementById("c");
const ctx = canvas.getContext("2d");

/* ---------- 便利関数 ---------- */
function poly(pts, fill, stroke, lw) {
  ctx.beginPath();
  ctx.moveTo(pts[0][0], pts[0][1]);
  for (let i = 1; i < pts.length; i++) ctx.lineTo(pts[i][0], pts[i][1]);
  ctx.closePath();
  if (fill) { ctx.fillStyle = fill; ctx.fill(); }
  if (stroke) { ctx.strokeStyle = stroke; ctx.lineWidth = lw || 2; ctx.stroke(); }
}
function line(pts, color, lw) {
  ctx.beginPath();
  ctx.moveTo(pts[0][0], pts[0][1]);
  for (let i = 1; i < pts.length; i++) ctx.lineTo(pts[i][0], pts[i][1]);
  ctx.strokeStyle = color; ctx.lineWidth = lw; ctx.lineCap = "round"; ctx.lineJoin = "round"; ctx.stroke();
}
function circle(x, y, r, fill, stroke, lw) {
  ctx.beginPath(); ctx.arc(x, y, r, 0, Math.PI * 2);
  if (fill) { ctx.fillStyle = fill; ctx.fill(); }
  if (stroke) { ctx.strokeStyle = stroke; ctx.lineWidth = lw || 2; ctx.stroke(); }
}
function rect(x, y, w, h, fill) { ctx.fillStyle = fill; ctx.fillRect(x, y, w, h); }
function rrect(x, y, w, h, r, fill, stroke, lw) {
  ctx.beginPath();
  ctx.moveTo(x + r, y);
  ctx.arcTo(x + w, y, x + w, y + h, r);
  ctx.arcTo(x + w, y + h, x, y + h, r);
  ctx.arcTo(x, y + h, x, y, r);
  ctx.arcTo(x, y, x + w, y, r);
  ctx.closePath();
  if (fill) { ctx.fillStyle = fill; ctx.fill(); }
  if (stroke) { ctx.strokeStyle = stroke; ctx.lineWidth = lw || 2; ctx.stroke(); }
}
function ellipse(x, y, rx, ry, fill) {
  ctx.beginPath(); ctx.ellipse(x, y, rx, ry, 0, 0, Math.PI * 2); ctx.fillStyle = fill; ctx.fill();
}
function text(str, x, y, size, color, align, alpha) {
  ctx.save();
  ctx.globalAlpha = alpha === undefined ? 1 : alpha;
  ctx.font = "bold " + size + "px " + FONT;
  ctx.textAlign = align || "center";
  ctx.textBaseline = "middle";
  ctx.lineWidth = Math.max(3, size / 8);
  ctx.strokeStyle = "rgba(0,0,0,0.55)";
  ctx.lineJoin = "round";
  ctx.strokeText(str, x, y);
  ctx.fillStyle = color;
  ctx.fillText(str, x, y);
  ctx.restore();
}

/* ---------- ラグドール(Verlet) ---------- */
class Ragdoll {
  constructor(anchor) { this.anchor = anchor; this.NECK_SEG = 11; this.NECK_N = 3; this.HEAD_LEN = 100; this.reset(); }
  reset() {
    const [ax, ay] = this.anchor;
    this.pts = [{ x: ax, y: ay, ox: ax, oy: ay, pinned: true }];
    for (let i = 1; i <= this.NECK_N; i++) {
      const y = ay - i * this.NECK_SEG;
      this.pts.push({ x: ax, y, ox: ax, oy: y, pinned: false });
    }
    const c = this.pts[this.pts.length - 1];
    const tx = c.x + 30, ty = c.y - this.HEAD_LEN + 10;
    this.pts.push({ x: tx, y: ty, ox: tx, oy: ty, pinned: false });
    this.links = [];
    for (let i = 0; i < this.NECK_N; i++) this.links.push([i, i + 1, this.NECK_SEG]);
    this.links.push([this.NECK_N, this.NECK_N + 1, this.HEAD_LEN]);
  }
  get chin() { return this.pts[this.NECK_N]; }
  get top() { return this.pts[this.NECK_N + 1]; }
  impulse(ix, iy) { for (let i = 1; i < this.pts.length; i++) { this.pts[i].ox -= ix; this.pts[i].oy -= iy; } }
  step(dt, ax, ay) {
    const p0 = this.pts[0];
    p0.x = p0.ox = ax; p0.y = p0.oy = ay;
    const h = dt / SUBSTEPS;
    for (let s = 0; s < SUBSTEPS; s++) {
      for (const pt of this.pts) {
        if (pt.pinned) continue;
        const vx = (pt.x - pt.ox) * DAMPING, vy = (pt.y - pt.oy) * DAMPING;
        pt.ox = pt.x; pt.oy = pt.y;
        pt.x += vx; pt.y += vy + GRAVITY * h * h;
      }
      for (let it = 0; it < ITER; it++) {
        for (const [a, b, len] of this.links) {
          const pa = this.pts[a], pb = this.pts[b];
          const dx = pb.x - pa.x, dy = pb.y - pa.y;
          const d = Math.hypot(dx, dy) || 1e-6;
          const diff = (d - len) / d;
          const wa = pa.pinned ? 0 : 1, wb = pb.pinned ? 0 : 1;
          const ws = wa + wb;
          if (ws === 0) continue;
          pa.x += dx * diff * wa / ws; pa.y += dy * diff * wa / ws;
          pb.x -= dx * diff * wb / ws; pb.y -= dy * diff * wb / ws;
        }
        for (let i = 1; i < this.pts.length; i++) {
          const pt = this.pts[i];
          if (pt.y > DESK_Y - 4) { pt.y = DESK_Y - 4; pt.ox = pt.x - (pt.x - pt.ox) * 0.6; }
          pt.x = Math.max(20, Math.min(W - 20, pt.x));
        }
      }
    }
  }
}

/* ---------- 描画 ---------- */
/* ---------- 3Dっぽい丸いデフォルメ描画 ---------- */
function lightGrad(x, y, r, c0, c1, c2) {
  // 光源は画面の左上に固定(頭が回っても陰影は動かない)
  const g = ctx.createRadialGradient(x - r * 0.35, y - r * 0.4, r * 0.08, x, y, r * 1.05);
  g.addColorStop(0, c0); g.addColorStop(0.55, c1); g.addColorStop(1, c2);
  return g;
}
function ball(x, y, r, c0, c1, c2) { circle(x, y, r, lightGrad(x, y, r, c0, c1, c2)); }
function softShadow(x, y, rx, ry, alpha) {
  const g = ctx.createRadialGradient(x, y, 1, x, y, rx);
  g.addColorStop(0, "rgba(0,0,0," + alpha + ")"); g.addColorStop(1, "rgba(0,0,0,0)");
  ctx.save(); ctx.translate(0, 0); ctx.fillStyle = g;
  ctx.beginPath(); ctx.ellipse(x, y, rx, ry, 0, 0, Math.PI * 2); ctx.fill(); ctx.restore();
}

function drawHead(doll, tick) {
  const c = doll.chin, t = doll.top;
  let ux = t.x - c.x, uy = t.y - c.y;
  const n = Math.hypot(ux, uy) || 1;
  ux /= n; uy /= n;
  const rx = -uy, ry = ux;
  const Lp = (x, y) => [c.x + rx * x + ux * y, c.y + ry * x + uy * y];
  const rot = Math.atan2(uy, ux) + Math.PI / 2;

  // 首(ぷにっと太いチューブ)
  const neck = [];
  for (let i = 0; i <= doll.NECK_N; i++) neck.push([doll.pts[i].x, doll.pts[i].y]);
  line(neck, "#b98568", 20);
  line(neck, "#dcb292", 14);

  // 耳
  const hc = Lp(0, 52);
  for (const s of [-1, 1]) {
    const e = Lp(s * 57, 46);
    ball(e[0], e[1], 14, "#f6d8bc", "#dcb090", "#b98568");
    const e2 = Lp(s * 57, 46);
    circle(e2[0], e2[1], 6, "rgba(150,90,70,0.45)");
  }

  // 頭(つるんと丸い球体)
  ctx.beginPath(); ctx.ellipse(hc[0], hc[1], 59, 57, rot, 0, Math.PI * 2);
  const g = ctx.createRadialGradient(hc[0] - 24, hc[1] - 28, 6, hc[0], hc[1], 74);
  g.addColorStop(0, "#fff0dc"); g.addColorStop(0.45, "#eec7a4"); g.addColorStop(1, "#b07c60");
  ctx.fillStyle = g; ctx.fill();
  ctx.strokeStyle = "rgba(110,60,45,0.35)"; ctx.lineWidth = 2; ctx.stroke();

  // 顔のパーツ(頭のローカル座標:y が上向き)
  ctx.save();
  ctx.transform(rx, ry, ux, uy, c.x, c.y);

  // ほっぺ
  for (const s of [-1, 1]) {
    const bg = ctx.createRadialGradient(s * 36, 32, 1, s * 36, 32, 15);
    bg.addColorStop(0, "rgba(255,110,110,0.38)"); bg.addColorStop(1, "rgba(255,110,110,0)");
    ctx.fillStyle = bg; ctx.beginPath(); ctx.arc(s * 36, 32, 15, 0, Math.PI * 2); ctx.fill();
  }
  // 落ち窪んだ目元の影(彫りの深さ)
  for (const s of [-1, 1]) {
    const sg = ctx.createRadialGradient(s * 22, 54, 2, s * 22, 54, 22);
    sg.addColorStop(0, "rgba(110,60,50,0.55)"); sg.addColorStop(1, "rgba(110,60,50,0)");
    ctx.fillStyle = sg; ctx.beginPath(); ctx.arc(s * 22, 54, 22, 0, Math.PI * 2); ctx.fill();
  }
  // 目
  const look = 1.5 * Math.sin(tick * 0.05);
  for (const s of [-1, 1]) {
    ctx.fillStyle = "#1a1212";
    ctx.beginPath(); ctx.ellipse(s * 22, 52, 8.5, 11, 0, 0, Math.PI * 2); ctx.fill();
    ctx.fillStyle = "#ffffff";
    ctx.beginPath(); ctx.arc(s * 22 + 2.5 + look, 56.5, 3.4, 0, Math.PI * 2); ctx.fill();
    ctx.beginPath(); ctx.arc(s * 22 - 2.5, 47, 1.7, 0, Math.PI * 2); ctx.fill();
  }
  // 太い眉(少し険しく)
  for (const s of [-1, 1]) line([[s * 8, 68], [s * 22, 73], [s * 35, 74]], "#1c1414", 7);
  // 鼻
  ctx.fillStyle = "rgba(120,70,50,0.28)";
  ctx.beginPath(); ctx.ellipse(0, 33, 8, 3.2, 0, 0, Math.PI * 2); ctx.fill();
  const ng = ctx.createRadialGradient(-2, 42, 1, 0, 40, 10);
  ng.addColorStop(0, "#fbe4cc"); ng.addColorStop(1, "#d9a888");
  ctx.fillStyle = ng; ctx.beginPath(); ctx.ellipse(0, 40, 8, 7.5, 0, 0, Math.PI * 2); ctx.fill();
  // 口(力が抜けてぽかん)
  ctx.fillStyle = "#4e2224";
  ctx.beginPath(); ctx.ellipse(0, 16, 10, 7, 0, 0, Math.PI * 2); ctx.fill();
  ctx.fillStyle = "#d46a6a";
  ctx.beginPath(); ctx.ellipse(0, 12.5, 6, 3.2, 0, 0, Math.PI * 2); ctx.fill();
  ctx.restore();

  // 髪(頭の形でクリップ)
  ctx.save();
  ctx.beginPath(); ctx.ellipse(hc[0], hc[1], 59, 57, rot, 0, Math.PI * 2); ctx.clip();
  ctx.transform(rx, ry, ux, uy, c.x, c.y);
  const hg = ctx.createLinearGradient(-30, 140, 30, 80);
  hg.addColorStop(0, "#3a3030"); hg.addColorStop(1, "#120e0e");
  ctx.fillStyle = hg;
  ctx.beginPath(); ctx.ellipse(0, 122, 70, 38, 0, 0, Math.PI * 2); ctx.fill();
  for (const [bx_, by_, rx_, ry_] of [[-36, 88, 20, 15], [-12, 90, 20, 15], [14, 90, 20, 15], [38, 88, 20, 15]]) {
    ctx.beginPath(); ctx.ellipse(bx_, by_, rx_, ry_, 0, 0, Math.PI * 2); ctx.fill();
  }
  ctx.fillStyle = "rgba(255,255,255,0.18)";
  ctx.beginPath(); ctx.ellipse(-18, 104, 22, 5, 0.2, 0, Math.PI * 2); ctx.fill();
  ctx.restore();

  // つや(画面左上から当たるハイライト)
  ctx.save();
  ctx.translate(hc[0] - 26, hc[1] - 30); ctx.rotate(-0.6);
  const sp = ctx.createRadialGradient(0, 0, 1, 0, 0, 16);
  sp.addColorStop(0, "rgba(255,255,255,0.55)"); sp.addColorStop(1, "rgba(255,255,255,0)");
  ctx.fillStyle = sp; ctx.beginPath(); ctx.ellipse(0, 0, 16, 9, 0, 0, Math.PI * 2); ctx.fill();
  ctx.restore();
}

function drawScene(doll, sway, tick) {
  // 背景(グラデの壁 + 床)
  const wg = ctx.createLinearGradient(0, 0, 0, DESK_Y);
  wg.addColorStop(0, "#565c63"); wg.addColorStop(1, "#3b4046");
  rect(0, 0, W, H, wg);
  rect(0, 0, W, 90, "#33373c");
  rect(0, DESK_Y + 60, W, H, "#222226");
  // マジックミラー風の窓
  rrect(70, 120, 220, 150, 10, "#1e262c", "#7a848a", 6);
  poly([[84,134],[160,134],[122,256],[84,256]], "rgba(120,150,170,0.18)");
  // ランプと光
  line([[W/2,0],[W/2,70]], "#141414", 3);
  poly([[W/2-50,100],[W/2+50,100],[W/2+20,70],[W/2-20,70]], "#26262a");
  poly([[W/2-40,100],[W/2+40,100],[W/2+260,DESK_Y],[W/2-260,DESK_Y]], "rgba(255,240,180,0.13)");

  const ax = doll.anchor[0], ay = doll.anchor[1], bx = Math.round(sway);

  // 椅子の背もたれ
  const cg = ctx.createLinearGradient(ax - 120, 0, ax + 120, 0);
  cg.addColorStop(0, "#2e2e36"); cg.addColorStop(0.5, "#1a1a1f"); cg.addColorStop(1, "#101014");
  rrect(ax - 122 + bx, ay - 40, 244, 270, 46, cg, "#3a3a42", 3);

  // 胴体: まるっこいシャツ
  const sg = ctx.createLinearGradient(ax - 90, 0, ax + 90, 0);
  sg.addColorStop(0, "#c9c9c6"); sg.addColorStop(0.35, "#ffffff"); sg.addColorStop(1, "#b9b9b6");
  rrect(ax - 90 + bx, ay - 6, 180, 178, 58, sg, "rgba(0,0,0,0.25)", 2);

  // 腕(ぷっくりカプセル)+ 手
  for (const s of [-1, 1]) {
    const sh = [ax + s * 90 + bx, ay + 22], el = [ax + s * 120 + bx, ay + 120], hd = [ax + s * 72 + bx, DESK_Y - 12];
    line([sh, el], "#bdbdb9", 40);
    line([el, hd], "#bdbdb9", 34);
    line([sh, el], "#f4f4f0", 36);
    line([el, hd], "#f4f4f0", 30);
    line([[sh[0] - 7, sh[1] + 4], [el[0] - 7, el[1] - 2]], "rgba(255,255,255,0.8)", 8);
    ball(el[0], el[1], 19, "#ffffff", "#ececea", "#b5b5b0");
    ball(hd[0], hd[1], 19, "#fff0dc", "#e8bf9c", "#b07c60");
  }

  // 黒チョッキ(丸み + つや)
  const vg = ctx.createLinearGradient(ax - 70, 0, ax + 70, 0);
  vg.addColorStop(0, "#14141a"); vg.addColorStop(0.3, "#3e3e48"); vg.addColorStop(1, "#0e0e12");
  rrect(ax - 70 + bx, ay + 10, 140, 168, 40, vg);
  // Vの字のシャツ + 襟
  ctx.lineJoin = "round";
  poly([[ax - 24 + bx, ay + 8], [ax + 24 + bx, ay + 8], [ax + bx, ay + 82]], "#f4f4f0", "#f4f4f0", 6);
  poly([[ax - 28 + bx, ay - 2], [ax - 3 + bx, ay + 6], [ax - 21 + bx, ay + 30]], "#ffffff", "#c4c4c0", 2);
  poly([[ax + 28 + bx, ay - 2], [ax + 3 + bx, ay + 6], [ax + 21 + bx, ay + 30]], "#ffffff", "#c4c4c0", 2);
  for (let i = 0; i < 2; i++) ball(ax + bx, ay + 98 + i * 30, 6, "#ffffff", "#9a9aa2", "#3a3a40");
  ctx.fillStyle = "rgba(255,255,255,0.10)";
  ctx.beginPath(); ctx.ellipse(ax - 40 + bx, ay + 90, 8, 40, 0.1, 0, Math.PI * 2); ctx.fill();

  drawHead(doll, tick);

  // 机(木目っぽいグラデ + 上面のつや)
  const dg = ctx.createLinearGradient(0, DESK_Y, 0, DESK_Y + 40);
  dg.addColorStop(0, "#86643f"); dg.addColorStop(1, "#5d4328");
  rect(0, DESK_Y, W, 40, dg);
  rect(0, DESK_Y + 40, W, 110, "#3b2a1b");
  line([[0, DESK_Y + 1], [W, DESK_Y + 1]], "rgba(255,230,190,0.45)", 3);
  rrect(W/2 - 170, DESK_Y + 8, 96, 22, 4, "#ecece2", "#b8b8ae", 1);
  rrect(W/2 + 120, DESK_Y - 14, 34, 24, 8, "#4a4a50", "#2a2a2e", 1);
  softShadow(ax + bx, DESK_Y + 2, 190, 14, 0.35);

  // ビネット(奥行き感)
  const vig = ctx.createRadialGradient(W / 2, H / 2, 200, W / 2, H / 2, 620);
  vig.addColorStop(0, "rgba(0,0,0,0)"); vig.addColorStop(1, "rgba(0,0,0,0.45)");
  ctx.fillStyle = vig; ctx.fillRect(0, 0, W, H);
}

function drawHand(x, y, angleDeg, scale) {
  ctx.save();
  ctx.translate(x, y);
  ctx.rotate(angleDeg * Math.PI / 180);
  ctx.scale(scale, scale);
  rrect(-27, 38, 54, 52, 14, "#f4f4f0", "#bdbdb8", 2);
  const pg = ctx.createLinearGradient(-28, 0, 28, 46);
  pg.addColorStop(0, "#fbe2c8"); pg.addColorStop(1, "#d3a583");
  const fingers = [[-20, 42], [-7, 50], [7, 48], [20, 40]];
  for (const [fx, fl] of fingers) rrect(fx - 7.5, -fl, 15, fl + 10, 7.5, pg, "#b98a6c", 1.5);
  rrect(-29, -2, 58, 48, 22, pg, "#b98a6c", 2);
  ctx.save(); ctx.translate(-26, 24); ctx.rotate(-0.9);
  rrect(-30, -9, 34, 18, 9, pg, "#b98a6c", 1.5);
  ctx.restore();
  ctx.fillStyle = "rgba(255,255,255,0.4)";
  ctx.beginPath(); ctx.ellipse(-8, 14, 11, 5, -0.3, 0, Math.PI * 2); ctx.fill();
  ctx.restore();
}

function rankText(score) {
  if (score === 0) return "空振り職人";
  if (score <= 30) return "まぐれ当たり";
  if (score <= 90) return "尋問官見習い";
  if (score <= 180) return "手練れ";
  return "神の手";
}

/* ---------- ゲーム状態 ---------- */
const anchor = [W / 2, 330];
const doll = new Ragdoll(anchor);

let state = "title";
let best = 0, score = 0, timeLeft = GAME_TIME;
let sway = 0, swayV = 0, tick = 0, clockT = 0;
let history = [];
let hand = [W / 2, H / 2], handPrev = [W / 2, H / 2];
let swing = null, impactDone = false;
let shake = 0, flash = 0;
let floaters = [], sparks = [];
let nextJolt = 1.0, hits = 0, swings = 0;
let mouse = [W / 2, H / 2];
let stateSince = 0;

function resetGame() {
  doll.reset();
  score = 0; timeLeft = GAME_TIME; sway = swayV = 0;
  swing = null; impactDone = false; shake = flash = 0;
  floaters = []; sparks = []; nextJolt = 0.8; hits = swings = 0;
}
function startGame() { resetGame(); state = "play"; canvas.style.cursor = "none"; }

function toCanvas(e) {
  const r = canvas.getBoundingClientRect();
  return [(e.clientX - r.left) * W / r.width, (e.clientY - r.top) * H / r.height];
}
canvas.addEventListener("pointermove", e => { mouse = toCanvas(e); });
canvas.addEventListener("pointerdown", e => {
  mouse = toCanvas(e);
  if (state === "play") {
    if (swing === null) { swing = 0; impactDone = false; swings++; }
  } else if (clockT - stateSince > 0.6) {
    startGame();
  }
  e.preventDefault();
});
window.addEventListener("keydown", e => {
  if ((e.code === "Space" || e.code === "Enter") && state !== "play" && clockT - stateSince > 0.6) {
    startGame(); e.preventDefault();
  }
});

/* ---------- メインループ ---------- */
let last = performance.now();
function frame(now) {
  const dt = Math.min((now - last) / 1000, 1 / 30);
  last = now;
  if (dt <= 0) { requestAnimationFrame(frame); return; }
  tick++; clockT += dt;

  // 手のラグ
  history.push([clockT, mouse[0], mouse[1]]);
  const lag = 0.13 + 0.12 * (0.5 + 0.5 * Math.sin(clockT * 1.7)) + 0.04 * Math.sin(clockT * 5.3);
  while (history.length > 2 && history[1][0] < clockT - 0.6) history.shift();
  let target = [history[0][1], history[0][2]];
  for (const h of history) {
    if (h[0] <= clockT - lag) target = [h[1], h[2]]; else break;
  }
  handPrev = hand.slice();
  const k = Math.min(1, dt * 14);
  hand[0] += (target[0] - hand[0]) * k;
  hand[1] += (target[1] - hand[1]) * k;
  const hvx = (hand[0] - handPrev[0]) / dt, hvy = (hand[1] - handPrev[1]) / dt;

  if (state === "play") {
    timeLeft -= dt;
    if (timeLeft <= 0) {
      timeLeft = 0; state = "result"; stateSince = clockT; best = Math.max(best, score); swing = null;
      canvas.style.cursor = "default";
    }
    nextJolt -= dt;
    if (nextJolt <= 0) {
      nextJolt = 0.6 + Math.random() * 0.9;
      swayV += (Math.random() < 0.5 ? -1 : 1) * (80 + Math.random() * 140);
      doll.impulse((Math.random() * 14 - 7), -(2 + Math.random() * 8));
    }
    if (swing !== null) {
      swing += dt;
      if (!impactDone && swing >= IMPACT_AT) {
        impactDone = true;
        const c = doll.chin, t = doll.top;
        const cx = (c.x + t.x) / 2, cy = (c.y + t.y) / 2;
        if (Math.hypot(hand[0] - cx, hand[1] - cy) <= HIT_RADIUS) {
          score += HIT_POINTS; hits++;
          shake = 14; flash = 0.18;
          doll.impulse(14 + Math.max(0, hvx) * 0.012, -4 + hvy * 0.008);
          swayV += 420;
          floaters.push({ text: "+" + HIT_POINTS, x: cx, y: cy - 60, color: "#ffe65a", t: 0 });
          floaters.push({ text: "パァン!", x: cx + 40, y: cy - 10, color: "#ff785a", t: 0 });
          for (let i = 0; i < 22; i++) {
            const a = Math.random() * Math.PI * 2, s = 160 + Math.random() * 300;
            sparks.push({ x: cx, y: cy, vx: Math.cos(a) * s, vy: Math.sin(a) * s, t: 0, life: 0.25 + Math.random() * 0.25 });
          }
        } else {
          floaters.push({ text: "空振り", x: hand[0], y: hand[1] - 40, color: "#c8c8d2", t: 0 });
        }
      }
      if (swing >= SWING_TIME) swing = null;
    }
  }

  // 物理
  swayV += (-sway * 40) * dt;
  swayV *= 0.93;
  sway += swayV * dt;
  doll.step(dt, anchor[0] + sway, anchor[1] + Math.sin(tick * 0.04) * 1.5);

  floaters = floaters.filter(f => { f.t += dt; f.y -= 70 * dt; return f.t < 0.9; });
  sparks = sparks.filter(s => { s.t += dt; s.x += s.vx * dt; s.y += s.vy * dt; s.vy += 600 * dt; return s.t < s.life; });
  shake = Math.max(0, shake - 40 * dt);
  flash = Math.max(0, flash - dt);

  // 描画
  ctx.save();
  if (shake) ctx.translate((Math.random() * 2 - 1) * shake, (Math.random() * 2 - 1) * shake);
  drawScene(doll, sway, tick);
  for (const s of sparks) circle(s.x, s.y, 4, "#ffdc78");
  for (const f of floaters) text(f.text, f.x, f.y, 54, f.color, "center", Math.max(0, 1 - f.t / 0.9));

  if (state === "play") {
    circle(mouse[0], mouse[1], 18, null, "rgba(255,255,255,0.85)", 2);
    circle(mouse[0], mouse[1], 2, "#fff");
    let ang = -20, sc = 1;
    if (swing !== null) {
      const p = swing / SWING_TIME;
      ang = -55 + 110 * (p * p * (3 - 2 * p));
      sc = 1 + 0.3 * Math.sin(p * Math.PI);
    }
    drawHand(hand[0], hand[1], ang, sc);
  }
  ctx.restore();

  if (state === "play" || state === "result") {
    rect(0, 0, W, 54, "#14141a");
    text("SCORE " + score, 18, 28, 30, "#ffe65a", "left");
    rrect(W/2 - 150, 18, 300, 20, 6, "#46464c");
    const ratio = timeLeft / GAME_TIME;
    if (ratio > 0) rrect(W/2 - 150, 18, Math.max(12, 300 * ratio), 20, 6, ratio > 0.34 ? "#6edc82" : "#eb5a50");
    text(timeLeft.toFixed(1).padStart(4, "0"), W - 18, 28, 30, "#f0f0f0", "right");
  }
  if (flash > 0) { ctx.fillStyle = "rgba(255,255,255," + (0.7 * flash / 0.18) + ")"; ctx.fillRect(0, 0, W, H); }

  if (state === "title") {
    rect(0, 0, W, H, "rgba(0,0,0,0.6)");
    text("尋問室ビンタ", W/2, 150, 96, "#fff0c8");
    text("首の据わらない男の頭を、ラグった手でひっぱたけ", W/2, 250, 30, "#e6e6e6");
    text("クリック / タップ = ビンタ   命中 +30pt   制限時間 30秒", W/2, 320, 20, "#d2d2d2");
    text("薄い輪っか = あなたの指先 / 手はそれより遅れてついてくる", W/2, 352, 20, "#d2d2d2");
    text("クリック or SPACE でスタート", W/2, 440, 30, "#ffe65a");
  } else if (state === "result") {
    rect(0, 0, W, H, "rgba(0,0,0,0.67)");
    const acc = swings ? Math.floor(100 * hits / swings) : 0;
    text("TIME UP", W/2, 140, 54, "#fff0c8");
    text(score + " pt", W/2, 240, 96, "#ffe65a");
    text("称号: " + rankText(score), W/2, 330, 30, "#f0f0f0");
    text("命中 " + hits + " / " + swings + " 回 (" + acc + "%)    ベスト " + best + " pt", W/2, 380, 20, "#d2d2d2");
    text("クリック or SPACE でリトライ", W/2, 460, 30, "#ffe65a");
  }

  requestAnimationFrame(frame);
}
requestAnimationFrame(frame);
</script>
</body>
</html>
"""

components.html(GAME_HTML, height=660, scrolling=False)
