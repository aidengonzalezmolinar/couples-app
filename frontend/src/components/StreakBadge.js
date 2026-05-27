import React, { useState, useEffect } from 'react';
import { useAuth } from '../context/AuthContext';
import axios from 'axios';
import { Flame, AlertTriangle } from 'lucide-react';
import { motion } from 'framer-motion';
import { toast } from 'sonner';
import MilestoneCelebration from './MilestoneCelebration';

const BACKEND_URL = process.env.REACT_APP_BACKEND_URL;
const API = `${BACKEND_URL}/api`;

export default function StreakBadge() {
  const { user } = useAuth();
  const [streak, setStreak] = useState(null);
  const [pinging, setPinging] = useState(false);
  const [showMilestone, setShowMilestone] = useState(null);
  const [shownMilestonesLocally, setShownMilestonesLocally] = useState(new Set());

  useEffect(() => {
    if (!user) return;
    loadStreak();
    const interval = setInterval(loadStreak, 30000);
    return () => clearInterval(interval);
  }, [user]);

  const loadStreak = async () => {
    try {
      const { data } = await axios.get(`${API}/streak`, { params: { userId: user.id } });
      setStreak(data);
      
      // Show milestone celebration if applicable
      if (
        data.newMilestone &&
        !shownMilestonesLocally.has(data.newMilestone)
      ) {
        setShowMilestone(data.newMilestone);
      }
    } catch (e) {
      console.error(e);
    }
  };

  const handleSaveStreak = async (e) => {
    e.stopPropagation();
    if (pinging) return;
    setPinging(true);
    try {
      await axios.post(`${API}/streak/save`, null, { params: { userId: user.id } });
      toast.success('Ping sent to your partner! 🔥');
    } catch (err) {
      toast.error('Could not send ping');
    } finally {
      setPinging(false);
    }
  };

  const handleCelebrationClose = async () => {
    if (showMilestone) {
      try {
        await axios.post(`${API}/streak/celebrate`, null, {
          params: { milestone: showMilestone, userId: user.id },
        });
      } catch (e) {
        console.error(e);
      }
      setShownMilestonesLocally(new Set([...shownMilestonesLocally, showMilestone]));
      setShowMilestone(null);
    }
  };

  if (!streak) return null;

  // User hasn't sent today but streak is at risk
  const showSaveButton = streak.atRisk && streak.streak > 0 && !streak.todayPartnerSent;

  return (
    <>
      <div className="flex items-center gap-2">
        <motion.div
          initial={{ scale: 0 }}
          animate={{
            scale: 1,
            // Pulse if at risk
            ...(streak.atRisk && { boxShadow: ['2px 2px 0px 0px #121212', '2px 2px 0px 0px #FF7A9F', '2px 2px 0px 0px #121212'] }),
          }}
          transition={streak.atRisk ? { duration: 1, repeat: Infinity } : {}}
          className={`flex items-center gap-1 border-2 border-[#121212] rounded-full px-3 py-1 neo-brutal-shadow-sm ${
            streak.atRisk ? 'bg-[#FF7A9F] text-white' : 'bg-[#FFE270]'
          }`}
          data-testid="streak-badge"
          title={
            streak.atRisk
              ? 'Your streak is at risk! Send a photo today!'
              : `${streak.streak} day streak — both partners shared a photo`
          }
        >
          {streak.atRisk ? (
            <AlertTriangle className="w-4 h-4" fill="white" />
          ) : (
            <Flame className="w-4 h-4 text-[#FF7A9F]" fill="#FF7A9F" />
          )}
          <span className="font-bold text-sm" data-testid="streak-count">{streak.streak}</span>
          <span className="text-xs opacity-80">day{streak.streak !== 1 ? 's' : ''}</span>
        </motion.div>

        {showSaveButton && (
          <motion.button
            initial={{ scale: 0 }}
            animate={{ scale: 1 }}
            data-testid="save-streak-button"
            onClick={handleSaveStreak}
            disabled={pinging}
            className="bg-[#FF7A9F] hover:bg-[#ff6b8f] text-white border-2 border-[#121212] rounded-full px-3 py-1 text-xs font-bold neo-brutal-shadow-sm active:translate-y-[2px] active:translate-x-[2px] active:shadow-none transition-all duration-150 whitespace-nowrap"
          >
            {pinging ? '...' : 'Ping! 🔥'}
          </motion.button>
        )}
      </div>

      {showMilestone && (
        <MilestoneCelebration
          milestone={showMilestone}
          onClose={handleCelebrationClose}
        />
      )}
    </>
  );
}
