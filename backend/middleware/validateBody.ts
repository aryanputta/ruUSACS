import { Request, Response, NextFunction } from "express";
import { GeoPoint } from "../services/navigation/optimization";

/**
 * Validates that the request body contains a well-formed
 * CommuteOptimizationRequest payload.
 *
 * Returns 400 with a descriptive message on validation failure.
 */
export function validateCommuteBody(
  req: Request,
  res: Response,
  next: NextFunction
): void {
  const { origin, destination, transitionPoints } = req.body ?? {};

  if (!isGeoPoint(origin)) {
    res.status(400).json({
      success: false,
      error: {
        message:
          "origin must be an object with numeric latitude and longitude.",
      },
    });
    return;
  }

  if (!isGeoPoint(destination)) {
    res.status(400).json({
      success: false,
      error: {
        message:
          "destination must be an object with numeric latitude and longitude.",
      },
    });
    return;
  }

  if (!Array.isArray(transitionPoints) || transitionPoints.length === 0) {
    res.status(400).json({
      success: false,
      error: {
        message:
          "transitionPoints must be a non-empty array of { latitude, longitude } objects.",
      },
    });
    return;
  }

  for (let i = 0; i < transitionPoints.length; i++) {
    if (!isGeoPoint(transitionPoints[i])) {
      res.status(400).json({
        success: false,
        error: {
          message: `transitionPoints[${i}] must have numeric latitude and longitude.`,
        },
      });
      return;
    }
  }

  next();
}

// ---------------------------------------------------------------------------
// Helpers
// ---------------------------------------------------------------------------

function isGeoPoint(value: unknown): value is GeoPoint {
  if (typeof value !== "object" || value === null) return false;
  const v = value as Record<string, unknown>;
  return typeof v.latitude === "number" && typeof v.longitude === "number";
}
