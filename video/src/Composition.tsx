import React from "react";
import {
  AbsoluteFill,
  interpolate,
  spring,
  useCurrentFrame,
  useVideoConfig,
  Sequence,
} from "remotion";

// ── الألوان ──────────────────────────────────────────────
const C = {
  bg: "#0A0E1A",
  green: "#00D46E",
  darkGreen: "#009650",
  white: "#FFFFFF",
  gray: "#96A0B4",
  card: "#141C30",
  accent: "#64DCFF",
  gradientEnd: "#001E14",
};

const FONT = "'Cairo', 'Arial', sans-serif";

// ── مساعدات ──────────────────────────────────────────────
function useSpr(frame: number, delay: number, damping = 14, stiffness = 120) {
  const { fps } = useVideoConfig();
  return spring({ frame: frame - delay, fps, config: { damping, stiffness } });
}

function easeOut(t: number) {
  return 1 - Math.pow(1 - t, 3);
}

function clamp01(v: number) {
  return Math.max(0, Math.min(1, v));
}

function fadeIn(frame: number, delay: number, dur = 12) {
  return clamp01((frame - delay) / dur);
}

function slideUp(frame: number, delay: number, dur = 15) {
  const p = easeOut(clamp01((frame - delay) / dur));
  return { opacity: p, translateY: (1 - p) * 80 };
}

// ── مكونات مشتركة ────────────────────────────────────────

const GlowOrb: React.FC<{ x: number; y: number; color: string; size?: number }> = ({
  x, y, color, size = 500,
}) => (
  <div
    style={{
      position: "absolute",
      left: x - size / 2,
      top: y - size / 2,
      width: size,
      height: size,
      borderRadius: "50%",
      background: `radial-gradient(circle, ${color}33 0%, transparent 70%)`,
      pointerEvents: "none",
    }}
  />
);

const Card: React.FC<{
  children: React.ReactNode;
  style?: React.CSSProperties;
  glow?: boolean;
}> = ({ children, style, glow }) => (
  <div
    style={{
      background: C.card,
      borderRadius: 32,
      border: `2px solid ${C.green}`,
      padding: "48px 56px",
      boxShadow: glow
        ? `0 0 40px ${C.green}44, 0 0 80px ${C.green}22`
        : "none",
      ...style,
    }}
  >
    {children}
  </div>
);

const ArabicText: React.FC<{
  children: string;
  size: number;
  color?: string;
  weight?: number;
  style?: React.CSSProperties;
}> = ({ children, size, color = C.white, weight = 700, style }) => (
  <div
    style={{
      fontFamily: FONT,
      fontSize: size,
      fontWeight: weight,
      color,
      direction: "rtl",
      textAlign: "center",
      lineHeight: 1.3,
      ...style,
    }}
  >
    {children}
  </div>
);

// ════════════════════════════════════════════════════════════
// المشهد 1 — Hook (0-5 ثواني)
// ════════════════════════════════════════════════════════════
const Scene1: React.FC = () => {
  const frame = useCurrentFrame();

  const emoji = slideUp(frame, 0, 12);
  const line1 = slideUp(frame, 8, 12);
  const line2 = slideUp(frame, 16, 12);
  const underline = fadeIn(frame, 60, 20);

  return (
    <AbsoluteFill
      style={{
        background: `linear-gradient(160deg, ${C.bg} 60%, #0A1F10 100%)`,
        alignItems: "center",
        justifyContent: "center",
        flexDirection: "column",
        gap: 28,
      }}
    >
      <GlowOrb x={540} y={600} color={C.green} size={700} />

      <div style={{ opacity: emoji.opacity, transform: `translateY(${emoji.translateY}px)`, fontSize: 140 }}>
        😩
      </div>

      <div style={{ opacity: line1.opacity, transform: `translateY(${line1.translateY}px)` }}>
        <ArabicText size={100} weight={900}>تعبت تحسب</ArabicText>
      </div>

      <div style={{ opacity: line2.opacity, transform: `translateY(${line2.translateY}px)`, position: "relative" }}>
        <ArabicText size={100} weight={900} color={C.green}>مصاريفك؟</ArabicText>
        <div
          style={{
            position: "absolute",
            bottom: -8,
            left: "10%",
            right: "10%",
            height: 5,
            background: C.green,
            borderRadius: 4,
            opacity: underline,
          }}
        />
      </div>
    </AbsoluteFill>
  );
};

// ════════════════════════════════════════════════════════════
// المشهد 2 — الحل (5-10 ثواني)
// ════════════════════════════════════════════════════════════
const Scene2: React.FC = () => {
  const frame = useCurrentFrame();
  const { fps } = useVideoConfig();

  const scale = spring({ frame, fps, config: { damping: 18, stiffness: 100 } });
  const scaleFrom = interpolate(scale, [0, 1], [0.8, 1]);

  const emoji = fadeIn(frame, 10, 12);
  const title = slideUp(frame, 20, 15);
  const sub = slideUp(frame, 35, 15);
  const telegram = fadeIn(frame, 50, 15);

  return (
    <AbsoluteFill
      style={{
        background: C.bg,
        alignItems: "center",
        justifyContent: "center",
        flexDirection: "column",
        gap: 40,
      }}
    >
      <GlowOrb x={900} y={300} color={C.accent} size={400} />
      <GlowOrb x={200} y={1500} color={C.green} size={500} />

      <div style={{ transform: `scale(${scaleFrom})`, width: "85%" }}>
        <Card glow style={{ textAlign: "center", position: "relative" }}>
          <div style={{ opacity: emoji.opacity, fontSize: 110, marginBottom: 24 }}>💬</div>

          <div style={{ opacity: title.opacity, transform: `translateY(${title.translateY}px)` }}>
            <ArabicText size={92} weight={900} color={C.green}>BotBudget</ArabicText>
          </div>

          <div style={{ opacity: sub.opacity, transform: `translateY(${sub.translateY}px)`, marginTop: 16 }}>
            <ArabicText size={78} weight={700}>بيعمله عنك!</ArabicText>
          </div>

          <div
            style={{
              position: "absolute",
              top: 28,
              left: 28,
              fontSize: 52,
              opacity: telegram,
            }}
          >
            ✈️
          </div>
        </Card>
      </div>
    </AbsoluteFill>
  );
};

// ════════════════════════════════════════════════════════════
// المشهد 3 — Feature: تسجيل سريع (10-15 ثواني)
// ════════════════════════════════════════════════════════════
const ChatBubble: React.FC<{
  text: string;
  side: "right" | "left";
  color: string;
  frame: number;
  delay: number;
}> = ({ text, side, color, frame, delay }) => {
  const { fps } = useVideoConfig();
  const sc = spring({ frame: frame - delay, fps, config: { damping: 16, stiffness: 130 } });
  const op = fadeIn(frame, delay, 10);

  return (
    <div
      style={{
        display: "flex",
        justifyContent: side === "right" ? "flex-end" : "flex-start",
        opacity: op,
        transform: `scale(${sc})`,
        transformOrigin: side === "right" ? "right center" : "left center",
      }}
    >
      <div
        style={{
          background: color,
          borderRadius: side === "right" ? "28px 28px 8px 28px" : "28px 28px 28px 8px",
          padding: "24px 36px",
          maxWidth: "80%",
          direction: "rtl",
          fontFamily: FONT,
          fontSize: 48,
          fontWeight: 600,
          color: C.white,
          lineHeight: 1.5,
        }}
      >
        {text}
      </div>
    </div>
  );
};

const Scene3: React.FC = () => {
  const frame = useCurrentFrame();

  const slideX = interpolate(frame, [0, 18], [120, 0], {
    extrapolateLeft: "clamp",
    extrapolateRight: "clamp",
  });
  const op = interpolate(frame, [0, 18], [0, 1], {
    extrapolateLeft: "clamp",
    extrapolateRight: "clamp",
  });

  const caption = slideUp(frame, 110, 15);

  return (
    <AbsoluteFill
      style={{
        background: C.bg,
        alignItems: "center",
        justifyContent: "center",
        flexDirection: "column",
        gap: 32,
        padding: "0 60px",
        opacity: op,
        transform: `translateX(${slideX}px)`,
      }}
    >
      <GlowOrb x={540} y={900} color={C.darkGreen} size={600} />

      <ArabicText size={68} weight={700} color={C.gray}>سجّل مصاريفك فوراً 💬</ArabicText>

      <div style={{ display: "flex", flexDirection: "column", gap: 28, width: "100%" }}>
        <ChatBubble
          frame={frame}
          delay={20}
          side="right"
          color={C.card}
          text={"صرفت 50 ريال كافيه ☕"}
        />
        <ChatBubble
          frame={frame}
          delay={44}
          side="left"
          color={C.darkGreen}
          text={"✅ تم التسجيل!\nالإجمالي اليوم: 120 ريال"}
        />
      </div>

      <div style={{ opacity: caption.opacity, transform: `translateY(${caption.translateY}px)` }}>
        <ArabicText size={52} color={C.accent} weight={600}>
          سجّل بـ رسالة واحدة بس! 🚀
        </ArabicText>
      </div>
    </AbsoluteFill>
  );
};

// ════════════════════════════════════════════════════════════
// المشهد 4 — Feature: تقارير (15-20 ثواني)
// ════════════════════════════════════════════════════════════
const ReportRow: React.FC<{
  emoji: string;
  label: string;
  amount: string;
  frame: number;
  delay: number;
  highlight?: boolean;
}> = ({ emoji, label, amount, frame, delay, highlight }) => {
  const op = fadeIn(frame, delay, 10);
  const slide = slideUp(frame, delay, 12);

  return (
    <div
      style={{
        display: "flex",
        justifyContent: "space-between",
        alignItems: "center",
        opacity: op,
        transform: `translateY(${slide.translateY}px)`,
        padding: "18px 0",
        borderBottom: highlight ? "none" : `1px solid ${C.green}22`,
        direction: "rtl",
      }}
    >
      <div style={{ display: "flex", alignItems: "center", gap: 20, direction: "rtl" }}>
        <span style={{ fontSize: 48 }}>{emoji}</span>
        <span style={{ fontFamily: FONT, fontSize: 48, color: highlight ? C.green : C.white, fontWeight: 600 }}>
          {label}
        </span>
      </div>
      <span
        style={{
          fontFamily: FONT,
          fontSize: 48,
          color: highlight ? C.green : C.gray,
          fontWeight: highlight ? 900 : 600,
        }}
      >
        {amount}
      </span>
    </div>
  );
};

const Scene4: React.FC = () => {
  const frame = useCurrentFrame();
  const title = slideUp(frame, 0, 15);

  return (
    <AbsoluteFill
      style={{
        background: C.bg,
        alignItems: "center",
        justifyContent: "center",
        flexDirection: "column",
        gap: 40,
        padding: "0 60px",
      }}
    >
      <GlowOrb x={900} y={500} color={C.accent} size={400} />

      <div style={{ opacity: title.opacity, transform: `translateY(${title.translateY}px)` }}>
        <ArabicText size={76} weight={900}>📊 تقرير مارس</ArabicText>
      </div>

      <Card style={{ width: "100%" }}>
        <ReportRow emoji="🍕" label="أكل" amount="450 ريال" frame={frame} delay={20} />
        <ReportRow emoji="🚗" label="مواصلات" amount="200 ريال" frame={frame} delay={32} />
        <ReportRow emoji="☕" label="كافيه" amount="150 ريال" frame={frame} delay={44} />
        <div style={{ margin: "12px 0", borderTop: `2px solid ${C.green}55` }} />
        <ReportRow
          emoji="📌"
          label="الإجمالي"
          amount="800 ريال"
          frame={frame}
          delay={60}
          highlight
        />
      </Card>
    </AbsoluteFill>
  );
};

// ════════════════════════════════════════════════════════════
// المشهد 5 — السعر / مجاني (20-25 ثواني)
// ════════════════════════════════════════════════════════════
const Scene5: React.FC = () => {
  const frame = useCurrentFrame();
  const { fps } = useVideoConfig();

  const sc = spring({ frame, fps, config: { damping: 12, stiffness: 90 } });
  const pulse = 1 + 0.025 * Math.sin((frame / 30) * Math.PI * 2 * 1.5);

  const emoji = fadeIn(frame, 5, 12);
  const line1 = slideUp(frame, 18, 15);
  const line2 = slideUp(frame, 32, 15);
  const divider = fadeIn(frame, 55, 15);
  const pro = fadeIn(frame, 65, 15);

  return (
    <AbsoluteFill
      style={{
        background: C.bg,
        alignItems: "center",
        justifyContent: "center",
        flexDirection: "column",
        gap: 40,
        padding: "0 80px",
      }}
    >
      <GlowOrb x={540} y={960} color={C.green} size={800} />

      <div
        style={{
          transform: `scale(${interpolate(sc, [0, 1], [0.8, 1]) * pulse})`,
          width: "100%",
        }}
      >
        <Card glow style={{ textAlign: "center" }}>
          <div style={{ opacity: emoji.opacity, fontSize: 130, marginBottom: 28 }}>🆓</div>

          <div style={{ opacity: line1.opacity, transform: `translateY(${line1.translateY}px)` }}>
            <ArabicText size={90} weight={900} color={C.green}>مجاني تماماً</ArabicText>
          </div>

          <div style={{ opacity: line2.opacity, transform: `translateY(${line2.translateY}px)`, marginTop: 16 }}>
            <ArabicText size={52} color={C.gray} weight={500}>
              ابدأ دلوقتي بدون بطاقة
            </ArabicText>
          </div>

          <div
            style={{
              margin: "36px 0",
              height: 2,
              background: `${C.green}44`,
              borderRadius: 2,
              opacity: divider,
            }}
          />

          <div style={{ opacity: pro.opacity }}>
            <ArabicText size={44} color={C.gray} weight={500}>
              🔒 خطة Pro قريباً
            </ArabicText>
          </div>
        </Card>
      </div>
    </AbsoluteFill>
  );
};

// ════════════════════════════════════════════════════════════
// المشهد 6 — CTA (25-30 ثواني)
// ════════════════════════════════════════════════════════════
const Confetti: React.FC<{ frame: number }> = ({ frame }) => {
  const particles = Array.from({ length: 18 }, (_, i) => {
    const angle = (i / 18) * Math.PI * 2;
    const speed = 4 + (i % 3) * 2;
    const x = 540 + Math.cos(angle) * speed * frame * 0.6;
    const y = 960 + Math.sin(angle) * speed * frame * 0.6;
    const op = Math.max(0, 1 - frame / 90);
    const colors = [C.green, C.accent, "#FFD700", C.white];
    return { x, y, op, color: colors[i % colors.length] };
  });

  return (
    <>
      {particles.map((p, i) => (
        <div
          key={i}
          style={{
            position: "absolute",
            left: p.x,
            top: p.y,
            width: 14,
            height: 14,
            borderRadius: "50%",
            background: p.color,
            opacity: p.op,
          }}
        />
      ))}
    </>
  );
};

const Scene6: React.FC = () => {
  const frame = useCurrentFrame();
  const { fps } = useVideoConfig();

  const sc = spring({ frame, fps, config: { damping: 16, stiffness: 100 } });
  const zoomOut = interpolate(sc, [0, 1], [1.2, 1]);

  const shake = Math.sin(frame * 0.4) * (frame > 120 ? 6 : 0);

  const title = slideUp(frame, 10, 15);
  const btn = slideUp(frame, 30, 15);
  const sub = fadeIn(frame, 55, 15);

  const blink =
    frame > 110 ? Math.floor((frame - 110) / 10) % 2 === 0 ? 1 : 0.4 : 1;

  return (
    <AbsoluteFill
      style={{
        background: `linear-gradient(180deg, ${C.bg} 0%, ${C.gradientEnd} 100%)`,
        alignItems: "center",
        justifyContent: "center",
        flexDirection: "column",
        gap: 44,
        padding: "0 70px",
        transform: `scale(${zoomOut})`,
      }}
    >
      <GlowOrb x={540} y={700} color={C.green} size={900} />

      <Confetti frame={frame} />

      <div
        style={{
          fontSize: 150,
          transform: `translateX(${shake}px)`,
          filter: "drop-shadow(0 0 30px rgba(0,212,110,0.6))",
        }}
      >
        🚀
      </div>

      <div style={{ opacity: title.opacity, transform: `translateY(${title.translateY}px)` }}>
        <ArabicText size={100} weight={900}>ابدأ دلوقتي!</ArabicText>
      </div>

      <div
        style={{
          opacity: btn.opacity * blink,
          transform: `translateY(${btn.translateY}px)`,
          width: "100%",
        }}
      >
        <div
          style={{
            background: C.green,
            borderRadius: 28,
            padding: "40px 48px",
            display: "flex",
            alignItems: "center",
            justifyContent: "center",
            gap: 20,
            direction: "rtl",
          }}
        >
          <span style={{ fontSize: 52 }}>✈️</span>
          <span
            style={{
              fontFamily: FONT,
              fontSize: 52,
              fontWeight: 900,
              color: "#000000",
              direction: "ltr",
            }}
          >
            @Mybudgettracke_bot
          </span>
        </div>
      </div>

      <div style={{ opacity: sub.opacity }}>
        <ArabicText size={44} color={C.gray} weight={500}>
          مجاناً • بدون تسجيل • فوري
        </ArabicText>
      </div>
    </AbsoluteFill>
  );
};

// ════════════════════════════════════════════════════════════
// الـ Root Component
// ════════════════════════════════════════════════════════════
export const BotBudgetAd: React.FC = () => {
  const SCENE = 75; // 2.5 ثانية × 30fps

  return (
    <AbsoluteFill style={{ background: C.bg }}>
      <Sequence from={0} durationInFrames={SCENE}>
        <Scene1 />
      </Sequence>
      <Sequence from={SCENE} durationInFrames={SCENE}>
        <Scene2 />
      </Sequence>
      <Sequence from={SCENE * 2} durationInFrames={SCENE}>
        <Scene3 />
      </Sequence>
      <Sequence from={SCENE * 3} durationInFrames={SCENE}>
        <Scene4 />
      </Sequence>
      <Sequence from={SCENE * 4} durationInFrames={SCENE}>
        <Scene5 />
      </Sequence>
      <Sequence from={SCENE * 5} durationInFrames={SCENE}>
        <Scene6 />
      </Sequence>
    </AbsoluteFill>
  );
};
