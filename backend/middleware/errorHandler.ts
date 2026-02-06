import { Request, Response, NextFunction } from "express";

/**
 * Centralised error-handling middleware.
 *
 * Any error thrown (or passed via `next(err)`) inside route handlers is
 * caught here and turned into a consistent JSON error response so the
 * frontend never receives raw stack traces.
 */
export function errorHandler(
  err: unknown,
  _req: Request,
  res: Response,
  _next: NextFunction
): void {
  const message =
    err instanceof Error ? err.message : "An unexpected error occurred";

  const statusCode =
    (err as { statusCode?: number }).statusCode ?? 500;

  console.error(`[ERROR] ${statusCode} – ${message}`);
  if (err instanceof Error && err.stack) {
    console.error(err.stack);
  }

  res.status(statusCode).json({
    success: false,
    error: {
      message,
      ...(process.env.NODE_ENV !== "production" && err instanceof Error
        ? { stack: err.stack }
        : {}),
    },
  });
}
