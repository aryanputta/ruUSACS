import { useState, useEffect } from 'react';
import { PhoneFrame } from './PhoneFrame';
import { ThemeToggle } from './ThemeToggle';
import { useTheme } from './ThemeContext';
import { Clock, X, Zap, MapPin } from 'lucide-react';
import { motion, AnimatePresence } from 'framer-motion';

interface ParkingSpot {
  id: number;
  row: number;
  col: number;
  status: 'available' | 'occupied';
}

export function Dashboard() {
  const { theme } = useTheme();
  const [currentTime, setCurrentTime] = useState(new Date());
  const [selectedTimeOffset, setSelectedTimeOffset] = useState(0); // 0, 15, 30, 45, 60 minutes
  const [selectedLot, setSelectedLot] = useState<string | null>(null);

  useEffect(() => {
    const timer = setInterval(() => {
      setCurrentTime(new Date());
    }, 60000); // Update every minute
    return () => clearInterval(timer);
  }, []);

  // Parking lot data with better organization
  const parkingLots = [
    { name: 'LOT A', available: 12, total: 45, status: 'low', campus: 'BUSCH', spots: generateParkingLot(45, 12, 5, 9) },
    { name: 'LOT B', available: 3, total: 50, status: 'critical', campus: 'BUSCH', spots: generateParkingLot(50, 3, 5, 10) },
    { name: 'LOT C', available: 28, total: 60, status: 'good', campus: 'BUSCH', spots: generateParkingLot(60, 28, 6, 10) },
    { name: 'LOT D', available: 8, total: 35, status: 'medium', campus: 'COLLEGE AVE', spots: generateParkingLot(35, 8, 5, 7) },
  ];

  function generateParkingLot(total: number, available: number, rows: number, cols: number): ParkingSpot[] {
    const spots: ParkingSpot[] = [];
    let id = 1;
    let availableCount = available;

    for (let row = 0; row < rows; row++) {
      for (let col = 0; col < cols; col++) {
        if (id <= total) {
          spots.push({
            id: id++,
            row,
            col,
            status: 'occupied',
          });
        }
      }
    }

    // Randomly assign available spots
    const shuffled = [...spots].sort(() => Math.random() - 0.5);
    for (let i = 0; i < availableCount && i < shuffled.length; i++) {
      shuffled[i].status = 'available';
    }

    return spots;
  }

  const getStatusColor = (status: string) => {
    switch (status) {
      case 'good':
        return theme === 'stranger' ? '#00ff00' : '#10b981';
      case 'medium':
        return theme === 'stranger' ? '#ffff00' : '#f59e0b';
      case 'low':
        return theme === 'stranger' ? '#ff9900' : '#f97316';
      case 'critical':
        return theme === 'stranger' ? '#ff0000' : '#ef4444';
      default:
        return '#666666';
    }
  };

  const getStatusIcon = (status: string) => {
    switch (status) {
      case 'good':
        return Zap;
      case 'critical':
        return Zap;
      default:
        return Zap;
    }
  };

  const getDisplayTime = () => {
    const futureTime = new Date(currentTime.getTime() + selectedTimeOffset * 60000);
    const hours = futureTime.getHours();
    const minutes = futureTime.getMinutes();
    const isPM = hours >= 12;
    const displayHours = hours % 12 || 12;
    return `${displayHours}:${String(minutes).padStart(2, '0')} ${isPM ? 'PM' : 'AM'}`;
  };

  const getPredictedOccupancy = () => {
    // Base occupancy that changes with time offset
    const baseOccupancy = 73;
    const variation = Math.sin(selectedTimeOffset / 30) * 15;
    return Math.floor(baseOccupancy + variation);
  };

  const getTrend = () => {
    if (selectedTimeOffset === 0) return '→ CURRENT';
    if (selectedTimeOffset < 30) return '↗ RISING';
    return '↘ FALLING';
  };

  const selectedLotData = parkingLots.find(lot => lot.name === selectedLot);

  const timeOffsets = [0, 15, 30, 45, 60];

  // Organize spots into rows for display
  const organizeSpotsIntoRows = (spots: ParkingSpot[]) => {
    const rows: ParkingSpot[][] = [];
    const maxRow = Math.max(...spots.map(s => s.row));

    for (let i = 0; i <= maxRow; i++) {
      const rowSpots = spots.filter(s => s.row === i).sort((a, b) => a.col - b.col);
      if (rowSpots.length > 0) {
        rows.push(rowSpots);
      }
    }

    return rows;
  };

  return (
    <PhoneFrame>
      <div className={`min-h-full ${theme === 'stranger' ? 'scanlines' : ''}`}>
        {/* Header */}
        <div className={`px-6 pt-3 pb-4 ${theme === 'stranger' ? 'border-b-2 border-red-600/30' : 'border-b border-gray-800'
          }`}>
          <div className="flex items-center justify-between mb-2">
            <h1 className={`text-3xl tracking-wider ${theme === 'stranger'
              ? "font-['Bebas_Neue'] text-red-600 glow-text"
              : 'font-bold text-white'
              }`}>
              {theme === 'stranger' ? 'RUPARKED' : 'RUParked'}
            </h1>
            <ThemeToggle />
          </div>
          {theme === 'stranger' ? (
            <div className="text-xs text-gray-400 font-mono">
              <div>SYS_STATUS: ONLINE</div>
              <div className="text-red-600">NODE: BUSCH_ALPHA</div>
            </div>
          ) : (
            <div className="text-sm text-gray-500">Real-time parking availability</div>
          )}
        </div>

        {/* Quick Stats */}
        <motion.div
          initial={{ opacity: 0 }}
          animate={{ opacity: 1 }}
          className="px-6 py-4 grid grid-cols-3 gap-3"
        >
          <div className={theme === 'stranger'
            ? 'bg-black border border-red-600/40 p-3 relative overflow-hidden'
            : 'bg-white/5 border border-white/10 rounded-2xl p-3 backdrop-blur-md shadow-lg'
          }>
            {theme === 'stranger' && (
              <div className="absolute inset-0 bg-gradient-to-br from-red-600/10 to-transparent" />
            )}
            <div className="relative text-center">
              <div className={`text-[10px] uppercase font-bold tracking-wider mb-1 ${theme === 'stranger' ? 'text-gray-400' : 'text-gray-400'}`}>
                {theme === 'stranger' ? 'TOTAL' : 'Total'}
              </div>
              <div className={`text-2xl font-bold font-mono ${theme === 'stranger' ? 'text-red-600' : 'text-white'
                }`}>190</div>
            </div>
          </div>
          <div className={theme === 'stranger'
            ? 'bg-black border border-green-600/40 p-3 relative overflow-hidden'
            : 'bg-white/5 border border-white/10 rounded-2xl p-3 backdrop-blur-md shadow-lg'
          }>
            {theme === 'stranger' && (
              <div className="absolute inset-0 bg-gradient-to-br from-green-600/10 to-transparent" />
            )}
            <div className="relative text-center">
              <div className={`text-[10px] uppercase font-bold tracking-wider mb-1 ${theme === 'stranger' ? 'text-gray-400' : 'text-gray-400'}`}>
                {theme === 'stranger' ? 'OPEN' : 'Open'}
              </div>
              <div className={`text-2xl font-bold font-mono ${theme === 'stranger' ? 'text-green-500' : 'text-emerald-400'
                }`}>51</div>
            </div>
          </div>
          <div className={theme === 'stranger'
            ? 'bg-black border border-yellow-600/40 p-3 relative overflow-hidden'
            : 'bg-white/5 border border-white/10 rounded-2xl p-3 backdrop-blur-md shadow-lg'
          }>
            {theme === 'stranger' && (
              <div className="absolute inset-0 bg-gradient-to-br from-yellow-600/10 to-transparent" />
            )}
            <div className="relative text-center">
              <div className={`text-[10px] uppercase font-bold tracking-wider mb-1 ${theme === 'stranger' ? 'text-gray-400' : 'text-gray-400'}`}>
                {theme === 'stranger' ? 'OCCUPIED' : 'Occupied'}
              </div>
              <div className={`text-2xl font-bold font-mono ${theme === 'stranger' ? 'text-yellow-500' : 'text-amber-400'
                }`}>73%</div>
            </div>
          </div>
        </motion.div>

        {/* AI Recommendation */}
        <motion.div
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          className="mx-6 mb-4"
        >
          <div className={theme === 'stranger'
            ? 'bg-black border-2 border-red-600 p-4 relative overflow-hidden'
            : 'bg-gray-900 border border-red-500 rounded-lg p-4'
          }>
            {theme === 'stranger' && (
              <>
                <div className="absolute top-0 left-0 right-0 h-6 bg-gradient-to-b from-red-600/20 to-transparent" />
                <div className="absolute -top-1 -left-1 w-2 h-2 bg-red-600 animate-pulse" />
                <div className="absolute -top-1 -right-1 w-2 h-2 bg-red-600 animate-pulse" />
              </>
            )}
            <div className="relative">
              <div className={`text-xs mb-2 flex items-center gap-2 ${theme === 'stranger'
                ? "text-red-600 font-['Bebas_Neue'] tracking-wider"
                : 'text-red-500 font-semibold'
                }`}>
                <Zap className="w-4 h-4" />
                {theme === 'stranger' ? 'AI RECOMMENDATION' : 'Smart Suggestion'}
              </div>
              <div className="text-white font-mono text-sm leading-relaxed">
                Best spot at <span className={theme === 'stranger' ? 'text-red-600 font-bold' : 'text-red-400 font-semibold'}>
                  2:45 PM
                </span> in <span className={theme === 'stranger' ? 'text-red-600 font-bold' : 'text-red-400 font-semibold'}>
                  LOT C Row 3
                </span>
                <br />
                <span className="text-gray-400">
                  400ft from SEC-202
                </span>
              </div>
            </div>
          </div>
        </motion.div>

        {/* Parking Lots Status */}
        <div className="px-6 mb-4">
          <h2 className={`text-lg tracking-wider mb-3 flex items-center gap-2 ${theme === 'stranger'
            ? "font-['Bebas_Neue'] text-red-600"
            : 'font-semibold text-red-500'
            }`}>
            {theme === 'stranger' && <div className="w-1 h-4 bg-red-600 animate-pulse" />}
            {theme === 'stranger' ? 'LIVE STATUS FEED' : 'Live Parking Status'}
          </h2>
          <div className="space-y-2">
            {parkingLots.map((lot, index) => {
              const StatusIcon = getStatusIcon(lot.status);
              const percentage = Math.round((lot.available / lot.total) * 100);
              return (
                <motion.button
                  key={lot.name}
                  initial={{ opacity: 0, x: -20 }}
                  animate={{ opacity: 1, x: 0 }}
                  transition={{ delay: index * 0.1 }}
                  onClick={() => setSelectedLot(lot.name)}
                  className={`w-full text-left p-3 transition-colors ${theme === 'stranger'
                    ? 'bg-black border border-red-600/30 hover:border-red-600/60'
                    : 'bg-gray-900 border border-gray-700 hover:border-red-500 rounded-lg'
                    }`}
                >
                  <div className="flex items-center justify-between mb-2">
                    <div className="flex items-center gap-2">
                      <StatusIcon
                        className="w-4 h-4"
                        style={{ color: getStatusColor(lot.status) }}
                      />
                      <span className={theme === 'stranger'
                        ? "font-['Bebas_Neue'] text-white tracking-wider"
                        : 'font-semibold text-white'
                      }>
                        {lot.name}
                      </span>
                      <span className="text-xs text-gray-500 font-mono">{lot.campus}</span>
                    </div>
                    <div className="text-right">
                      <div className="font-mono text-lg font-bold" style={{ color: getStatusColor(lot.status) }}>
                        {lot.available}/{lot.total}
                      </div>
                    </div>
                  </div>
                  <div className={`relative h-1.5 overflow-hidden ${theme === 'stranger' ? 'bg-red-950/50' : 'bg-gray-800 rounded-full'
                    }`}>
                    <motion.div
                      initial={{ width: 0 }}
                      animate={{ width: `${percentage}%` }}
                      transition={{ delay: 0.2 + index * 0.1, duration: 0.6 }}
                      className={`absolute left-0 top-0 h-full ${theme === 'universal' ? 'rounded-full' : ''}`}
                      style={{
                        backgroundColor: getStatusColor(lot.status),
                        boxShadow: theme === 'stranger' ? `0 0 10px ${getStatusColor(lot.status)}` : 'none',
                      }}
                    />
                  </div>
                </motion.button>
              );
            })}
          </div>
        </div>

        {/* Time Machine */}
        <motion.div
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ delay: 0.5 }}
          className="mx-6 mb-6"
        >
          <div className={theme === 'stranger'
            ? 'bg-black border-2 border-red-600/50 p-4 relative'
            : 'bg-gray-900 border border-gray-700 rounded-lg p-4'
          }>
            {theme === 'stranger' && (
              <div className="absolute inset-0 bg-gradient-to-b from-red-600/5 to-transparent pointer-events-none" />
            )}
            <div className="relative">
              <div className="flex items-center justify-between mb-3">
                <div className="flex items-center gap-2">
                  <Clock className={`w-5 h-5 ${theme === 'stranger' ? 'text-red-600' : 'text-red-500'}`} />
                  <h3 className={theme === 'stranger'
                    ? "font-['Bebas_Neue'] tracking-wider text-red-600"
                    : 'font-semibold text-red-500'
                  }>
                    {theme === 'stranger' ? 'TIME MACHINE' : 'Forecast'}
                  </h3>
                </div>
                <div className={`font-mono text-xl font-bold tabular-nums ${theme === 'stranger' ? 'text-red-600' : 'text-red-500'
                  }`}>
                  {getDisplayTime()}
                </div>
              </div>

              {/* Time Scrubber - Sleek Slider Design */}
              <div className={`relative flex items-center mb-4 p-1 rounded-xl overflow-hidden ${theme === 'stranger'
                ? 'bg-red-950/20 border border-red-900/40'
                : 'bg-gray-800/50 border border-white/5'
                }`}>
                <div className="flex w-full relative z-10 overflow-x-auto no-scrollbar snap-x">
                  {timeOffsets.map((offset) => {
                    const futureTime = new Date(currentTime.getTime() + offset * 60000);
                    const hours = futureTime.getHours();
                    const minutes = futureTime.getMinutes();
                    const isPM = hours >= 12;
                    const displayHours = hours % 12 || 12;
                    const timeStr = `${displayHours}:${String(minutes).padStart(2, '0')}`;
                    const ampm = isPM ? 'PM' : 'AM';
                    const isActive = selectedTimeOffset === offset;

                    return (
                      <button
                        key={offset}
                        onClick={() => setSelectedTimeOffset(offset)}
                        className={`relative flex-1 min-w-[70px] py-2 flex flex-col items-center justify-center transition-colors z-10 snap-center outline-none ${isActive
                          ? theme === 'stranger' ? 'text-white' : 'text-white'
                          : theme === 'stranger' ? 'text-red-600/60 hover:text-red-500' : 'text-gray-500 hover:text-gray-300'
                          }`}
                      >
                        {isActive && (
                          <motion.div
                            layoutId="activeTime"
                            className={`absolute inset-0 rounded-lg ${theme === 'stranger'
                              ? 'bg-red-600 shadow-[0_0_15px_rgba(220,38,38,0.5)]'
                              : 'bg-gray-700 shadow-sm'
                              }`}
                            transition={{ type: "spring", bounce: 0.2, duration: 0.6 }}
                          />
                        )}
                        <span className="relative text-xs font-bold leading-none mb-0.5 z-10">
                          {offset === 0 ? 'NOW' : `+${offset}m`}
                        </span>
                        <span className="relative text-[10px] font-mono leading-none opacity-80 z-10">
                          {timeStr}<span className="text-[8px] ml-0.5">{ampm}</span>
                        </span>
                      </button>
                    );
                  })}
                </div>
              </div>

              <div className={`grid grid-cols-2 gap-3 pt-3 ${theme === 'stranger' ? 'border-t border-red-600/30' : 'border-t border-gray-700'
                }`}>
                <div>
                  <div className="text-xs text-gray-400 mb-1">
                    {theme === 'stranger' ? 'PREDICTED' : 'Predicted'}
                  </div>
                  <div className={`font-mono text-2xl font-bold ${theme === 'stranger' ? 'text-yellow-500' : 'text-yellow-400'
                    }`}>
                    {getPredictedOccupancy()}%
                  </div>
                </div>
                <div>
                  <div className="text-xs text-gray-400 mb-1">
                    {theme === 'stranger' ? 'TREND' : 'Trend'}
                  </div>
                  <div className={`font-mono text-sm ${theme === 'stranger' ? 'text-green-500' : 'text-green-400'
                    }`}>
                    {getTrend()}
                  </div>
                </div>
              </div>
            </div>
          </div>
        </motion.div>

        {/* Lot Detail Modal - Improved Parking Lot View */}
        <AnimatePresence>
          {selectedLot && selectedLotData && (
            <motion.div
              initial={{ opacity: 0 }}
              animate={{ opacity: 1 }}
              exit={{ opacity: 0 }}
              className="fixed inset-0 z-50 flex items-center justify-center p-4"
              onClick={() => setSelectedLot(null)}
            >
              {/* Background Overlay */}
              <div className="absolute inset-0 bg-black/80 backdrop-blur-sm" />

              {/* Modal Content */}
              <motion.div
                initial={{ scale: 0.9, y: 20 }}
                animate={{ scale: 1, y: 0 }}
                exit={{ scale: 0.9, y: 20 }}
                transition={{ type: "spring", damping: 20, stiffness: 300 }}
                onClick={(e) => e.stopPropagation()}
                className={`relative w-full max-w-sm max-h-[85vh] overflow-y-auto
                  ${theme === 'stranger'
                    ? 'bg-black border-2 border-red-600'
                    : 'bg-[#1a1a1a] border border-white/20 rounded-2xl'
                  } shadow-2xl`}
              >
                {/* Header */}
                <div className={`sticky top-0 z-10 p-4 ${theme === 'stranger'
                  ? 'bg-black border-b-2 border-red-600/50'
                  : 'bg-[#1a1a1a] border-b border-white/10'
                  }`}>
                  <div className="flex items-center justify-between">
                    <div>
                      <h2 className={`text-2xl font-bold ${theme === 'stranger'
                        ? "font-['Bebas_Neue'] text-red-600 glow-text tracking-wider"
                        : 'text-white'
                        }`}>
                        {selectedLotData.name}
                      </h2>
                      <div className="flex items-center gap-2 mt-1">
                        <MapPin className="w-3 h-3 text-gray-500" />
                        <p className="text-xs text-gray-500 font-mono">
                          {selectedLotData.campus} CAMPUS
                        </p>
                      </div>
                    </div>
                    <button
                      onClick={() => setSelectedLot(null)}
                      className={`p-2 rounded-lg transition-colors ${theme === 'stranger'
                        ? 'text-red-600 hover:bg-red-600/10'
                        : 'text-gray-400 hover:bg-white/5 hover:text-white'
                        }`}
                    >
                      <X className="w-5 h-5" />
                    </button>
                  </div>

                  {/* Stats Bar */}
                  <div className={`mt-3 p-3 rounded-lg ${theme === 'stranger'
                    ? 'bg-red-950/20 border border-red-600/30'
                    : 'bg-white/5 border border-white/10'
                    }`}>
                    <div className="grid grid-cols-3 gap-2 text-center">
                      <div>
                        <div className="text-[10px] text-gray-500 uppercase font-bold mb-0.5">
                          Available
                        </div>
                        <div className={`text-lg font-bold font-mono ${theme === 'stranger' ? 'text-green-500' : 'text-emerald-400'
                          }`}>
                          {selectedLotData.available}
                        </div>
                      </div>
                      <div>
                        <div className="text-[10px] text-gray-500 uppercase font-bold mb-0.5">
                          Occupied
                        </div>
                        <div className={`text-lg font-bold font-mono ${theme === 'stranger' ? 'text-red-500' : 'text-red-400'
                          }`}>
                          {selectedLotData.total - selectedLotData.available}
                        </div>
                      </div>
                      <div>
                        <div className="text-[10px] text-gray-500 uppercase font-bold mb-0.5">
                          Total
                        </div>
                        <div className="text-lg font-bold font-mono text-gray-400">
                          {selectedLotData.total}
                        </div>
                      </div>
                    </div>
                  </div>
                </div>

                {/* Parking Lot Grid */}
                <div className="p-4">
                  <div className={`p-4 rounded-lg ${theme === 'stranger'
                    ? 'bg-red-950/10 border border-red-600/20'
                    : 'bg-black/30 border border-white/5'
                    }`}>
                    {/* Entrance Label */}
                    <div className={`text-center mb-3 pb-2 border-b ${theme === 'stranger' ? 'border-red-600/30' : 'border-white/10'
                      }`}>
                      <div className={`text-xs font-bold uppercase tracking-wider ${theme === 'stranger' ? 'text-red-600' : 'text-gray-400'
                        }`}>
                        ↓ ENTRANCE ↓
                      </div>
                    </div>

                    {/* Parking Spots in Rows */}
                    <div className="space-y-3">
                      {organizeSpotsIntoRows(selectedLotData.spots).map((row, rowIndex) => (
                        <div key={rowIndex}>
                          <div className="flex items-center gap-2 mb-1.5">
                            <div className={`text-[10px] font-bold uppercase ${theme === 'stranger' ? 'text-red-600' : 'text-gray-500'
                              }`}>
                              Row {rowIndex + 1}
                            </div>
                          </div>
                          <div className="grid gap-1.5" style={{
                            gridTemplateColumns: `repeat(${row.length}, minmax(0, 1fr))`
                          }}>
                            {row.map((spot) => (
                              <motion.div
                                key={spot.id}
                                initial={{ scale: 0, opacity: 0 }}
                                animate={{ scale: 1, opacity: 1 }}
                                transition={{ delay: (rowIndex * 0.05) + (spot.col * 0.02) }}
                                className={`aspect-square rounded-md flex flex-col items-center justify-center relative overflow-hidden
                                  ${spot.status === 'available'
                                    ? theme === 'stranger'
                                      ? 'bg-green-600 shadow-[0_0_8px_rgba(0,255,0,0.3)]'
                                      : 'bg-emerald-500'
                                    : theme === 'stranger'
                                      ? 'bg-red-600 shadow-[0_0_8px_rgba(255,0,0,0.3)]'
                                      : 'bg-red-500'
                                  }`}
                              >
                                {/* Car Icon for Occupied */}
                                {spot.status === 'occupied' && (
                                  <div className="absolute inset-0 flex items-center justify-center">
                                    <svg
                                      className="w-3/4 h-3/4 opacity-50"
                                      viewBox="0 0 24 24"
                                      fill="currentColor"
                                    >
                                      <path d="M5,11L6.5,6.5H17.5L19,11M17.5,16A1.5,1.5 0 0,1 16,14.5A1.5,1.5 0 0,1 17.5,13A1.5,1.5 0 0,1 19,14.5A1.5,1.5 0 0,1 17.5,16M6.5,16A1.5,1.5 0 0,1 5,14.5A1.5,1.5 0 0,1 6.5,13A1.5,1.5 0 0,1 8,14.5A1.5,1.5 0 0,1 6.5,16M18.92,6C18.72,5.42 18.16,5 17.5,5H6.5C5.84,5 5.28,5.42 5.08,6L3,12V20A1,1 0 0,0 4,21H5A1,1 0 0,0 6,20V19H18V20A1,1 0 0,0 19,21H20A1,1 0 0,0 21,20V12L18.92,6Z" />
                                    </svg>
                                  </div>
                                )}

                                {/* Spot Number */}
                                <div className={`text-[9px] font-bold z-10 ${spot.status === 'available'
                                  ? theme === 'stranger' ? 'text-black' : 'text-white'
                                  : 'text-white/70'
                                  }`}>
                                  {spot.id}
                                </div>
                              </motion.div>
                            ))}
                          </div>
                        </div>
                      ))}
                    </div>

                    {/* Exit Label */}
                    <div className={`text-center mt-3 pt-2 border-t ${theme === 'stranger' ? 'border-red-600/30' : 'border-white/10'
                      }`}>
                      <div className={`text-xs font-bold uppercase tracking-wider ${theme === 'stranger' ? 'text-red-600' : 'text-gray-400'
                        }`}>
                        ↑ EXIT ↑
                      </div>
                    </div>
                  </div>

                  {/* Legend */}
                  <div className="flex items-center justify-center gap-4 mt-4">
                    <div className="flex items-center gap-1.5">
                      <div className={`w-4 h-4 rounded ${theme === 'stranger' ? 'bg-green-600' : 'bg-emerald-500'
                        }`} />
                      <span className="text-xs text-gray-400">Available</span>
                    </div>
                    <div className="flex items-center gap-1.5">
                      <div className={`w-4 h-4 rounded ${theme === 'stranger' ? 'bg-red-600' : 'bg-red-500'
                        }`} />
                      <span className="text-xs text-gray-400">Occupied</span>
                    </div>
                  </div>
                </div>

                {/* Close Button */}
                <div className="p-4 pt-0">
                  <button
                    onClick={() => setSelectedLot(null)}
                    className={`w-full py-3 font-bold rounded-xl transition-all active:scale-95 ${theme === 'stranger'
                      ? "bg-red-600 text-black font-['Bebas_Neue'] text-lg tracking-widest shadow-[0_0_15px_rgba(220,38,38,0.4)] hover:shadow-[0_0_20px_rgba(220,38,38,0.6)]"
                      : 'bg-white text-black hover:bg-gray-200'
                      }`}
                  >
                    CLOSE VIEW
                  </button>
                </div>
              </motion.div>
            </motion.div>
          )}
        </AnimatePresence>
      </div>
    </PhoneFrame>
  );
}