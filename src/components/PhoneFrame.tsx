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
    <div className="min-h-screen bg-gradient-to-br from-gray-900 via-black to-gray-900 flex items-center justify-center p-2 sm:p-4">
      {/* Phone Device - Scales with viewport height, max at 98vh */}
      <div
        className="relative bg-black rounded-[40px] sm:rounded-[60px] shadow-2xl border-[12px] sm:border-[16px] border-gray-900 overflow-hidden transition-all duration-300"
        style={{
          width: 'min(460px, 98vw)',
          height: 'min(940px, 98vh)',
          boxShadow: '0 0 100px rgba(59, 130, 246, 0.4), 0 0 200px rgba(59, 130, 246, 0.2)'
        }}
      >
        {/* Notch */}
        <div className="absolute top-0 left-1/2 -translate-x-1/2 w-[120px] sm:w-[150px] h-[25px] sm:h-[30px] bg-black rounded-b-3xl z-50" />

        {/* Status Bar */}
        <div className="absolute top-0 left-0 right-0 h-[44px] sm:h-[50px] px-6 sm:px-8 flex items-center justify-between z-40 pt-2">
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
        <div className="absolute bottom-1.5 left-1/2 -translate-x-1/2 w-28 sm:w-32 h-1 bg-white/30 rounded-full z-50" />
      </div>
    </div>
  );
}