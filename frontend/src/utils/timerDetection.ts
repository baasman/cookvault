export interface DetectedTimer {
  durationSeconds: number;
  label: string;
  isRange: boolean;
}

export interface DonenessCue {
  text: string;
}

const TIME_PATTERN = /(\d+)\s*(?:[-–to]+\s*(\d+)\s*)?(?:hours?|hrs?|minutes?|mins?|seconds?|secs?)/gi;

const DONENESS_PATTERNS = [
  /until\s+(.{3,60}?)(?:\.|,|;|$)/gi,
  /(?:should be|will be|becomes?)\s+(.{3,40}?)(?:\.|,|;|$)/gi,
];

function parseUnit(match: string): 'hours' | 'minutes' | 'seconds' {
  const lower = match.toLowerCase();
  if (lower.startsWith('h')) return 'hours';
  if (lower.startsWith('s')) return 'seconds';
  return 'minutes';
}

function toSeconds(value: number, unit: 'hours' | 'minutes' | 'seconds'): number {
  switch (unit) {
    case 'hours': return value * 3600;
    case 'minutes': return value * 60;
    case 'seconds': return value;
  }
}

export function detectTimers(text: string): DetectedTimer[] {
  const timers: DetectedTimer[] = [];

  TIME_PATTERN.lastIndex = 0;
  let match: RegExpExecArray | null;

  while ((match = TIME_PATTERN.exec(text)) !== null) {
    const fullMatch = match[0];
    const firstNum = parseInt(match[1], 10);
    const secondNum = match[2] ? parseInt(match[2], 10) : null;

    const unitMatch = fullMatch.match(/hours?|hrs?|minutes?|mins?|seconds?|secs?/i);
    if (!unitMatch) continue;

    const unit = parseUnit(unitMatch[0]);
    const isRange = secondNum !== null;
    // Use the higher value for ranges
    const value = isRange ? Math.max(firstNum, secondNum) : firstNum;

    if (value > 0) {
      timers.push({
        durationSeconds: toSeconds(value, unit),
        label: fullMatch.trim(),
        isRange,
      });
    }
  }

  return timers;
}

export function detectDonenessCues(text: string): DonenessCue[] {
  const cues: DonenessCue[] = [];
  const seen = new Set<string>();

  for (const pattern of DONENESS_PATTERNS) {
    pattern.lastIndex = 0;
    let match: RegExpExecArray | null;

    while ((match = pattern.exec(text)) !== null) {
      const cueText = match[1].trim();
      const lower = cueText.toLowerCase();

      // Skip if it's just a time reference or too short
      if (lower.match(/^\d+\s*(min|hour|sec)/)) continue;
      if (cueText.length < 5) continue;

      if (!seen.has(lower)) {
        seen.add(lower);
        cues.push({ text: cueText });
      }
    }
  }

  return cues;
}
