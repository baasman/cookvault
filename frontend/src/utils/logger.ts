/**
 * Logger utility for consistent logging across the application
 * In development, logs to console. In production, could be extended to send to monitoring service.
 */

export const LogLevel = {
  DEBUG: 0,
  INFO: 1,
  WARN: 2,
  ERROR: 3,
} as const;

export type LogLevel = typeof LogLevel[keyof typeof LogLevel];

class Logger {
  private isDevelopment = import.meta.env.DEV;
  private currentLevel: LogLevel;

  constructor(level: LogLevel = LogLevel.INFO) {
    this.currentLevel = level;
  }

  private shouldLog(level: LogLevel): boolean {
    return level >= this.currentLevel;
  }

  private formatMessage(level: string, message: string, context?: any): void {
    const timestamp = new Date().toISOString();
    const prefix = `[${timestamp}] [${level}]`;
    
    if (context) {
      console.log(`${prefix} ${message}`, context);
    } else {
      console.log(`${prefix} ${message}`);
    }
  }

  debug(message: string, context?: any): void {
    if (this.isDevelopment && this.shouldLog(LogLevel.DEBUG)) {
      this.formatMessage('DEBUG', message, context);
    }
  }

  info(message: string, context?: any): void {
    if (this.isDevelopment && this.shouldLog(LogLevel.INFO)) {
      this.formatMessage('INFO', message, context);
    }
  }

  warn(message: string, context?: any): void {
    if (this.shouldLog(LogLevel.WARN)) {
      this.formatMessage('WARN', message, context);
    }
  }

  error(message: string, error?: Error | any): void {
    if (this.shouldLog(LogLevel.ERROR)) {
      // Always show errors, even in production
      const errorInfo = error instanceof Error 
        ? { message: error.message, stack: error.stack }
        : error;
      
      this.formatMessage('ERROR', message, errorInfo);
      
      // In production, you might want to send errors to a monitoring service
      // Example: this.sendToMonitoring(message, error);
    }
  }

  // Method for API errors specifically
  apiError(endpoint: string, error: any, context?: any): void {
    const message = `API Error - ${endpoint}`;
    this.error(message, { error, context });
  }

  // Method for authentication errors
  authError(message: string, error?: any): void {
    this.error(`Auth: ${message}`, error);
  }

  // Method for upload errors
  uploadError(message: string, error?: any): void {
    this.error(`Upload: ${message}`, error);
  }
}

// Create default logger instance
export const logger = new Logger(
  import.meta.env.DEV ? LogLevel.DEBUG : LogLevel.WARN
);

// Export specific loggers for different contexts
export const apiLogger = {
  info: (message: string, context?: any) => logger.info(`API: ${message}`, context),
  error: (endpoint: string, error: any) => logger.apiError(endpoint, error),
};

export const authLogger = {
  info: (message: string, context?: any) => logger.info(`Auth: ${message}`, context),
  error: (message: string, error?: any) => logger.authError(message, error),
};

export const uploadLogger = {
  info: (message: string, context?: any) => logger.info(`Upload: ${message}`, context),
  error: (message: string, error?: any) => logger.uploadError(message, error),
};