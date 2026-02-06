/**
 * Smart Commute Optimization – Fastest Total Commute (Drive + Walk)
 *
 * Uses the Azure Maps Route Matrix API to evaluate multi-modal commute
 * options.  Given an origin, a destination, and a set of candidate
 * transition points (e.g. parking lots, transit stops), the service:
 *
 *   1. Requests a driving route-matrix from the origin to every
 *      candidate transition point.
 *   2. Requests a walking route-matrix from every candidate transition
 *      point to the final destination.
 *   3. Combines the two legs and returns the transition point that
 *      yields the shortest *total* travel time, along with full
 *      summary data for both legs.
 *
 * All Azure Maps credentials stay on the server – the frontend only
 * interacts through the REST API exposed in /routes.
 */

import { config } from "../../config";

// ---------------------------------------------------------------------------
// Types
// ---------------------------------------------------------------------------

/** A geographic coordinate (latitude / longitude). */
export interface GeoPoint {
  latitude: number;
  longitude: number;
}

/** Summary for a single route leg returned by Azure Maps. */
export interface RouteLegSummary {
  /** Travel time in seconds. */
  travelTimeInSeconds: number;
  /** Distance in metres. */
  lengthInMeters: number;
  /** ISO-8601 departure time (when available). */
  departureTime?: string;
  /** ISO-8601 arrival time (when available). */
  arrivalTime?: string;
}

/** A candidate transition point with the combined commute analysis. */
export interface TransitionCandidate {
  /** The transition (park / drop-off) point that was evaluated. */
  point: GeoPoint;
  /** Optional human-readable label (e.g. "Lot A"). */
  label?: string;
  /** Driving leg: origin → transition point. */
  driveLeg: RouteLegSummary;
  /** Walking leg: transition point → destination. */
  walkLeg: RouteLegSummary;
  /** Total travel time in seconds (drive + walk). */
  totalTravelTimeInSeconds: number;
  /** Total distance in metres (drive + walk). */
  totalLengthInMeters: number;
}

/** Full response returned by the optimisation service. */
export interface CommuteOptimizationResult {
  /** The origin of the commute. */
  origin: GeoPoint;
  /** The final destination of the commute. */
  destination: GeoPoint;
  /** Best (fastest) transition point and its route summary. */
  best: TransitionCandidate;
  /** All evaluated candidates, sorted by total travel time ascending. */
  candidates: TransitionCandidate[];
}

/** Input payload for the optimisation request. */
export interface CommuteOptimizationRequest {
  /** Starting point of the commute. */
  origin: GeoPoint;
  /** Final destination of the commute. */
  destination: GeoPoint;
  /** Candidate transition points between drive and walk legs. */
  transitionPoints: Array<GeoPoint & { label?: string }>;
  /** Optional: departure time in ISO-8601 for traffic-aware routing. */
  departAt?: string;
}

// ---------------------------------------------------------------------------
// Azure Maps Route Matrix helpers
// ---------------------------------------------------------------------------

/**
 * Shape of a single cell inside the Azure Maps Route Matrix response.
 * See: https://learn.microsoft.com/en-us/rest/api/maps/route/post-route-matrix-sync
 */
interface AzureMatrixCell {
  statusCode: number;
  response?: {
    routeSummary?: {
      lengthInMeters: number;
      travelTimeInSeconds: number;
      departureTime?: string;
      arrivalTime?: string;
    };
  };
}

interface AzureRouteMatrixResponse {
  formatVersion?: string;
  matrix: AzureMatrixCell[][];
  summary: {
    successfulRoutes: number;
    totalRoutes: number;
  };
}

/**
 * Calls the Azure Maps **Post Route Matrix Sync** endpoint.
 *
 * @param origins   Array of origin coordinates.
 * @param destinations Array of destination coordinates.
 * @param travelMode   "car" | "pedestrian"
 * @param departAt     Optional ISO-8601 departure time.
 * @returns The parsed matrix response.
 */
async function fetchRouteMatrix(
  origins: GeoPoint[],
  destinations: GeoPoint[],
  travelMode: "car" | "pedestrian",
  departAt?: string
): Promise<AzureRouteMatrixResponse> {
  const url = new URL(
    "/route/matrix/sync/json",
    config.azureMapsBaseUrl
  );
  url.searchParams.set("api-version", "1.0");
  url.searchParams.set("subscription-key", config.azureMapsSubscriptionKey);
  url.searchParams.set("travelMode", travelMode);
  url.searchParams.set("routeType", "fastest");

  if (departAt) {
    url.searchParams.set("departAt", departAt);
  }

  const body = {
    origins: {
      type: "MultiPoint" as const,
      coordinates: origins.map((p) => [p.longitude, p.latitude]),
    },
    destinations: {
      type: "MultiPoint" as const,
      coordinates: destinations.map((p) => [p.longitude, p.latitude]),
    },
  };

  const res = await fetch(url.toString(), {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(body),
  });

  if (!res.ok) {
    const text = await res.text();
    throw new Error(
      `Azure Maps Route Matrix API returned ${res.status}: ${text}`
    );
  }

  return (await res.json()) as AzureRouteMatrixResponse;
}

// ---------------------------------------------------------------------------
// Core optimisation logic
// ---------------------------------------------------------------------------

/**
 * Computes the fastest combined drive + walk commute.
 *
 * The algorithm fans out two route-matrix requests in parallel:
 *   • Drive matrix: origin  → each transition point
 *   • Walk matrix:  each transition point → destination
 *
 * It then zips the results per transition point, sums the travel times,
 * and selects the candidate with the lowest total.
 */
export async function computeFastestCommute(
  request: CommuteOptimizationRequest
): Promise<CommuteOptimizationResult> {
  const { origin, destination, transitionPoints, departAt } = request;

  if (!transitionPoints || transitionPoints.length === 0) {
    throw new Error(
      "At least one transition point is required for drive+walk optimisation."
    );
  }

  // Fan out both matrix requests in parallel.
  const [driveMatrix, walkMatrix] = await Promise.all([
    fetchRouteMatrix([origin], transitionPoints, "car", departAt),
    fetchRouteMatrix(transitionPoints, [destination], "pedestrian", departAt),
  ]);

  // The drive matrix has 1 origin row and N destination columns.
  const driveRow = driveMatrix.matrix[0];
  // The walk matrix has N origin rows, each with 1 destination column.

  const candidates: TransitionCandidate[] = transitionPoints.map(
    (tp, idx) => {
      // Drive leg – origin → transition point (row 0, col idx)
      const driveCell = driveRow?.[idx];
      const driveSummary = driveCell?.response?.routeSummary;
      if (!driveSummary || driveCell.statusCode !== 200) {
        // Fallback to max-safe values so this candidate sorts to the end.
        return buildUnreachableCandidate(tp, idx);
      }

      // Walk leg – transition point → destination (row idx, col 0)
      const walkCell = walkMatrix.matrix[idx]?.[0];
      const walkSummary = walkCell?.response?.routeSummary;
      if (!walkSummary || walkCell.statusCode !== 200) {
        return buildUnreachableCandidate(tp, idx);
      }

      const driveLeg: RouteLegSummary = {
        travelTimeInSeconds: driveSummary.travelTimeInSeconds,
        lengthInMeters: driveSummary.lengthInMeters,
        departureTime: driveSummary.departureTime,
        arrivalTime: driveSummary.arrivalTime,
      };

      const walkLeg: RouteLegSummary = {
        travelTimeInSeconds: walkSummary.travelTimeInSeconds,
        lengthInMeters: walkSummary.lengthInMeters,
        departureTime: walkSummary.departureTime,
        arrivalTime: walkSummary.arrivalTime,
      };

      return {
        point: { latitude: tp.latitude, longitude: tp.longitude },
        label: tp.label,
        driveLeg,
        walkLeg,
        totalTravelTimeInSeconds:
          driveLeg.travelTimeInSeconds + walkLeg.travelTimeInSeconds,
        totalLengthInMeters:
          driveLeg.lengthInMeters + walkLeg.lengthInMeters,
      };
    }
  );

  // Sort ascending by total travel time.
  candidates.sort(
    (a, b) => a.totalTravelTimeInSeconds - b.totalTravelTimeInSeconds
  );

  return {
    origin,
    destination,
    best: candidates[0],
    candidates,
  };
}

// ---------------------------------------------------------------------------
// Helpers
// ---------------------------------------------------------------------------

function buildUnreachableCandidate(
  tp: GeoPoint & { label?: string },
  _idx: number
): TransitionCandidate {
  const unreachable: RouteLegSummary = {
    travelTimeInSeconds: Number.MAX_SAFE_INTEGER,
    lengthInMeters: Number.MAX_SAFE_INTEGER,
  };
  return {
    point: { latitude: tp.latitude, longitude: tp.longitude },
    label: tp.label,
    driveLeg: unreachable,
    walkLeg: unreachable,
    totalTravelTimeInSeconds: Number.MAX_SAFE_INTEGER,
    totalLengthInMeters: Number.MAX_SAFE_INTEGER,
  };
}
