import { ReactNode } from 'react';
import { Battery, Wifi, Signal } from 'lucide-react';
import { Navigation } from './Navigation';
import { useTheme } from './ThemeContext';

interface PhoneFrameProps {
  children: ReactNode;
}

export function PhoneFrame({ children }: PhoneFrameProps) {
  const { theme } = useTheme();

  return (
    <div className="min-h-screen bg-gradient-to-br from-gray-900 via-black to-gray-900 flex items-center justify-center p-4">
      {/* Phone Device */}
      <div className="relative w-full max-w-[390px] h-[844px] bg-black rounded-[50px] shadow-2xl border-[14px] border-gray-900 overflow-hidden">
        {/* Notch */}
        <div className="absolute top-0 left-1/2 -translate-x-1/2 w-[150px] h-[30px] bg-black rounded-b-3xl z-50" />

        {/* Status Bar */}
        <div className="absolute top-0 left-0 right-0 h-[50px] px-8 flex items-center justify-between z-40 pt-2">
          <div className="text-white text-sm font-medium">9:41</div>
          <div className="flex items-center gap-1.5">
            <Signal className="w-4 h-4 text-white" />
            <Wifi className="w-4 h-4 text-white" />
            <Battery className="w-5 h-5 text-white" />
          </div>
        </div>

        {/* Screen Content */}
        <div className={`absolute inset-0 overflow-auto ${theme === 'stranger' ? 'bg-black' : 'bg-gray-950'}`}>
          <div className="pt-[50px] pb-[68px]">
            {children}
          </div>
        </div>

        {/* Navigation Tabs - Part of Phone Chrome */}
        <Navigation />

        {/* Home Indicator */}
        <div className="absolute bottom-1.5 left-1/2 -translate-x-1/2 w-32 h-1 bg-white/30 rounded-full z-50" />
      </div>
    </div>
  );
}