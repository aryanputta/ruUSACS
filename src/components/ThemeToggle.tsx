import { useTheme } from './ThemeContext';
import { Sun, Moon } from 'lucide-react';
import { motion } from 'framer-motion';

export function ThemeToggle() {
  const { theme, toggleTheme } = useTheme();

  return (
    <button
      onClick={toggleTheme}
      className={`relative p-2 rounded-xl border overflow-hidden transition-all ${theme === 'stranger'
          ? 'bg-black border-red-600/30 hover:border-red-600/60'
          : 'bg-gray-800 border-white/10 hover:border-white/20'
        }`}
      title={theme === 'stranger' ? 'Switch to Standard' : 'Switch to Stranger'}
    >
      <motion.div
        className="relative z-10"
        initial={false}
        animate={{
          rotate: theme === 'stranger' ? 0 : 180,
          scale: theme === 'stranger' ? 1.1 : 1
        }}
      >
        {theme === 'stranger' ? (
          <Moon className="w-5 h-5 text-red-600" />
        ) : (
          <Sun className="w-5 h-5 text-yellow-400" />
        )}
      </motion.div>

      {/* Background glow effect for stranger theme */}
      {theme === 'stranger' && (
        <div className="absolute inset-0 bg-red-900/10 pointer-events-none" />
      )}
    </button>
  );
}
