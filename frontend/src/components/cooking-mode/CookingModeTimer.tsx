import React, { useState, useEffect, useRef, useCallback } from 'react';
import type { DetectedTimer, DonenessCue } from '../../utils/timerDetection';
import { notifyWarning } from '../../utils/haptics';

interface CookingModeTimerProps {
  timer: DetectedTimer;
  cues: DonenessCue[];
  stepNumber: number;
}

type TimerStatus = 'idle' | 'running' | 'paused' | 'completed';

function formatTime(seconds: number): string {
  const hrs = Math.floor(seconds / 3600);
  const mins = Math.floor((seconds % 3600) / 60);
  const secs = seconds % 60;

  if (hrs > 0) {
    return `${hrs}:${mins.toString().padStart(2, '0')}:${secs.toString().padStart(2, '0')}`;
  }
  return `${mins}:${secs.toString().padStart(2, '0')}`;
}

function playBeep() {
  try {
    const ctx = new AudioContext();
    const oscillator = ctx.createOscillator();
    const gain = ctx.createGain();
    oscillator.connect(gain);
    gain.connect(ctx.destination);
    oscillator.frequency.value = 880;
    oscillator.type = 'sine';
    gain.gain.value = 0.3;

    oscillator.start();
    setTimeout(() => { gain.gain.value = 0; }, 150);
    setTimeout(() => { gain.gain.value = 0.3; }, 250);
    setTimeout(() => { gain.gain.value = 0; }, 400);
    setTimeout(() => { gain.gain.value = 0.3; }, 500);
    setTimeout(() => {
      oscillator.stop();
      ctx.close();
    }, 650);
  } catch (error) {
    console.error('Failed to play timer beep:', error);
  }
}

// Get the adjustment step size based on total duration
function getAdjustStep(totalSeconds: number): number {
  if (totalSeconds >= 3600) return 300; // 5 min steps for hours
  if (totalSeconds >= 600) return 60;   // 1 min steps for 10+ min
  if (totalSeconds >= 60) return 30;    // 30s steps for 1-10 min
  return 10;                             // 10s steps for < 1 min
}

function formatAdjustLabel(stepSeconds: number): string {
  if (stepSeconds >= 60) return `${stepSeconds / 60}m`;
  return `${stepSeconds}s`;
}

const CookingModeTimer: React.FC<CookingModeTimerProps> = ({ timer, cues }) => {
  const [status, setStatus] = useState<TimerStatus>('idle');
  const [adjustedDuration, setAdjustedDuration] = useState(timer.durationSeconds);
  const [remaining, setRemaining] = useState(timer.durationSeconds);
  const startTimeRef = useRef<number | null>(null);
  const pausedRemainingRef = useRef(timer.durationSeconds);
  const intervalRef = useRef<ReturnType<typeof setInterval> | null>(null);

  const adjustStep = getAdjustStep(timer.durationSeconds);

  const clearTimer = useCallback(() => {
    if (intervalRef.current) {
      clearInterval(intervalRef.current);
      intervalRef.current = null;
    }
  }, []);

  const tick = useCallback(() => {
    if (!startTimeRef.current) return;
    const elapsed = Math.floor((Date.now() - startTimeRef.current) / 1000);
    const newRemaining = Math.max(0, pausedRemainingRef.current - elapsed);
    setRemaining(newRemaining);

    if (newRemaining <= 0) {
      clearTimer();
      setStatus('completed');
      playBeep();
      notifyWarning(); // Warning not success — it's a "check" reminder
    }
  }, [clearTimer]);

  const start = useCallback(() => {
    pausedRemainingRef.current = adjustedDuration;
    setRemaining(adjustedDuration);
    startTimeRef.current = Date.now();
    setStatus('running');
    intervalRef.current = setInterval(tick, 250);
  }, [tick, adjustedDuration]);

  const pause = useCallback(() => {
    clearTimer();
    pausedRemainingRef.current = remaining;
    startTimeRef.current = null;
    setStatus('paused');
  }, [clearTimer, remaining]);

  const resume = useCallback(() => {
    startTimeRef.current = Date.now();
    setStatus('running');
    intervalRef.current = setInterval(tick, 250);
  }, [tick]);

  const reset = useCallback(() => {
    clearTimer();
    startTimeRef.current = null;
    pausedRemainingRef.current = adjustedDuration;
    setRemaining(adjustedDuration);
    setStatus('idle');
  }, [clearTimer, adjustedDuration]);

  const adjustTime = useCallback((delta: number) => {
    setAdjustedDuration(prev => {
      const next = Math.max(adjustStep, prev + delta);
      setRemaining(next);
      pausedRemainingRef.current = next;
      return next;
    });
  }, [adjustStep]);

  useEffect(() => {
    return clearTimer;
  }, [clearTimer]);

  const isCompleted = status === 'completed';
  const isIdle = status === 'idle';
  const hasCues = cues.length > 0;

  return (
    <div className={`mt-4 p-4 rounded-xl border ${isCompleted ? 'bg-amber-50 border-amber-300' : 'bg-gray-50 border-gray-200'}`}>
      {/* Header */}
      <div className="flex items-center gap-2 mb-1">
        <svg className="w-4 h-4 text-gray-500" fill="none" stroke="currentColor" viewBox="0 0 24 24">
          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 8v4l3 3m6-3a9 9 0 11-18 0 9 9 0 0118 0z" />
        </svg>
        <span className="text-sm text-gray-500">
          {timer.isRange ? `Around ${timer.label}` : timer.label}
        </span>
      </div>

      {/* Doneness cues — the real signal */}
      {hasCues && (
        <div className="mb-3 flex flex-wrap gap-2">
          {cues.map((cue, i) => (
            <span
              key={i}
              className={`inline-flex items-center gap-1 text-sm px-2.5 py-1 rounded-full ${isCompleted ? 'bg-amber-100 text-amber-800 font-medium' : 'bg-blue-50 text-blue-700'}`}
            >
              <svg className="w-3.5 h-3.5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M15 12a3 3 0 11-6 0 3 3 0 016 0z" />
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M2.458 12C3.732 7.943 7.523 5 12 5c4.478 0 8.268 2.943 9.542 7-1.274 4.057-5.064 7-9.542 7-4.477 0-8.268-2.943-9.542-7z" />
              </svg>
              {cue.text}
            </span>
          ))}
        </div>
      )}

      {/* Timer display */}
      <div className="flex items-center justify-center gap-3 my-3">
        {/* Minus button — only when idle */}
        {isIdle && (
          <button
            onClick={() => adjustTime(-adjustStep)}
            disabled={adjustedDuration <= adjustStep}
            className="w-10 h-10 rounded-full border border-gray-300 flex items-center justify-center text-gray-500 active:scale-95 disabled:opacity-30"
          >
            <span className="text-lg font-bold">−</span>
          </button>
        )}

        <div className="text-center">
          <div
            className={`text-4xl font-mono font-bold ${isCompleted ? 'text-amber-600' : ''}`}
            style={!isCompleted ? { color: '#1c120d' } : undefined}
          >
            {isCompleted ? 'Time to check!' : formatTime(remaining)}
          </div>
          {isIdle && adjustedDuration !== timer.durationSeconds && (
            <button
              onClick={() => {
                setAdjustedDuration(timer.durationSeconds);
                setRemaining(timer.durationSeconds);
                pausedRemainingRef.current = timer.durationSeconds;
              }}
              className="text-xs text-gray-400 hover:text-gray-600 mt-1"
            >
              Reset to {formatTime(timer.durationSeconds)}
            </button>
          )}
        </div>

        {/* Plus button — only when idle */}
        {isIdle && (
          <button
            onClick={() => adjustTime(adjustStep)}
            className="w-10 h-10 rounded-full border border-gray-300 flex items-center justify-center text-gray-500 active:scale-95"
          >
            <span className="text-lg font-bold">+</span>
          </button>
        )}
      </div>

      {/* Adjust step hint */}
      {isIdle && (
        <p className="text-xs text-center text-gray-400 mb-3">
          ± {formatAdjustLabel(adjustStep)} per tap
        </p>
      )}

      {/* Controls */}
      <div className="flex gap-2 justify-center">
        {status === 'idle' && (
          <button
            onClick={start}
            className="px-6 py-2 rounded-lg text-white font-medium active:scale-95"
            style={{ backgroundColor: '#f15f1c' }}
          >
            Remind me
          </button>
        )}
        {status === 'running' && (
          <button
            onClick={pause}
            className="px-6 py-2 rounded-lg text-white font-medium active:scale-95 bg-gray-600"
          >
            Pause
          </button>
        )}
        {status === 'paused' && (
          <>
            <button
              onClick={resume}
              className="px-6 py-2 rounded-lg text-white font-medium active:scale-95"
              style={{ backgroundColor: '#f15f1c' }}
            >
              Resume
            </button>
            <button
              onClick={reset}
              className="px-6 py-2 rounded-lg border border-gray-300 text-gray-600 font-medium active:scale-95"
            >
              Reset
            </button>
          </>
        )}
        {status === 'completed' && (
          <div className="flex gap-2">
            <button
              onClick={reset}
              className="px-5 py-2 rounded-lg border border-gray-300 text-gray-600 font-medium active:scale-95"
            >
              Reset
            </button>
            <button
              onClick={() => {
                // Add 2 more minutes for "needs more time"
                pausedRemainingRef.current = 120;
                setRemaining(120);
                startTimeRef.current = Date.now();
                setStatus('running');
                intervalRef.current = setInterval(tick, 250);
              }}
              className="px-5 py-2 rounded-lg text-white font-medium active:scale-95"
              style={{ backgroundColor: '#f15f1c' }}
            >
              +2 min
            </button>
          </div>
        )}
      </div>
    </div>
  );
};

export { CookingModeTimer };
