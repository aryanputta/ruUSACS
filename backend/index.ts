/**
 * Smart Commute Optimization – Express API entry point.
 *
 * All backend functionality is exposed exclusively through REST endpoints.
 * The frontend communicates with Azure Maps and other cloud services only
 * through this API layer; it never accesses Azure keys directly.
 */

import express from "express";
import cors from "cors";
import { config } from "./config";
import { commuteRouter } from "./routes";
import { errorHandler } from "./middleware";

const app = express();

// ---------------------------------------------------------------------------
// Global middleware
// ---------------------------------------------------------------------------

app.use(
  cors({
    origin: config.corsOrigins,
    methods: ["GET", "POST", "OPTIONS"],
    allowedHeaders: ["Content-Type", "Authorization"],
  })
);

app.use(express.json({ limit: "1mb" }));

// ---------------------------------------------------------------------------
// Routes
// ---------------------------------------------------------------------------

app.use("/api/commute", commuteRouter);

// Root health-check
app.get("/", (_req, res) => {
  res.json({
    service: "smart-commute-optimization",
    version: "1.0.0",
    endpoints: [
      "POST /api/commute/optimize",
      "GET  /api/commute/health",
    ],
  });
});

// ---------------------------------------------------------------------------
// Error handler (must be registered last)
// ---------------------------------------------------------------------------

app.use(errorHandler);

// ---------------------------------------------------------------------------
// Start server
// ---------------------------------------------------------------------------

app.listen(config.port, () => {
  console.log(
    `[smart-commute] API server listening on http://localhost:${config.port}`
  );
});

export default app;
