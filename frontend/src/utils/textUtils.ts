/**
 * Text utility functions for handling HTML entities, truncation, and formatting
 */

/**
 * Decode HTML entities and clean up HTML tags from text
 * @param text - The text containing HTML entities or tags
 * @returns Cleaned text with HTML entities decoded
 */
export function decodeHtmlEntities(text: string): string {
  if (!text) return '';

  // Create a temporary DOM element to decode HTML entities
  const textArea = document.createElement('textarea');
  textArea.innerHTML = text;
  let decoded = textArea.value;

  // Remove HTML tags but preserve some formatting
  decoded = decoded
    // Replace line breaks with actual line breaks
    .replace(/<br\s*\/?>/gi, '\n')
    .replace(/<\/p><p>/gi, '\n\n')
    .replace(/<p>/gi, '')
    .replace(/<\/p>/gi, '\n')
    // Remove other HTML tags
    .replace(/<[^>]*>/g, '')
    // Clean up multiple spaces and line breaks
    .replace(/\s+/g, ' ')
    .replace(/\n\s+/g, '\n')
    .replace(/\n{3,}/g, '\n\n')
    .trim();

  return decoded;
}

/**
 * Truncate text to a specified length while preserving word boundaries
 * @param text - The text to truncate
 * @param maxLength - Maximum character length (default: 150)
 * @param suffix - Suffix to add when truncated (default: '...')
 * @returns Truncated text
 */
export function truncateText(text: string, maxLength: number = 500, suffix: string = '...'): string {
  if (!text) return '';

  // First decode HTML entities
  const cleanText = decodeHtmlEntities(text);

  if (cleanText.length <= maxLength) {
    return cleanText;
  }

  // Find the last space before the max length to avoid cutting words
  const truncated = cleanText.substring(0, maxLength);
  const lastSpaceIndex = truncated.lastIndexOf(' ');

  if (lastSpaceIndex > maxLength * 0.7) {
    // If we found a space in the last 30% of the text, cut there (less conservative)
    return truncated.substring(0, lastSpaceIndex) + suffix;
  } else {
    // Otherwise, just cut at maxLength
    return truncated + suffix;
  }
}

/**
 * Format text for display with proper line breaks and paragraphs
 * @param text - The text to format
 * @param preserveLineBreaks - Whether to preserve line breaks as <br> tags
 * @returns Formatted text
 */
export function formatTextForDisplay(text: string, preserveLineBreaks: boolean = true): string {
  if (!text) return '';

  const cleanText = decodeHtmlEntities(text);

  if (!preserveLineBreaks) {
    return cleanText;
  }

  // Convert line breaks to HTML breaks for display
  return cleanText
    .split('\n')
    .map(line => line.trim())
    .filter(line => line.length > 0)
    .join('\n');
}

/**
 * Check if text appears to contain HTML content
 * @param text - The text to check
 * @returns True if text contains HTML tags or entities
 */
export function containsHtml(text: string): boolean {
  if (!text) return false;

  // Check for HTML tags or common HTML entities
  const htmlRegex = /<[^>]*>|&[a-zA-Z0-9#]+;/;
  return htmlRegex.test(text);
}

/**
 * Get a safe excerpt from text for previews
 * @param text - The full text
 * @param maxLength - Maximum length for the excerpt
 * @returns Safe excerpt with HTML cleaned
 */
export function getTextExcerpt(text: string, maxLength: number = 500): string {
  if (!text) return '';

  const cleanText = decodeHtmlEntities(text);

  // DEBUG: Log input and parameters
  console.log('getTextExcerpt DEBUG:', {
    originalLength: text.length,
    cleanLength: cleanText.length,
    maxLength,
    originalStart: text.substring(0, 50) + '...',
    cleanStart: cleanText.substring(0, 50) + '...'
  });

  // For excerpts, show more text - be much less conservative
  if (cleanText.length <= maxLength) {
    console.log('getTextExcerpt DEBUG: Returning full text (no truncation needed)');
    return cleanText;
  }

  const truncated = cleanText.substring(0, maxLength);

  // Try to find the last sentence boundary but be much less picky
  const lastPeriod = truncated.lastIndexOf('.');
  const lastExclamation = truncated.lastIndexOf('!');
  const lastQuestion = truncated.lastIndexOf('?');

  const lastSentenceEnd = Math.max(lastPeriod, lastExclamation, lastQuestion);

  if (lastSentenceEnd > maxLength * 0.3) {
    // Much more aggressive - if we find ANY sentence boundary in the last 70% of text, use it
    const result = truncated.substring(0, lastSentenceEnd + 1);
    console.log('getTextExcerpt DEBUG: Cut at sentence boundary, result length:', result.length);
    return result;
  } else {
    // Otherwise, just cut at word boundary near the end
    const lastSpaceIndex = truncated.lastIndexOf(' ');
    if (lastSpaceIndex > maxLength * 0.8) {
      const result = truncated.substring(0, lastSpaceIndex) + '...';
      console.log('getTextExcerpt DEBUG: Cut at word boundary, result length:', result.length);
      return result;
    } else {
      const result = truncated + '...';
      console.log('getTextExcerpt DEBUG: Cut at max length, result length:', result.length);
      return result;
    }
  }
}

/**
 * Convert plain text to HTML with line breaks
 * @param text - Plain text with line breaks
 * @returns HTML string with <br> tags
 */
export function textToHtml(text: string): string {
  if (!text) return '';

  return text
    .split('\n')
    .map(line => line.trim())
    .filter(line => line.length > 0)
    .join('<br>');
}
