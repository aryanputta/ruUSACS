import { useState, useEffect, useCallback } from "react";

// ─── ARCHITECTURE EXPLANATION ───────────────────────────────────────────────
// The core idea: we DON'T show the camera feed to the user.
// Instead, we show a hand-drawn SVG schematic of the lot.
//
// PIPELINE:
//   Camera Feed → YOLO detects cars → Compares to known spot polygons →
//   Returns JSON: { spotId: "A1", occupied: true } →
//   React colors each SVG <rect> green or red
//
// The SVG schematic is created ONCE (in Figma or code) based on the
// actual lot layout. Each spot gets a unique ID that matches the
// polygon IDs defined in the YOLO config (bounding_boxes.json).
// ────────────────────────────────────────────────────────────────────────────

// ─── API CONFIGURATION ──────────────────────────────────────────────────────
const API_BASE_URL = "http://localhost:8000";
const POLL_INTERVAL_MS = 10000; // Poll every 10 seconds

// ─── SPOT MAPPING ───────────────────────────────────────────────────────────
// Maps backend detector spot IDs to frontend display structure.
// This should match the spot_mapping.json configuration.
const SPOT_MAPPING = {
  sections: [
    {
      name: "A",
      spots: [
        { frontend_id: "A1", detector_id: 25, row: "bottom" },
        { frontend_id: "A2", detector_id: 15, row: "bottom" },
        { frontend_id: "A3", detector_id: 14, row: "bottom" },
        { frontend_id: "A4", detector_id: 0, row: "bottom" },
        { frontend_id: "A5", detector_id: 1, row: "bottom" },
        { frontend_id: "A6", detector_id: 2, row: "bottom" },
        { frontend_id: "A7", detector_id: 4, row: "bottom" },
        { frontend_id: "A8", detector_id: 5, row: "bottom" },
        { frontend_id: "A9", detector_id: 6, row: "bottom" },
        { frontend_id: "A10", detector_id: 7, row: "bottom" },
        { frontend_id: "A11", detector_id: 8, row: "bottom" },
      ],
    },
    {
      name: "B",
      spots: [
        { frontend_id: "B1", detector_id: 26, row: "top" },
        { frontend_id: "B2", detector_id: 16, row: "top" },
        { frontend_id: "B3", detector_id: 27, row: "top" },
        { frontend_id: "B4", detector_id: 24, row: "top" },
        { frontend_id: "B5", detector_id: 23, row: "top" },
        { frontend_id: "B6", detector_id: 3, row: "top" },
        { frontend_id: "B7", detector_id: 40, row: "top" },
        { frontend_id: "B8", detector_id: 41, row: "top" },
        { frontend_id: "B9", detector_id: 42, row: "top" },
      ],
    },
    {
      name: "C",
      spots: [
        { frontend_id: "C1", detector_id: 29, row: "bottom" },
        { frontend_id: "C2", detector_id: 28, row: "bottom" },
        { frontend_id: "C3", detector_id: 43, row: "bottom" },
        { frontend_id: "C4", detector_id: 17, row: "bottom" },
        { frontend_id: "C5", detector_id: 18, row: "bottom" },
        { frontend_id: "C6", detector_id: 19, row: "bottom" },
        { frontend_id: "C7", detector_id: 20, row: "bottom" },
        { frontend_id: "C8", detector_id: 21, row: "bottom" },
        { frontend_id: "C9", detector_id: 22, row: "bottom" },
        { frontend_id: "C10", detector_id: 12, row: "bottom" },
        { frontend_id: "C11", detector_id: 13, row: "bottom" },
        { frontend_id: "C12", detector_id: 11, row: "bottom" },
        { frontend_id: "C13", detector_id: 9, row: "bottom" },
        { frontend_id: "C14", detector_id: 10, row: "bottom" },
      ],
    },
    {
      name: "D",
      spots: [
        { frontend_id: "D1", detector_id: 30, row: "top" },
        { frontend_id: "D2", detector_id: 31, row: "top" },
        { frontend_id: "D3", detector_id: 32, row: "top" },
        { frontend_id: "D4", detector_id: 33, row: "top" },
        { frontend_id: "D5", detector_id: 34, row: "top" },
        { frontend_id: "D6", detector_id: 35, row: "top" },
        { frontend_id: "D7", detector_id: 36, row: "top" },
        { frontend_id: "D8", detector_id: 37, row: "top" },
        { frontend_id: "D9", detector_id: 38, row: "top" },
        { frontend_id: "D10", detector_id: 39, row: "top" },
      ],
    },
    {
      name: "E",
      spots: [
        { frontend_id: "E1", detector_id: 44, row: "bottom" },
        { frontend_id: "E2", detector_id: 45, row: "bottom" },
        { frontend_id: "E3", detector_id: 46, row: "bottom" },
      ],
    },
  ],
};

// ─── FALLBACK LAYOUT GENERATOR ──────────────────────────────────────────────
// Used when API is not available (demo mode)
const generateFallbackLayout = () => {
  return SPOT_MAPPING.sections.map((section) => ({
    name: section.name,
    topRow: section.spots
      .filter((s) => s.row === "top")
      .map((s) => ({
        id: s.frontend_id,
        occupied: Math.random() < 0.65,
        section: section.name,
        row: "top",
        handicap: s.frontend_id === "A1",
        electric: s.frontend_id === "D10",
      })),
    bottomRow: section.spots
      .filter((s) => s.row === "bottom")
      .map((s) => ({
        id: s.frontend_id,
        occupied: Math.random() < 0.65,
        section: section.name,
        row: "bottom",
        handicap: false,
        electric: false,
      })),
  }));
};

// ─── MAP API DATA TO FRONTEND SECTIONS ──────────────────────────────────────
const mapApiDataToSections = (backendSpots) => {
  if (!backendSpots || backendSpots.length === 0) {
    return generateFallbackLayout();
  }

  return SPOT_MAPPING.sections.map((section) => ({
    name: section.name,
    topRow: section.spots
      .filter((s) => s.row === "top")
      .map((s) => {
        const backendSpot = backendSpots.find((bs) => bs.id === s.detector_id);
        return {
          id: s.frontend_id,
          occupied: backendSpot?.occupied ?? false,
          section: section.name,
          row: "top",
          handicap: s.frontend_id === "A1",
          electric: s.frontend_id === "D10",
        };
      }),
    bottomRow: section.spots
      .filter((s) => s.row === "bottom")
      .map((s) => {
        const backendSpot = backendSpots.find((bs) => bs.id === s.detector_id);
        return {
          id: s.frontend_id,
          occupied: backendSpot?.occupied ?? false,
          section: section.name,
          row: "bottom",
          handicap: false,
          electric: false,
        };
      }),
  }));
};

// ─── SPOT COMPONENT ─────────────────────────────────────────────────────────
// Each parking spot is an SVG rect. Color = status. Hover = tooltip.
const ParkingSpot = ({ x, y, width, height, spot, isHovered, onHover, onLeave, onClick, vertical }) => {
  const getColor = () => {
    if (spot.handicap && !spot.occupied) return "#3b82f6"; // blue for handicap
    if (spot.electric && !spot.occupied) return "#8b5cf6"; // purple for EV
    return spot.occupied ? "#ef4444" : "#22c55e"; // red occupied, green open
  };

  const getOpacity = () => {
    if (isHovered) return 1;
    return spot.occupied ? 0.7 : 0.85;
  };

  return (
    <g
      onMouseEnter={() => onHover(spot)}
      onMouseLeave={onLeave}
      onClick={() => onClick(spot)}
      style={{ cursor: "pointer" }}
    >
      {/* Spot background */}
      <rect
        x={x}
        y={y}
        width={width}
        height={height}
        rx={3}
        ry={3}
        fill={getColor()}
        opacity={getOpacity()}
        stroke={isHovered ? "#ffffff" : "rgba(0,0,0,0.3)"}
        strokeWidth={isHovered ? 2.5 : 0.8}
        style={{
          transition: "all 0.2s ease",
          filter: isHovered ? "brightness(1.2)" : "none",
        }}
      />
      {/* Spot label */}
      <text
        x={x + width / 2}
        y={y + height / 2}
        textAnchor="middle"
        dominantBaseline="central"
        fill={isHovered ? "#fff" : "rgba(255,255,255,0.8)"}
        fontSize={width < 30 ? 6 : 8}
        fontFamily="'JetBrains Mono', monospace"
        fontWeight={isHovered ? 700 : 500}
        style={{ pointerEvents: "none", transition: "all 0.2s ease" }}
      >
        {spot.id}
      </text>
      {/* Handicap icon */}
      {spot.handicap && (
        <text
          x={x + width / 2}
          y={y + height - 6}
          textAnchor="middle"
          fontSize={8}
          style={{ pointerEvents: "none" }}
        >
          ♿
        </text>
      )}
      {/* EV icon */}
      {spot.electric && (
        <text
          x={x + width / 2}
          y={y + height - 6}
          textAnchor="middle"
          fontSize={8}
          fill="#fff"
          style={{ pointerEvents: "none" }}
        >
          ⚡
        </text>
      )}
    </g>
  );
};

// ─── DRIVING LANE ───────────────────────────────────────────────────────────
const DrivingLane = ({ x, y, width, height, direction }) => (
  <g>
    <rect
      x={x} y={y} width={width} height={height}
      fill="rgba(30, 30, 40, 0.5)"
      rx={2}
    />
    {/* Lane direction arrows */}
    {Array.from({ length: Math.floor(width / 80) }).map((_, i) => (
      <text
        key={i}
        x={x + 40 + i * 80}
        y={y + height / 2}
        textAnchor="middle"
        dominantBaseline="central"
        fill="rgba(255,255,255,0.15)"
        fontSize={14}
        fontFamily="sans-serif"
      >
        {direction === "right" ? "→" : "←"}
      </text>
    ))}
  </g>
);

// ─── SECTION LABEL ──────────────────────────────────────────────────────────
const SectionLabel = ({ x, y, label }) => (
  <text
    x={x} y={y}
    fill="rgba(255,255,255,0.3)"
    fontSize={16}
    fontFamily="'Outfit', sans-serif"
    fontWeight={700}
    letterSpacing={3}
  >
    ROW {label}
  </text>
);

// ─── MAIN COMPONENT ─────────────────────────────────────────────────────────
export default function RUParked() {
  const [sections, setSections] = useState(generateFallbackLayout());
  const [hoveredSpot, setHoveredSpot] = useState(null);
  const [selectedSpot, setSelectedSpot] = useState(null);
  const [lastUpdated, setLastUpdated] = useState(new Date());
  const [isLive, setIsLive] = useState(true);
  const [viewMode, setViewMode] = useState("map"); // "map" or "list"
  const [apiStatus, setApiStatus] = useState("connecting"); // "connecting" | "live" | "demo"
  const [error, setError] = useState(null);

  // Fetch occupancy data from the FastAPI backend
  const fetchOccupancy = useCallback(async () => {
    try {
      const response = await fetch(`${API_BASE_URL}/api/lots/yellow-lot/status`);
      if (!response.ok) {
        throw new Error(`HTTP ${response.status}`);
      }
      const data = await response.json();

      if (data.spots && data.spots.length > 0) {
        setSections(mapApiDataToSections(data.spots));
        setLastUpdated(data.timestamp ? new Date(data.timestamp) : new Date());
        setApiStatus("live");
        setError(null);
      } else if (data.error) {
        // API is up but detector isn't running
        setApiStatus("demo");
        setError("Detector not running - showing demo data");
      }
    } catch (err) {
      console.error("Failed to fetch occupancy:", err);
      setApiStatus("demo");
      setError("API unavailable - showing demo data");
      
      // In demo mode, simulate small changes
      setSections((prev) =>
        prev.map((section) => ({
          ...section,
          topRow: section.topRow.map((s) => ({
            ...s,
            occupied: Math.random() < 0.02 ? !s.occupied : s.occupied,
          })),
          bottomRow: section.bottomRow.map((s) => ({
            ...s,
            occupied: Math.random() < 0.02 ? !s.occupied : s.occupied,
          })),
        }))
      );
      setLastUpdated(new Date());
    }
  }, []);

  // Poll API for updates
  useEffect(() => {
    fetchOccupancy(); // Initial fetch

    if (!isLive) return;
    const interval = setInterval(fetchOccupancy, POLL_INTERVAL_MS);
    return () => clearInterval(interval);
  }, [isLive, fetchOccupancy]);

  const allSpots = sections.flatMap((s) => [...s.topRow, ...s.bottomRow]);
  const totalSpots = allSpots.length;
  const occupiedSpots = allSpots.filter((s) => s.occupied).length;
  const availableSpots = totalSpots - occupiedSpots;
  const occupancyPct = Math.round((occupiedSpots / totalSpots) * 100);

  // SVG Layout constants
  const spotW = 38;
  const spotH = 52;
  const spotGap = 4;
  const laneH = 36;
  const sectionPadding = 16;
  const leftMargin = 60;
  const topMargin = 40;

  const svgWidth = leftMargin + 12 * (spotW + spotGap) + 60;
  const svgHeight = topMargin + 4 * (2 * spotH + laneH + sectionPadding) + 50;

  return (
    <div
      style={{
        minHeight: "100vh",
        background: "linear-gradient(145deg, #0a0a12 0%, #0d1117 40%, #0a0f1a 100%)",
        color: "#e2e8f0",
        fontFamily: "'Outfit', system-ui, sans-serif",
        overflow: "hidden",
      }}
    >
      {/* Load fonts */}
      <link href="https://fonts.googleapis.com/css2?family=Outfit:wght@300;400;500;600;700;800;900&family=JetBrains+Mono:wght@400;500;700&display=swap" rel="stylesheet" />

      {/* ── HEADER ── */}
      <div style={{
        padding: "20px 28px 16px",
        borderBottom: "1px solid rgba(255,255,255,0.06)",
        display: "flex",
        justifyContent: "space-between",
        alignItems: "center",
        flexWrap: "wrap",
        gap: 12,
      }}>
        <div style={{ display: "flex", alignItems: "center", gap: 14 }}>
          {/* Logo */}
          <div style={{
            width: 40, height: 40, borderRadius: 10,
            background: "linear-gradient(135deg, #ef4444, #dc2626)",
            display: "flex", alignItems: "center", justifyContent: "center",
            fontFamily: "'Outfit'", fontWeight: 900, fontSize: 18, color: "#fff",
            boxShadow: "0 0 20px rgba(239,68,68,0.3)",
          }}>
            RU
          </div>
          <div>
            <h1 style={{
              margin: 0, fontSize: 22, fontWeight: 800,
              letterSpacing: "-0.5px",
              background: "linear-gradient(90deg, #fff, #94a3b8)",
              WebkitBackgroundClip: "text", WebkitTextFillColor: "transparent",
            }}>
              RUParked
            </h1>
            <p style={{ margin: 0, fontSize: 11, color: "#64748b", fontWeight: 500 }}>
              Livingston Campus — Yellow Lot
            </p>
          </div>
        </div>

        {/* Live indicator */}
        <div style={{ display: "flex", alignItems: "center", gap: 16 }}>
          {/* API Status Badge */}
          <div style={{
            display: "flex", alignItems: "center", gap: 6,
            padding: "6px 12px", borderRadius: 20,
            background: apiStatus === "live" ? "rgba(59,130,246,0.1)" : "rgba(245,158,11,0.1)",
            border: `1px solid ${apiStatus === "live" ? "rgba(59,130,246,0.3)" : "rgba(245,158,11,0.3)"}`,
          }}>
            <span style={{
              fontSize: 10, fontWeight: 600,
              color: apiStatus === "live" ? "#3b82f6" : "#f59e0b",
              fontFamily: "'JetBrains Mono'",
              textTransform: "uppercase",
            }}>
              {apiStatus === "live" ? "API LIVE" : apiStatus === "connecting" ? "CONNECTING..." : "DEMO MODE"}
            </span>
          </div>
          
          {/* Live/Paused Toggle */}
          <div style={{
            display: "flex", alignItems: "center", gap: 6,
            padding: "6px 14px", borderRadius: 20,
            background: isLive ? "rgba(34,197,94,0.1)" : "rgba(100,116,139,0.1)",
            border: `1px solid ${isLive ? "rgba(34,197,94,0.3)" : "rgba(100,116,139,0.2)"}`,
            cursor: "pointer",
          }} onClick={() => setIsLive(!isLive)}>
            <div style={{
              width: 7, height: 7, borderRadius: "50%",
              background: isLive ? "#22c55e" : "#64748b",
              boxShadow: isLive ? "0 0 8px #22c55e" : "none",
              animation: isLive ? "pulse 2s infinite" : "none",
            }} />
            <span style={{
              fontSize: 11, fontWeight: 600,
              color: isLive ? "#22c55e" : "#64748b",
              fontFamily: "'JetBrains Mono'",
            }}>
              {isLive ? "LIVE" : "PAUSED"}
            </span>
          </div>
          <span style={{ fontSize: 11, color: "#475569", fontFamily: "'JetBrains Mono'" }}>
            Updated {lastUpdated.toLocaleTimeString()}
          </span>
        </div>
      </div>

      {/* ── STATS BAR ── */}
      <div style={{
        display: "flex", gap: 12, padding: "16px 28px",
        flexWrap: "wrap",
      }}>
        {[
          { label: "Available", value: availableSpots, color: "#22c55e", icon: "○" },
          { label: "Occupied", value: occupiedSpots, color: "#ef4444", icon: "●" },
          { label: "Total", value: totalSpots, color: "#94a3b8", icon: "◉" },
          { label: "Occupancy", value: `${occupancyPct}%`, color: occupancyPct > 80 ? "#ef4444" : occupancyPct > 50 ? "#f59e0b" : "#22c55e", icon: "◧" },
        ].map((stat) => (
          <div key={stat.label} style={{
            flex: "1 1 120px",
            padding: "14px 18px", borderRadius: 12,
            background: "rgba(255,255,255,0.03)",
            border: "1px solid rgba(255,255,255,0.06)",
          }}>
            <div style={{ display: "flex", alignItems: "center", gap: 6, marginBottom: 4 }}>
              <span style={{ color: stat.color, fontSize: 10 }}>{stat.icon}</span>
              <span style={{ fontSize: 11, color: "#64748b", fontWeight: 500, textTransform: "uppercase", letterSpacing: 1 }}>
                {stat.label}
              </span>
            </div>
            <div style={{
              fontSize: 26, fontWeight: 800, color: stat.color,
              fontFamily: "'JetBrains Mono'", letterSpacing: "-1px",
            }}>
              {stat.value}
            </div>
          </div>
        ))}
      </div>

      {/* ── OCCUPANCY BAR ── */}
      <div style={{ padding: "0 28px 12px" }}>
        <div style={{
          height: 6, borderRadius: 3,
          background: "rgba(255,255,255,0.06)",
          overflow: "hidden",
        }}>
          <div style={{
            height: "100%",
            width: `${occupancyPct}%`,
            borderRadius: 3,
            background: occupancyPct > 80
              ? "linear-gradient(90deg, #ef4444, #dc2626)"
              : occupancyPct > 50
                ? "linear-gradient(90deg, #f59e0b, #d97706)"
                : "linear-gradient(90deg, #22c55e, #16a34a)",
            transition: "width 0.5s ease",
          }} />
        </div>
      </div>

      {/* ── SVG LOT MAP ── */}
      <div style={{
        padding: "8px 28px 20px",
        overflowX: "auto",
      }}>
        <div style={{
          background: "rgba(255,255,255,0.02)",
          border: "1px solid rgba(255,255,255,0.06)",
          borderRadius: 16,
          padding: 20,
          position: "relative",
        }}>
          {/* Legend */}
          <div style={{
            display: "flex", gap: 16, marginBottom: 14, flexWrap: "wrap",
            alignItems: "center",
          }}>
            {[
              { color: "#22c55e", label: "Available" },
              { color: "#ef4444", label: "Occupied" },
              { color: "#3b82f6", label: "Handicap" },
              { color: "#8b5cf6", label: "EV Charging" },
            ].map((item) => (
              <div key={item.label} style={{ display: "flex", alignItems: "center", gap: 6 }}>
                <div style={{
                  width: 12, height: 12, borderRadius: 3,
                  background: item.color, opacity: 0.85,
                }} />
                <span style={{ fontSize: 11, color: "#94a3b8", fontWeight: 500 }}>
                  {item.label}
                </span>
              </div>
            ))}
            <span style={{
              marginLeft: "auto", fontSize: 10, color: "#475569",
              fontFamily: "'JetBrains Mono'",
            }}>
              📷 Camera Section: Yellow-NW
            </span>
          </div>

          {/* The actual SVG lot schematic */}
          <svg
            viewBox={`0 0 ${svgWidth} ${svgHeight}`}
            width="100%"
            style={{ maxWidth: svgWidth, display: "block", margin: "0 auto" }}
          >
            {/* Background grid pattern for "asphalt" feel */}
            <defs>
              <pattern id="grid" width="20" height="20" patternUnits="userSpaceOnUse">
                <path d="M 20 0 L 0 0 0 20" fill="none" stroke="rgba(255,255,255,0.02)" strokeWidth="0.5" />
              </pattern>
            </defs>
            <rect width={svgWidth} height={svgHeight} fill="url(#grid)" rx={8} />

            {/* Entry arrow */}
            <g>
              <text x={svgWidth / 2} y={20} textAnchor="middle" fill="rgba(255,255,255,0.2)" fontSize={10} fontFamily="'Outfit', sans-serif" fontWeight={600}>
                ← ENTRANCE — JOYCE KILMER AVE — EXIT →
              </text>
            </g>

            {/* Render each section */}
            {sections.map((section, sIdx) => {
              const sectionY = topMargin + sIdx * (2 * spotH + laneH + sectionPadding);

              return (
                <g key={section.name}>
                  {/* Section label */}
                  <SectionLabel x={8} y={sectionY + spotH + laneH / 2 + 4} label={section.name} />

                  {/* Top row of spots (cars face down toward lane) */}
                  {section.topRow.map((spot, i) => (
                    <ParkingSpot
                      key={spot.id}
                      x={leftMargin + i * (spotW + spotGap)}
                      y={sectionY}
                      width={spotW}
                      height={spotH}
                      spot={spot}
                      isHovered={hoveredSpot?.id === spot.id}
                      onHover={setHoveredSpot}
                      onLeave={() => setHoveredSpot(null)}
                      onClick={setSelectedSpot}
                    />
                  ))}

                  {/* Driving lane between rows */}
                  <DrivingLane
                    x={leftMargin}
                    y={sectionY + spotH + 2}
                    width={12 * (spotW + spotGap) - spotGap}
                    height={laneH - 4}
                    direction={sIdx % 2 === 0 ? "right" : "left"}
                  />

                  {/* Bottom row of spots (cars face up toward lane) */}
                  {section.bottomRow.map((spot, i) => (
                    <ParkingSpot
                      key={spot.id}
                      x={leftMargin + i * (spotW + spotGap)}
                      y={sectionY + spotH + laneH}
                      width={spotW}
                      height={spotH}
                      spot={spot}
                      isHovered={hoveredSpot?.id === spot.id}
                      onHover={setHoveredSpot}
                      onLeave={() => setHoveredSpot(null)}
                      onClick={setSelectedSpot}
                    />
                  ))}
                </g>
              );
            })}

            {/* Solar panel canopy indicators */}
            {sections.map((_, sIdx) => {
              const sectionY = topMargin + sIdx * (2 * spotH + laneH + sectionPadding);
              return (
                <g key={`canopy-${sIdx}`} opacity={0.15}>
                  <line
                    x1={leftMargin - 5} y1={sectionY - 5}
                    x2={leftMargin + 12 * (spotW + spotGap)} y2={sectionY - 5}
                    stroke="#60a5fa" strokeWidth={1} strokeDasharray="4 4"
                  />
                  {sIdx === 0 && (
                    <text x={svgWidth - 45} y={sectionY - 1} fill="#60a5fa" fontSize={7} fontFamily="'JetBrains Mono'" textAnchor="end">
                      ☀ SOLAR
                    </text>
                  )}
                </g>
              );
            })}
          </svg>

          {/* Hover tooltip */}
          {hoveredSpot && (
            <div style={{
              position: "absolute", bottom: 20, left: "50%",
              transform: "translateX(-50%)",
              background: "rgba(15,23,42,0.95)",
              border: "1px solid rgba(255,255,255,0.1)",
              borderRadius: 10, padding: "10px 18px",
              display: "flex", alignItems: "center", gap: 12,
              backdropFilter: "blur(10px)",
              boxShadow: "0 8px 32px rgba(0,0,0,0.4)",
              zIndex: 10,
            }}>
              <div style={{
                width: 10, height: 10, borderRadius: 3,
                background: hoveredSpot.occupied ? "#ef4444" : "#22c55e",
                boxShadow: `0 0 8px ${hoveredSpot.occupied ? "#ef4444" : "#22c55e"}`,
              }} />
              <div>
                <span style={{
                  fontFamily: "'JetBrains Mono'", fontWeight: 700, fontSize: 14,
                  color: "#fff",
                }}>
                  Spot {hoveredSpot.id}
                </span>
                <span style={{ margin: "0 8px", color: "#334155" }}>|</span>
                <span style={{
                  fontSize: 12, fontWeight: 600,
                  color: hoveredSpot.occupied ? "#ef4444" : "#22c55e",
                }}>
                  {hoveredSpot.occupied ? "Occupied" : "Available"}
                </span>
                {hoveredSpot.handicap && (
                  <span style={{ marginLeft: 8, fontSize: 11, color: "#3b82f6" }}>♿ Accessible</span>
                )}
                {hoveredSpot.electric && (
                  <span style={{ marginLeft: 8, fontSize: 11, color: "#8b5cf6" }}>⚡ EV Charging</span>
                )}
              </div>
            </div>
          )}
        </div>
      </div>

      {/* ── PER-ROW SUMMARY ── */}
      <div style={{ padding: "0 28px 20px" }}>
        <div style={{
          display: "grid",
          gridTemplateColumns: "repeat(auto-fit, minmax(200px, 1fr))",
          gap: 10,
        }}>
          {sections.map((section) => {
            const sectionSpots = [...section.topRow, ...section.bottomRow];
            const sectionAvail = sectionSpots.filter((s) => !s.occupied).length;
            const sectionTotal = sectionSpots.length;
            const pct = Math.round((sectionAvail / sectionTotal) * 100);
            return (
              <div key={section.name} style={{
                padding: "12px 16px", borderRadius: 10,
                background: "rgba(255,255,255,0.02)",
                border: "1px solid rgba(255,255,255,0.06)",
                display: "flex", justifyContent: "space-between", alignItems: "center",
              }}>
                <div>
                  <div style={{
                    fontSize: 13, fontWeight: 700,
                    fontFamily: "'JetBrains Mono'", color: "#e2e8f0",
                  }}>
                    Row {section.name}
                  </div>
                  <div style={{ fontSize: 11, color: "#64748b", marginTop: 2 }}>
                    {sectionAvail} of {sectionTotal} available
                  </div>
                </div>
                <div style={{
                  fontSize: 18, fontWeight: 800,
                  fontFamily: "'JetBrains Mono'",
                  color: pct > 40 ? "#22c55e" : pct > 15 ? "#f59e0b" : "#ef4444",
                }}>
                  {pct}%
                </div>
              </div>
            );
          })}
        </div>
      </div>

      {/* ── ARCHITECTURE NOTE (for hackathon judges) ── */}
      <div style={{
        margin: "0 28px 28px",
        padding: "16px 20px", borderRadius: 12,
        background: "rgba(59,130,246,0.05)",
        border: "1px solid rgba(59,130,246,0.15)",
      }}>
        <div style={{
          fontSize: 10, fontWeight: 700, color: "#3b82f6",
          textTransform: "uppercase", letterSpacing: 1.5, marginBottom: 6,
        }}>
          How it works
        </div>
        <p style={{
          fontSize: 12, lineHeight: 1.6, color: "#94a3b8", margin: 0,
        }}>
          Camera under solar canopy captures lot → YOLOv8 detects vehicles on Azure →
          IoU matching maps detections to known spot polygons → API returns per-spot
          occupancy → This SVG schematic updates every 10 seconds. No camera feed is
          shown to users — only this clean, accessible map view.
        </p>
      </div>

      {/* Pulse animation */}
      <style>{`
        @keyframes pulse {
          0%, 100% { opacity: 1; }
          50% { opacity: 0.4; }
        }
      `}</style>
    </div>
  );
}
