import { useNavigate, useLocation } from 'react-router';
import { MapPin, Calendar, Users } from 'lucide-react';
import { useTheme } from './ThemeContext';

export function Navigation() {
  const { theme } = useTheme();
  const navigate = useNavigate();
  const location = useLocation();

  const tabs = [
    { path: '/', icon: MapPin, label: 'MAP' },
    { path: '/schedule', icon: Calendar, label: 'SCHEDULE' },
    { path: '/social', icon: Users, label: 'SOCIAL' },
  ];

  return (
    <nav className={`absolute bottom-0 left-0 right-0 z-50 pb-[env(safe-area-inset-bottom)] ${theme === 'stranger'
      ? 'bg-black border-t-2 border-red-600' // Changed: Solid black, no gradient
      : 'bg-white/5 backdrop-blur-xl border-t border-white/5 shadow-[0_-5px_20px_rgba(0,0,0,0.5)]'
      }`}>
      <div className="flex justify-around items-center">
        {tabs.map((tab) => {
          const isActive = location.pathname === tab.path;
          const Icon = tab.icon;
          return (
            <button
              key={tab.path}
              onClick={() => navigate(tab.path)}
              className={`relative flex flex-col items-center gap-1 px-6 py-3 transition-all tracking-wider ${theme === 'stranger' ? "font-['Bebas_Neue']" : 'font-semibold'
                } ${isActive
                  ? theme === 'stranger' ? 'text-red-600' : 'text-red-500'
                  : 'text-gray-500'
                }`}
            >
              <Icon
                className={`w-6 h-6 transition-all ${isActive
                  ? theme === 'stranger'
                    ? 'text-red-600 drop-shadow-[0_0_8px_rgba(255,0,0,0.8)]'
                    : 'text-red-500'
                  : 'text-gray-500'
                  }`}
              />
              <span className={`text-xs ${isActive && theme === 'stranger' ? 'glow-text' : ''}`}>
                {tab.label}
              </span>
              {isActive && (
                <div className={`absolute bottom-0 left-0 right-0 h-0.5 ${theme === 'stranger'
                  ? 'bg-red-600 shadow-[0_0_10px_rgba(255,0,0,0.8)]'
                  : 'bg-red-500'
                  }`} />
              )}
            </button>
          );
        })}
      </div>
    </nav>
  );
}