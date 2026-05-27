import React, { useEffect, useState } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { Sparkles } from 'lucide-react';
import { Button } from './ui/button';

const MILESTONE_MESSAGES = {
  3: { emoji: '🌱', title: '3 Days!', subtitle: 'You\'re building something special' },
  7: { emoji: '⭐', title: 'One Week!', subtitle: 'Consistency is love' },
  14: { emoji: '💖', title: 'Two Weeks!', subtitle: 'You two are unstoppable' },
  30: { emoji: '🏆', title: '30 Days!', subtitle: 'A whole month of memories' },
  50: { emoji: '🔥', title: '50 Days!', subtitle: 'On fire!' },
  100: { emoji: '💯', title: '100 DAYS!', subtitle: 'Triple digits — legendary' },
  200: { emoji: '👑', title: '200 Days!', subtitle: 'Royalty status' },
  365: { emoji: '🎂', title: 'ONE FULL YEAR!', subtitle: 'A year of daily love' },
  500: { emoji: '🌟', title: '500 Days!', subtitle: 'You\'re a phenomenon' },
  1000: { emoji: '🦄', title: '1000 DAYS!', subtitle: 'Unicorn-level dedication' },
};

const confetti = ['🎉', '✨', '💖', '🌟', '🎊', '💕', '🔥'];

export default function MilestoneCelebration({ milestone, onClose }) {
  const data = MILESTONE_MESSAGES[milestone] || {
    emoji: '🎉',
    title: `${milestone} Days!`,
    subtitle: 'Amazing streak',
  };
  
  const [pieces] = useState(() =>
    Array.from({ length: 30 }, (_, i) => ({
      id: i,
      emoji: confetti[i % confetti.length],
      x: Math.random() * 100,
      delay: Math.random() * 0.5,
      duration: 2 + Math.random() * 2,
      rotate: Math.random() * 720 - 360,
    }))
  );

  return (
    <AnimatePresence>
      <motion.div
        initial={{ opacity: 0 }}
        animate={{ opacity: 1 }}
        exit={{ opacity: 0 }}
        className="fixed inset-0 bg-black/40 z-50 flex items-center justify-center p-6 overflow-hidden"
        data-testid="milestone-overlay"
      >
        {/* Confetti */}
        {pieces.map((p) => (
          <motion.div
            key={p.id}
            initial={{ y: -50, x: `${p.x}vw`, opacity: 1, rotate: 0 }}
            animate={{
              y: '110vh',
              opacity: [1, 1, 0],
              rotate: p.rotate,
            }}
            transition={{
              duration: p.duration,
              delay: p.delay,
              ease: 'easeIn',
            }}
            className="absolute text-4xl pointer-events-none"
          >
            {p.emoji}
          </motion.div>
        ))}

        <motion.div
          initial={{ scale: 0, rotate: -10 }}
          animate={{ scale: 1, rotate: 0 }}
          exit={{ scale: 0 }}
          transition={{ type: 'spring', damping: 12 }}
          className="bg-white border-2 border-[#121212] rounded-3xl p-8 max-w-sm w-full text-center neo-brutal-shadow-lg relative z-10"
          data-testid="milestone-card"
        >
          <motion.div
            animate={{ scale: [1, 1.2, 1] }}
            transition={{ duration: 1.5, repeat: Infinity }}
            className="text-7xl mb-4"
            data-testid="milestone-emoji"
          >
            {data.emoji}
          </motion.div>

          <div className="bg-[#FFE270] border-2 border-[#121212] rounded-full px-4 py-1 inline-flex items-center gap-1 mb-4 neo-brutal-shadow-sm">
            <Sparkles className="w-4 h-4" />
            <span className="text-sm font-bold">Milestone unlocked</span>
          </div>

          <h2 className="text-4xl font-extrabold mb-2" data-testid="milestone-title">{data.title}</h2>
          <p className="text-[#52525B] mb-6" data-testid="milestone-subtitle">{data.subtitle}</p>

          <Button
            data-testid="milestone-close-button"
            onClick={onClose}
            className="w-full bg-[#FF7A9F] hover:bg-[#ff6b8f] text-white border-2 border-[#121212] rounded-xl py-6 text-lg font-bold neo-brutal-shadow active:translate-y-[4px] active:translate-x-[4px] active:shadow-none transition-all duration-150"
          >
            Keep the streak going! 🔥
          </Button>
        </motion.div>
      </motion.div>
    </AnimatePresence>
  );
}
