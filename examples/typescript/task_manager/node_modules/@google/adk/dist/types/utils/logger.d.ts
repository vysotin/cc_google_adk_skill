/**
 * @license
 * Copyright 2025 Google LLC
 * SPDX-License-Identifier: Apache-2.0
 */
/** Log levels for the logger. */
export declare enum LogLevel {
    DEBUG = 0,
    INFO = 1,
    WARN = 2,
    ERROR = 3
}
/**
 * Logger interface for ADK.
 */
export interface Logger {
    log(level: LogLevel, ...args: unknown[]): void;
    debug(...args: unknown[]): void;
    info(...args: unknown[]): void;
    warn(...args: unknown[]): void;
    error(...args: unknown[]): void;
}
/**
 * Sets the log level for the logger.
 */
export declare function setLogLevel(level: LogLevel): void;
/**
 * Simple logger class for ADK.
 */
declare class SimpleLogger implements Logger {
    log(level: LogLevel, ...args: unknown[]): void;
    debug(...args: unknown[]): void;
    info(...args: unknown[]): void;
    warn(...args: unknown[]): void;
    error(...args: unknown[]): void;
}
/**
 * The logger instance for ADK.
 */
export declare const logger: SimpleLogger;
export {};
