/**
 * Recipe scaling utility functions
 * Provides smart scaling and formatting for recipe quantities
 */

// Unicode fractions for display
const UNICODE_FRACTIONS: { [key: number]: string } = {
  0.125: '⅛',
  0.25: '¼',
  0.333: '⅓',
  0.5: '½',
  0.667: '⅔',
  0.75: '¾',
};

/**
 * Parse a quantity string that might contain fractions
 * Examples: "1", "1.5", "1 1/2", "1/2"
 */
export function parseQuantity(quantityStr: string | number | undefined): number | null {
  if (quantityStr === undefined || quantityStr === null) return null;
  if (typeof quantityStr === 'number') return quantityStr;
  
  const str = quantityStr.toString().trim();
  if (!str) return null;
  
  // Check for mixed numbers (e.g., "1 1/2")
  const mixedMatch = str.match(/^(\d+)\s+(\d+)\/(\d+)$/);
  if (mixedMatch) {
    const whole = parseInt(mixedMatch[1]);
    const numerator = parseInt(mixedMatch[2]);
    const denominator = parseInt(mixedMatch[3]);
    return whole + (numerator / denominator);
  }
  
  // Check for simple fractions (e.g., "1/2")
  const fractionMatch = str.match(/^(\d+)\/(\d+)$/);
  if (fractionMatch) {
    const numerator = parseInt(fractionMatch[1]);
    const denominator = parseInt(fractionMatch[2]);
    return numerator / denominator;
  }
  
  // Try to parse as regular number
  const num = parseFloat(str);
  return isNaN(num) ? null : num;
}

/**
 * Convert a decimal to a readable fraction string
 */
export function decimalToFraction(decimal: number): string {
  const tolerance = 0.01; // Tolerance for fraction matching
  
  // Check if it's a whole number
  if (Math.abs(decimal - Math.round(decimal)) < tolerance) {
    return Math.round(decimal).toString();
  }
  
  // Separate whole and fractional parts
  const whole = Math.floor(decimal);
  const fractional = decimal - whole;
  
  // Find the closest common fraction
  let closestFraction = '';
  let minDiff = 1;
  
  for (const [value, fraction] of Object.entries(UNICODE_FRACTIONS)) {
    const diff = Math.abs(fractional - parseFloat(value));
    if (diff < minDiff && diff < tolerance) {
      minDiff = diff;
      closestFraction = fraction;
    }
  }
  
  if (closestFraction) {
    return whole > 0 ? `${whole}${closestFraction}` : closestFraction;
  }
  
  // If no close fraction found, return decimal with limited precision
  return decimal.toFixed(2).replace(/\.?0+$/, '');
}

/**
 * Round a number to a readable measurement
 */
export function roundToReadable(value: number): number {
  if (value === 0) return 0;
  
  // For very small values, round to nearest eighth
  if (value < 0.125) return 0.125;
  
  // For values less than 1, round to nearest common fraction
  if (value < 1) {
    const fractions = [0.125, 0.25, 0.333, 0.5, 0.667, 0.75, 1];
    let closest = fractions[0];
    let minDiff = Math.abs(value - fractions[0]);
    
    for (const fraction of fractions) {
      const diff = Math.abs(value - fraction);
      if (diff < minDiff) {
        minDiff = diff;
        closest = fraction;
      }
    }
    return closest;
  }
  
  // For values 1-10, round to nearest quarter
  if (value <= 10) {
    return Math.round(value * 4) / 4;
  }
  
  // For values 10-50, round to nearest half
  if (value <= 50) {
    return Math.round(value * 2) / 2;
  }
  
  // For larger values, round to nearest whole number
  return Math.round(value);
}

/**
 * Scale a quantity by a factor and return a readable result
 */
export function scaleQuantity(
  quantity: number | string | undefined,
  scaleFactor: number
): string | null {
  const parsed = parseQuantity(quantity);
  if (parsed === null) return null;
  
  const scaled = parsed * scaleFactor;
  const rounded = roundToReadable(scaled);
  
  return decimalToFraction(rounded);
}

/**
 * Format a quantity for display with optional scaling
 */
export function formatQuantityDisplay(
  quantity: number | string | undefined,
  unit: string | undefined,
  scaleFactor: number = 1
): string {
  if (!quantity) return '';
  
  const scaledQuantity = scaleFactor !== 1 
    ? scaleQuantity(quantity, scaleFactor)
    : quantity.toString();
  
  if (!scaledQuantity) return '';
  
  return unit ? `${scaledQuantity} ${unit}` : scaledQuantity;
}

/**
 * Check if a quantity string contains non-scalable values
 */
export function isScalableQuantity(quantity: string | number | undefined): boolean {
  if (!quantity) return false;
  
  const str = quantity.toString().toLowerCase();
  const nonScalable = ['pinch', 'dash', 'taste', 'few', 'some', 'handful'];
  
  return !nonScalable.some(term => str.includes(term));
}

/**
 * Calculate the scaling factor based on original and desired servings
 */
export function calculateScaleFactor(
  originalServings: number | undefined,
  desiredServings: number
): number {
  if (!originalServings || originalServings <= 0) return 1;
  return desiredServings / originalServings;
}