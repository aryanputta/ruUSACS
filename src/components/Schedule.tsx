import { PhoneFrame } from './PhoneFrame';
import { ThemeToggle } from './ThemeToggle';
import { useTheme } from './ThemeContext';
import { MapPin, TrendingUp, TrendingDown, Clock, ParkingCircle } from 'lucide-react';
import { motion } from 'framer-motion';

export function Schedule() {
  const { theme } = useTheme();

  const classes = [
    {
      id: 1,
      name: 'Data Structures',
      code: 'CS-112',
      time: '10:00 - 11:20 AM',
      building: 'HILL-114',
      campus: 'BUSCH',
      closestLot: 'LOT A',
      forecast: { occupancy: 78, trend: 'up', risk: 'HIGH' },
    },
    {
      id: 2,
      name: 'Discrete Mathematics',
      code: 'CS-205',
      time: '1:40 - 3:00 PM',
      building: 'SEC-202',
      campus: 'BUSCH',
      closestLot: 'LOT C',
      forecast: { occupancy: 45, trend: 'stable', risk: 'MED' },
    },
    {
      id: 3,
      name: 'Computer Architecture',
      code: 'CS-211',
      time: '3:20 - 4:40 PM',
      building: 'ARC-103',
      campus: 'BUSCH',
      closestLot: 'LOT B',
      forecast: { occupancy: 32, trend: 'down', risk: 'LOW' },
    },
    {
      id: 4,
      name: 'Systems Programming',
      code: 'CS-214',
      time: '5:00 - 6:20 PM',
      building: 'HILL-260',
      campus: 'BUSCH',
      closestLot: 'LOT A',
      forecast: { occupancy: 28, trend: 'down', risk: 'LOW' },
    },
  ];

  const getRiskColor = (risk: string) => {
    switch (risk) {
      case 'HIGH':
        return theme === 'stranger' ? '#ff0000' : '#ef4444';
      case 'MED':
        return theme === 'stranger' ? '#ffff00' : '#f59e0b';
      case 'LOW':
        return theme === 'stranger' ? '#00ff00' : '#10b981';
      default:
        return '#666666';
    }
  };

  return (
    <PhoneFrame>
      <div className={`min-h-full ${theme === 'stranger' ? 'scanlines' : ''}`}>
        {/* Header */}
        <div className={`px-6 pt-3 pb-4 ${theme === 'stranger' ? 'border-b-2 border-red-600/30' : 'border-b border-gray-700'
          }`}>
          <div className="flex items-center justify-between mb-1">
            <h1 className={`text-3xl tracking-wider ${theme === 'stranger'
              ? "font-['Bebas_Neue'] text-red-600 glow-text"
              : 'font-bold text-red-500'
              }`}>
              {theme === 'stranger' ? 'SCHEDULE' : 'Schedule'}
            </h1>
            <ThemeToggle />
          </div>
          <div className={`text-xs font-mono ${theme === 'stranger' ? 'text-gray-400' : 'text-gray-500'}`}>
            {theme === 'stranger' ? 'MONDAY / FEB 07 / 2026' : 'Monday, Feb 7, 2026'}
          </div>
        </div>

        {/* Summary */}
        <motion.div
          initial={{ opacity: 0 }}
          animate={{ opacity: 1 }}
          className="mx-6 my-4"
        >
          <div className={theme === 'stranger'
            ? 'bg-black border-2 border-red-600 p-4 relative'
            : 'bg-gray-900 border border-red-500 rounded-lg p-4'
          }>
            {theme === 'stranger' && (
              <>
                <div className="absolute -top-1 -left-1 w-2 h-2 bg-red-600" />
                <div className="absolute -top-1 -right-1 w-2 h-2 bg-red-600" />
              </>
            )}
            <div className="flex items-center justify-center">
              <div>
                <div className="text-xs text-gray-400 mb-1 text-center">
                  {theme === 'stranger' ? 'CLASSES TODAY' : 'Classes Today'}
                </div>
                <div className={`text-3xl font-bold font-mono text-center ${theme === 'stranger' ? 'text-red-600' : 'text-red-500'
                  }`}>{classes.length}</div>
              </div>
            </div>
          </div>
        </motion.div>

        {/* Class Cards */}
        <div className="px-6 space-y-3 mb-4">
          {classes.map((classItem, index) => {
            const riskColor = getRiskColor(classItem.forecast.risk);
            const TrendIcon = classItem.forecast.trend === 'up' ? TrendingUp : TrendingDown;

            return (
              <motion.div
                key={classItem.id}
                initial={{ opacity: 0, x: -20 }}
                animate={{ opacity: 1, x: 0 }}
                transition={{ delay: index * 0.1 }}
                className={theme === 'stranger'
                  ? 'bg-black border border-red-600/40 hover:border-red-600/80 transition-colors relative'
                  : 'bg-gray-900 border border-gray-700 hover:border-red-500 rounded-lg transition-colors'
                }
              >
                <div className="p-4">
                  {/* Header */}
                  <div className="flex items-start justify-between mb-3">
                    <div>
                      <div className="flex items-center gap-2 mb-1">
                        <h3 className={theme === 'stranger'
                          ? "font-['Bebas_Neue'] text-white tracking-wider text-lg"
                          : 'font-semibold text-white text-lg'
                        }>
                          {classItem.name}
                        </h3>
                      </div>
                      <div className="flex items-center gap-2 text-xs">
                        <span className={`font-mono font-bold ${theme === 'stranger' ? 'text-red-600' : 'text-red-500'
                          }`}>{classItem.code}</span>
                        <span className="text-gray-500">|</span>
                        <Clock className="w-3 h-3 text-gray-400" />
                        <span className="text-gray-400 font-mono">{classItem.time}</span>
                      </div>
                    </div>
                    <div
                      className={`px-2 py-1 text-xs font-mono font-bold border ${theme === 'universal' ? 'rounded' : ''
                        }`}
                      style={{
                        color: riskColor,
                        borderColor: riskColor,
                        boxShadow: theme === 'stranger' ? `0 0 10px ${riskColor}40` : 'none'
                      }}
                    >
                      {classItem.forecast.risk}
                    </div>
                  </div>

                  {/* Location */}
                  <div className="flex items-center gap-2 mb-3 text-sm">
                    <MapPin className="w-3.5 h-3.5 text-gray-500" />
                    <span className="text-gray-300 font-mono">
                      {classItem.building} / {classItem.campus}
                    </span>
                  </div>

                  {/* Parking Lot Info */}
                  <div className={`mb-3 p-2 ${theme === 'stranger'
                    ? 'bg-red-600/10 border-l-2 border-red-600'
                    : 'bg-gray-800 border-l-2 border-red-500 rounded'
                    }`}>
                    <div className="flex items-center gap-2">
                      <ParkingCircle className={`w-4 h-4 ${theme === 'stranger' ? 'text-red-600' : 'text-red-500'
                        }`} />
                      <span className="text-xs text-gray-400">
                        {theme === 'stranger' ? 'NEAREST LOT:' : 'Nearest Lot:'}
                      </span>
                      <span className={`text-sm font-bold font-mono ${theme === 'stranger' ? 'text-red-600' : 'text-red-500'
                        }`}>
                        {classItem.closestLot}
                      </span>
                    </div>
                  </div>

                  {/* Forecast */}
                  <div className={`pt-3 ${theme === 'stranger' ? 'border-t border-red-600/30' : 'border-t border-gray-700'
                    }`}>
                    <div className="flex items-center justify-between mb-2">
                      <div className="flex items-center gap-2">
                        <TrendIcon className="w-4 h-4 text-gray-400" />
                        <span className="text-xs text-gray-400 font-mono">
                          {theme === 'stranger' ? 'PARKING FORECAST' : 'Parking Forecast'}
                        </span>
                      </div>
                      <div className="font-mono text-xl font-bold tabular-nums" style={{ color: riskColor }}>
                        {classItem.forecast.occupancy}%
                      </div>
                    </div>

                    {/* Progress bar */}
                    <div className={`h-1 overflow-hidden ${theme === 'stranger' ? 'bg-red-950/50' : 'bg-gray-800 rounded-full'
                      }`}>
                      <motion.div
                        initial={{ width: 0 }}
                        animate={{ width: `${classItem.forecast.occupancy}%` }}
                        transition={{ delay: 0.2 + index * 0.1, duration: 0.6 }}
                        className={`h-full ${theme === 'universal' ? 'rounded-full' : ''}`}
                        style={{
                          backgroundColor: riskColor,
                          boxShadow: theme === 'stranger' ? `0 0 8px ${riskColor}` : 'none',
                        }}
                      />
                    </div>
                  </div>
                </div>
              </motion.div>
            );
          })}
        </div>

        {/* Tip */}
        <motion.div
          initial={{ opacity: 0 }}
          animate={{ opacity: 1 }}
          transition={{ delay: 0.5 }}
          className={`mx-6 mb-6 p-4 ${theme === 'stranger'
            ? 'bg-black border border-yellow-600/40'
            : 'bg-gray-900 border border-yellow-500 rounded-lg'
            }`}
        >
          <div className={`text-xs mb-2 ${theme === 'stranger'
            ? "text-yellow-500 font-['Bebas_Neue'] tracking-wider"
            : 'text-yellow-400 font-semibold'
            }`}>
            {theme === 'stranger' ? '⚡ SYSTEM TIP' : '💡 Pro Tip'}
          </div>
          <div className="text-white font-mono text-sm">
            Arrive <span className={`font-bold ${theme === 'stranger' ? 'text-red-600' : 'text-red-400'
              }`}>15min early</span> to first class for optimal parking
          </div>
        </motion.div>
      </div>
    </PhoneFrame>
  );
}