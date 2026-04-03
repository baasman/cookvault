/**
 * Shared date, time, and formatting utilities.
 * Replaces duplicated formatDate/formatTime functions across 9+ components.
 */

/** Format a date string to just the year (e.g., "2024") */
export function formatYear(dateString: string | null | undefined): string {
  if (!dateString) return '';
  try {
    return new Date(dateString).getFullYear().toString();
  } catch {
    return '';
  }
}

/** Format a date string to a long readable format (e.g., "January 15, 2024") */
export function formatDateLong(dateString: string | null | undefined): string {
  if (!dateString) return '';
  try {
    return new Date(dateString).toLocaleDateString('en-US', {
      year: 'numeric',
      month: 'long',
      day: 'numeric',
    });
  } catch {
    return '';
  }
}

/** Format a date string to short format with time (e.g., "Jan 15, 2024, 02:30 PM") */
export function formatDateShort(dateString: string | null | undefined): string {
  if (!dateString) return '';
  try {
    return new Intl.DateTimeFormat('en-US', {
      year: 'numeric',
      month: 'short',
      day: 'numeric',
      hour: '2-digit',
      minute: '2-digit',
    }).format(new Date(dateString));
  } catch {
    return '';
  }
}

/** Format a relative time string (e.g., "2 hours ago", "just now") */
export function formatRelativeTime(dateString: string | null | undefined): string {
  if (!dateString) return '';
  try {
    const date = new Date(dateString);
    const now = new Date();
    const diffMs = now.getTime() - date.getTime();
    const diffMins = Math.floor(diffMs / 60000);
    const diffHours = Math.floor(diffMins / 60);
    const diffDays = Math.floor(diffHours / 24);

    if (diffMins < 1) return 'just now';
    if (diffMins < 60) return `${diffMins} minute${diffMins !== 1 ? 's' : ''} ago`;
    if (diffHours < 24) return `${diffHours} hour${diffHours !== 1 ? 's' : ''} ago`;
    if (diffDays < 7) return `${diffDays} day${diffDays !== 1 ? 's' : ''} ago`;
    return formatDateLong(dateString);
  } catch {
    return '';
  }
}

/** Format cooking duration in minutes to readable string (e.g., "1 hour 30 minutes") */
export function formatCookingTime(minutes: number | undefined): string {
  if (!minutes) return 'Not specified';
  if (minutes < 60) return `${minutes} minutes`;
  const hours = Math.floor(minutes / 60);
  const mins = minutes % 60;
  return mins > 0
    ? `${hours} hour${hours > 1 ? 's' : ''} ${mins} minutes`
    : `${hours} hour${hours > 1 ? 's' : ''}`;
}
