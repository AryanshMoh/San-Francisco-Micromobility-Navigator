import { useCallback, useEffect, useRef, useState } from 'react';

interface IntroScreenProps {
  onEnter: () => void;
}

const TRANSITION_DURATION_MS = 700;

function BikeIcon() {
  return (
    <svg
      className="intro-screen__bike-icon"
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

export default function IntroScreen({ onEnter }: IntroScreenProps) {
  const [isEntering, setIsEntering] = useState(false);
  const timerRef = useRef<number | undefined>(undefined);

  const handleEnter = useCallback(() => {
    if (isEntering) {
      return;
    }

    setIsEntering(true);
    timerRef.current = window.setTimeout(onEnter, TRANSITION_DURATION_MS);
  }, [isEntering, onEnter]);

  useEffect(() => {
    return () => {
      window.clearTimeout(timerRef.current);
    };
  }, []);

  useEffect(() => {
    const onKeyDown = (event: KeyboardEvent) => {
      if (event.key === 'Enter' || event.key === ' ') {
        event.preventDefault();
        handleEnter();
      }
    };

    window.addEventListener('keydown', onKeyDown);
    return () => {
      window.removeEventListener('keydown', onKeyDown);
    };
  }, [handleEnter]);

  return (
    <section
      className={`intro-screen${isEntering ? ' intro-screen--entering' : ''}`}
      aria-label="Site intro"
    >
      <div className="intro-screen__mesh" aria-hidden="true" />
      <div className="intro-screen__grain" aria-hidden="true" />
      <div className="intro-screen__orbit intro-screen__orbit--one" aria-hidden="true" />
      <div className="intro-screen__orbit intro-screen__orbit--two" aria-hidden="true" />

      <div className="intro-screen__content">
        <div className="intro-screen__top-emblem">
          <div className="intro-screen__emblem">
            <BikeIcon />
          </div>
        </div>

        <p className="intro-screen__kicker">San Francisco Micromobility</p>

        <h1 className="intro-screen__title">
          Ride The City
          <br />
          With Precision
        </h1>

        <button type="button" className="intro-screen__enter-button" onClick={handleEnter}>
          <span>Enter Site</span>
          <span className="intro-screen__enter-glyph">-&gt;</span>
        </button>

        <p className="intro-screen__hint">Press Enter to continue</p>
      </div>
    </section>
  );
}
