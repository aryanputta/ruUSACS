/**
 * REST routes for the Smart Commute Optimization API.
 *
 * All functionality is exposed as HTTP endpoints so the frontend
 * never needs direct access to Azure services or keys.
 */

import { Router, Request, Response, NextFunction } from "express";
import {
  computeFastestCommute,
  CommuteOptimizationRequest,
} from "../services/navigation/optimization";
import { validateCommuteBody } from "../middleware/validateBody";

const router = Router();

// ---------------------------------------------------------------------------
// POST /api/commute/optimize
// ---------------------------------------------------------------------------
/**
 * Calculate the fastest combined drive + walk commute.
 *
 * **Request body** (JSON):
 * ```json
 * {
 *   "origin":           { "latitude": 40.5008, "longitude": -74.4474 },
 *   "destination":      { "latitude": 40.5230, "longitude": -74.4580 },
 *   "transitionPoints": [
 *     { "latitude": 40.5120, "longitude": -74.4510, "label": "Lot A" },
 *     { "latitude": 40.5170, "longitude": -74.4530, "label": "Lot B" }
 *   ],
 *   "departAt": "2026-02-06T08:00:00-05:00"      // optional
 * }
 * ```
 *
 * **Success response** (200):
 * ```json
 * {
 *   "success": true,
 *   "data": { ... CommuteOptimizationResult ... }
 * }
 * ```
 *
 * **Error response** (4xx / 5xx):
 * ```json
 * {
 *   "success": false,
 *   "error": { "message": "..." }
 * }
 * ```
 */
router.post(
  "/optimize",
  validateCommuteBody,
  async (req: Request, res: Response, next: NextFunction) => {
    try {
      const payload: CommuteOptimizationRequest = {
        origin: req.body.origin,
        destination: req.body.destination,
        transitionPoints: req.body.transitionPoints,
        departAt: req.body.departAt,
      };

      const result = await computeFastestCommute(payload);

      res.json({ success: true, data: result });
    } catch (err) {
      next(err);
    }
  }
);

// ---------------------------------------------------------------------------
// GET /api/commute/health
// ---------------------------------------------------------------------------
/**
 * Lightweight health-check endpoint.
 */
router.get("/health", (_req: Request, res: Response) => {
  res.json({
    success: true,
    service: "smart-commute-optimization",
    timestamp: new Date().toISOString(),
  });
});

export default router;
