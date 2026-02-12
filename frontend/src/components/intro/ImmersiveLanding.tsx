import { CSSProperties, useEffect, useMemo, useState } from 'react';

interface ImmersiveLandingProps {
  onNavigate: () => void;
  isExiting?: boolean;
}

interface DriftOrb {
  id: number;
  left: number;
  bottom: number;
  size: number;
  delay: number;
  duration: number;
}

const AMBIENT_LABELS = ['Live Lane Pulse', 'Fog Layer Drift', 'Night Route Glow'];

function BikeIcon({ className }: { className?: string }) {
  return (
    <svg
      className={className}
      viewBox="0 0 64 64"
      fill="none"
      xmlns="http://www.w3.org/2000/svg"
      role="presentation"
      aria-hidden="true"
    >
      <circle cx="16" cy="44" r="10" />
      <circle cx="48" cy="44" r="10" />
      <path d="M16 44L26 24H37L48 44" />
      <path d="M24 28H33L28 16H22" />
      <path d="M34 24L39 16H45" />
      <path d="M28 24L16 44" />
    </svg>
  );
}

interface Point {
  x: number;
  y: number;
}

const CRANK_CENTER: Point = { x: 248, y: 178 };
const PEDAL_RADIUS = 24;
const PEDAL_CYCLE_MS = 980;

const FRONT_HIP: Point = { x: 229, y: 140 };
const REAR_HIP: Point = { x: 221, y: 139 };
const THIGH_LENGTH = 56;
const SHIN_LENGTH = 54;

const FRONT_SHOULDER: Point = { x: 248, y: 109 };
const REAR_SHOULDER: Point = { x: 241, y: 108 };
const FRONT_GRIP: Point = { x: 308, y: 114 };
const REAR_GRIP: Point = { x: 302, y: 116 };
const UPPER_ARM_LENGTH = 35;
const FOREARM_LENGTH = 31;

const clamp = (value: number, min: number, max: number): number => Math.min(max, Math.max(min, value));

function pointOnCircle(center: Point, radius: number, angle: number): Point {
  return {
    x: center.x + Math.cos(angle) * radius,
    y: center.y + Math.sin(angle) * radius,
  };
}

function solveKnee(
  hip: Point,
  foot: Point,
  upperLength: number,
  lowerLength: number,
  bendDirection: 1 | -1,
): Point {
  const dx = foot.x - hip.x;
  const dy = foot.y - hip.y;
  const distance = Math.hypot(dx, dy);
  const safeDistance = clamp(distance, Math.abs(upperLength - lowerLength) + 0.001, upperLength + lowerLength - 0.001);

  const along = (upperLength ** 2 - lowerLength ** 2 + safeDistance ** 2) / (2 * safeDistance);
  const height = Math.sqrt(Math.max(upperLength ** 2 - along ** 2, 0));

  const ux = dx / safeDistance;
  const uy = dy / safeDistance;

  const midX = hip.x + ux * along;
  const midY = hip.y + uy * along;

  const perpX = -uy;
  const perpY = ux;

  return {
    x: midX + bendDirection * perpX * height,
    y: midY + bendDirection * perpY * height,
  };
}

function radiansToDegrees(radians: number): number {
  return (radians * 180) / Math.PI;
}

function WomanCyclistIllustration({ className }: { className?: string }) {
  const [crankAngle, setCrankAngle] = useState(0);

  useEffect(() => {
    const mediaQuery = window.matchMedia('(prefers-reduced-motion: reduce)');
    let frameId = 0;
    let startTime = 0;

    const tick = (timestamp: number) => {
      if (mediaQuery.matches) {
        setCrankAngle(0);
        return;
      }

      if (startTime === 0) {
        startTime = timestamp;
      }

      const elapsed = timestamp - startTime;
      const phase = (elapsed % PEDAL_CYCLE_MS) / PEDAL_CYCLE_MS;
      setCrankAngle(phase * Math.PI * 2);
      frameId = window.requestAnimationFrame(tick);
    };

    const restart = () => {
      window.cancelAnimationFrame(frameId);
      startTime = 0;

      if (mediaQuery.matches) {
        setCrankAngle(0);
        return;
      }

      frameId = window.requestAnimationFrame(tick);
    };

    frameId = window.requestAnimationFrame(tick);

    if (typeof mediaQuery.addEventListener === 'function') {
      mediaQuery.addEventListener('change', restart);
    } else {
      mediaQuery.addListener(restart);
    }

    return () => {
      window.cancelAnimationFrame(frameId);
      if (typeof mediaQuery.removeEventListener === 'function') {
        mediaQuery.removeEventListener('change', restart);
      } else {
        mediaQuery.removeListener(restart);
      }
    };
  }, []);

  const frontPedal = useMemo(() => pointOnCircle(CRANK_CENTER, PEDAL_RADIUS, crankAngle), [crankAngle]);
  const rearPedal = useMemo(() => pointOnCircle(CRANK_CENTER, PEDAL_RADIUS, crankAngle + Math.PI), [crankAngle]);

  const frontKnee = useMemo(
    () => solveKnee(FRONT_HIP, frontPedal, THIGH_LENGTH, SHIN_LENGTH, -1),
    [frontPedal],
  );
  const rearKnee = useMemo(
    () => solveKnee(REAR_HIP, rearPedal, THIGH_LENGTH, SHIN_LENGTH, 1),
    [rearPedal],
  );

  const frontElbow = useMemo(
    () => solveKnee(FRONT_SHOULDER, FRONT_GRIP, UPPER_ARM_LENGTH, FOREARM_LENGTH, 1),
    [],
  );
  const rearElbow = useMemo(
    () => solveKnee(REAR_SHOULDER, REAR_GRIP, UPPER_ARM_LENGTH, FOREARM_LENGTH, 1),
    [],
  );

  const frontShoeRotation = radiansToDegrees(crankAngle + Math.PI / 2);
  const rearShoeRotation = radiansToDegrees(crankAngle + Math.PI / 2 + Math.PI);

  return (
    <svg
      className={className}
      viewBox="0 0 520 290"
      xmlns="http://www.w3.org/2000/svg"
      role="presentation"
      aria-hidden="true"
    >
      <g className="immersive-landing__bike-shadow">
        <ellipse cx="258" cy="224" rx="195" ry="17" />
      </g>

      <g className="immersive-landing__wheel immersive-landing__wheel--rear">
        <circle className="immersive-landing__wheel-rim" cx="126" cy="190" r="56" />
        <circle className="immersive-landing__wheel-core" cx="126" cy="190" r="8.5" />
        <g className="immersive-landing__wheel-spokes">
          <line x1="126" y1="134" x2="126" y2="246" />
          <line x1="70" y1="190" x2="182" y2="190" />
          <line x1="88" y1="152" x2="164" y2="228" />
          <line x1="164" y1="152" x2="88" y2="228" />
        </g>
      </g>

      <g className="immersive-landing__wheel immersive-landing__wheel--front">
        <circle className="immersive-landing__wheel-rim" cx="378" cy="190" r="56" />
        <circle className="immersive-landing__wheel-core" cx="378" cy="190" r="8.5" />
        <g className="immersive-landing__wheel-spokes">
          <line x1="378" y1="134" x2="378" y2="246" />
          <line x1="322" y1="190" x2="434" y2="190" />
          <line x1="340" y1="152" x2="416" y2="228" />
          <line x1="416" y1="152" x2="340" y2="228" />
        </g>
      </g>

      <g className="immersive-landing__leg-set immersive-landing__leg-set--rear">
        <line className="immersive-landing__limb-segment immersive-landing__limb-segment--thigh" x1={REAR_HIP.x} y1={REAR_HIP.y} x2={rearKnee.x} y2={rearKnee.y} />
        <line className="immersive-landing__limb-segment immersive-landing__limb-segment--shin" x1={rearKnee.x} y1={rearKnee.y} x2={rearPedal.x} y2={rearPedal.y} />
        <circle className="immersive-landing__joint" cx={rearKnee.x} cy={rearKnee.y} r="4.6" />
      </g>

      <g className="immersive-landing__bike-frame">
        <line x1="126" y1="190" x2="209" y2="114" />
        <line x1="209" y1="114" x2="248" y2="178" />
        <line x1="248" y1="178" x2="171" y2="178" />
        <line x1="171" y1="178" x2="209" y2="114" />
        <line x1="248" y1="178" x2="320" y2="128" />
        <line x1="320" y1="128" x2="378" y2="190" />
        <line x1="209" y1="114" x2="320" y2="128" />
        <line x1="209" y1="114" x2="210" y2="100" />
      </g>

      <rect className="immersive-landing__seat" x="194" y="101" width="33" height="8" rx="4" />
      <g className="immersive-landing__handlebar">
        <line x1="320" y1="128" x2="347" y2="118" />
        <line x1="320" y1="128" x2="315" y2="99" />
      </g>

      <g className="immersive-landing__arm-set immersive-landing__arm-set--rear">
        <line className="immersive-landing__limb-segment immersive-landing__limb-segment--arm" x1={REAR_SHOULDER.x} y1={REAR_SHOULDER.y} x2={rearElbow.x} y2={rearElbow.y} />
        <line className="immersive-landing__limb-segment immersive-landing__limb-segment--arm" x1={rearElbow.x} y1={rearElbow.y} x2={REAR_GRIP.x} y2={REAR_GRIP.y} />
        <circle className="immersive-landing__joint" cx={rearElbow.x} cy={rearElbow.y} r="4.2" />
      </g>

      <g className="immersive-landing__crankset">
        <line className="immersive-landing__crank-arm immersive-landing__crank-arm--rear" x1={CRANK_CENTER.x} y1={CRANK_CENTER.y} x2={rearPedal.x} y2={rearPedal.y} />
        <line className="immersive-landing__crank-arm immersive-landing__crank-arm--front" x1={CRANK_CENTER.x} y1={CRANK_CENTER.y} x2={frontPedal.x} y2={frontPedal.y} />
        <circle className="immersive-landing__crank-hub" cx={CRANK_CENTER.x} cy={CRANK_CENTER.y} r="9" />

        <g className="immersive-landing__pedal immersive-landing__pedal--rear" transform={`translate(${rearPedal.x} ${rearPedal.y}) rotate(${rearShoeRotation})`}>
          <rect x="-8" y="-3.2" width="16" height="6.4" rx="2.2" />
        </g>
        <g className="immersive-landing__pedal immersive-landing__pedal--front" transform={`translate(${frontPedal.x} ${frontPedal.y}) rotate(${frontShoeRotation})`}>
          <rect x="-8" y="-3.2" width="16" height="6.4" rx="2.2" />
        </g>
      </g>

      <g className="immersive-landing__rider-core">
        <path className="immersive-landing__hair-back" d="M250 72C244 86 245 100 253 109C266 105 272 94 271 82C269 73 262 66 250 72Z" />
        <ellipse className="immersive-landing__head" cx="276" cy="83" rx="13.2" ry="15" transform="rotate(-17 276 83)" />
        <path className="immersive-landing__helmet" d="M261 81C264 66 281 58 295 66C301 69 305 75 304 84H266C264 83 262 82 261 81Z" />
        <circle className="immersive-landing__pony-tail" cx="252" cy="99" r="7.6" />
        <rect className="immersive-landing__neck" x="266" y="96" width="8.8" height="11.5" rx="4.2" />
        <path className="immersive-landing__torso" d="M229 105C242 95 261 95 276 106L289 132C280 141 266 145 249 143L231 119C227 114 227 108 229 105Z" />
        <path className="immersive-landing__shorts" d="M232 136C248 132 263 134 272 146L260 160C246 160 236 154 228 145Z" />
      </g>

      <g className="immersive-landing__arm-set immersive-landing__arm-set--front">
        <line className="immersive-landing__limb-segment immersive-landing__limb-segment--arm" x1={FRONT_SHOULDER.x} y1={FRONT_SHOULDER.y} x2={frontElbow.x} y2={frontElbow.y} />
        <line className="immersive-landing__limb-segment immersive-landing__limb-segment--arm" x1={frontElbow.x} y1={frontElbow.y} x2={FRONT_GRIP.x} y2={FRONT_GRIP.y} />
        <circle className="immersive-landing__joint" cx={frontElbow.x} cy={frontElbow.y} r="4.2" />
      </g>

      <g className="immersive-landing__leg-set immersive-landing__leg-set--front">
        <line className="immersive-landing__limb-segment immersive-landing__limb-segment--thigh" x1={FRONT_HIP.x} y1={FRONT_HIP.y} x2={frontKnee.x} y2={frontKnee.y} />
        <line className="immersive-landing__limb-segment immersive-landing__limb-segment--shin" x1={frontKnee.x} y1={frontKnee.y} x2={frontPedal.x} y2={frontPedal.y} />
        <circle className="immersive-landing__joint" cx={frontKnee.x} cy={frontKnee.y} r="4.8" />

        <g className="immersive-landing__shoe immersive-landing__shoe--rear" transform={`translate(${rearPedal.x} ${rearPedal.y}) rotate(${rearShoeRotation})`}>
          <ellipse cx="0" cy="0" rx="10.8" ry="4.3" />
        </g>
        <g className="immersive-landing__shoe immersive-landing__shoe--front" transform={`translate(${frontPedal.x} ${frontPedal.y}) rotate(${frontShoeRotation})`}>
          <ellipse cx="0" cy="0" rx="11.4" ry="4.6" />
        </g>
      </g>
    </svg>
  );
}

export default function ImmersiveLanding({ onNavigate, isExiting = false }: ImmersiveLandingProps) {
  const [parallax, setParallax] = useState({ x: 0, y: 0 });

  const driftOrbs = useMemo<DriftOrb[]>(
    () =>
      Array.from({ length: 16 }, (_, index) => {
        const seed = index + 1;
        return {
          id: seed,
          left: 6 + (seed * 6.4) % 88,
          bottom: 8 + (seed * 9.7) % 72,
          size: 4 + (seed * 7) % 14,
          delay: seed * 0.2,
          duration: 10 + (seed * 1.8) % 12,
        };
      }),
    [],
  );

  useEffect(() => {
    const onKeyDown = (event: KeyboardEvent) => {
      if (isExiting) {
        return;
      }

      if (event.key === 'Enter' || event.key.toLowerCase() === 'n') {
        event.preventDefault();
        onNavigate();
      }
    };

    window.addEventListener('keydown', onKeyDown);
    return () => {
      window.removeEventListener('keydown', onKeyDown);
    };
  }, [isExiting, onNavigate]);

  const cssVars = {
    '--parallax-x': `${parallax.x}px`,
    '--parallax-y': `${parallax.y}px`,
  } as CSSProperties & Record<'--parallax-x' | '--parallax-y', string>;

  return (
    <section
      className={`immersive-landing${isExiting ? ' immersive-landing--exiting' : ''}`}
      aria-label="Immersive city intro"
      style={cssVars}
      onMouseMove={(event) => {
        const x = ((event.clientX / window.innerWidth) * 2 - 1) * 18;
        const y = ((event.clientY / window.innerHeight) * 2 - 1) * 14;
        setParallax({ x, y });
      }}
      onMouseLeave={() => {
        setParallax({ x: 0, y: 0 });
      }}
    >
      <div className="immersive-landing__mesh" aria-hidden="true" />
      <div className="immersive-landing__grain" aria-hidden="true" />
      <div className="immersive-landing__vignette" aria-hidden="true" />

      <div className="immersive-landing__drift" aria-hidden="true">
        {driftOrbs.map((orb) => (
          <span
            key={orb.id}
            className="immersive-landing__orb"
            style={{
              left: `${orb.left}%`,
              bottom: `${orb.bottom}%`,
              width: `${orb.size}px`,
              height: `${orb.size}px`,
              animationDelay: `${orb.delay}s`,
              animationDuration: `${orb.duration}s`,
            }}
          />
        ))}
      </div>

      <header className="immersive-landing__header">
        <div className="immersive-landing__monogram" aria-hidden="true">
          <BikeIcon className="immersive-landing__monogram-icon" />
        </div>

        <button
          type="button"
          className="immersive-landing__navigate"
          onClick={onNavigate}
          disabled={isExiting}
        >
          <span>Go to Navigation</span>
          <span className="immersive-landing__navigate-emblem" aria-hidden="true">
            <BikeIcon className="immersive-landing__navigate-icon" />
          </span>
        </button>
      </header>

      <main className="immersive-landing__content">
        <p className="immersive-landing__eyebrow">San Francisco Ride</p>
        <h1 className="immersive-landing__title">Traffic is Optional</h1>
        <p className="immersive-landing__description">
          A focused first frame for city riders. Atmospheric, alert, and tuned for movement before
          your route begins.
        </p>

        <div className="immersive-landing__labels" role="list" aria-label="Ambient highlights">
          {AMBIENT_LABELS.map((label) => (
            <span className="immersive-landing__label" key={label} role="listitem">
              {label}
            </span>
          ))}
        </div>
      </main>

      <div className="immersive-landing__scene" aria-hidden="true">
        <div className="immersive-landing__skyline" />
        <div className="immersive-landing__road" />
        <div className="immersive-landing__trail" />

        <div className="immersive-landing__cyclist">
          <WomanCyclistIllustration className="immersive-landing__cyclist-svg" />
        </div>
      </div>

      <p className="immersive-landing__hint">Press N or Enter to open navigation</p>
    </section>
  );
}
