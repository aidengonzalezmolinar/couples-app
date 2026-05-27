import React, { useState, useEffect } from 'react';
import { useAuth } from '../context/AuthContext';
import { Button } from './ui/button';
import { Input } from './ui/input';
import { Switch } from './ui/switch';
import { Label } from './ui/label';
import { motion } from 'framer-motion';
import { Settings as SettingsIcon, LogOut, Bell, Clock } from 'lucide-react';
import axios from 'axios';
import { toast } from 'sonner';

const BACKEND_URL = process.env.REACT_APP_BACKEND_URL;
const API = `${BACKEND_URL}/api`;

export default function SettingsModal({ onClose }) {
  const { user, partner, logout } = useAuth();
  const [settings, setSettings] = useState({
    dailyReminderEnabled: false,
    dailyReminderTime: '20:00',
    inactivityReminderEnabled: false,
    inactivityHours: 24,
  });
  const [saving, setSaving] = useState(false);

  useEffect(() => {
    loadSettings();
  }, [user]);

  const loadSettings = async () => {
    if (!user) return;
    try {
      const { data } = await axios.get(`${API}/settings`, { params: { userId: user.id } });
      setSettings(data);
    } catch (e) {
      console.error(e);
    }
  };

  const saveSettings = async () => {
    setSaving(true);
    try {
      await axios.put(`${API}/settings`, settings, { params: { userId: user.id } });
      toast.success('Settings saved!');
    } catch (e) {
      toast.error('Failed to save settings');
    } finally {
      setSaving(false);
    }
  };

  return (
    <motion.div
      initial={{ opacity: 0 }}
      animate={{ opacity: 1 }}
      className="fixed inset-0 bg-black/30 z-50 flex items-end sm:items-center justify-center p-0 sm:p-6"
      onClick={onClose}
      data-testid="settings-overlay"
    >
      <motion.div
        initial={{ y: '100%' }}
        animate={{ y: 0 }}
        exit={{ y: '100%' }}
        onClick={(e) => e.stopPropagation()}
        className="bg-[#FFF9F0] border-2 border-[#121212] rounded-t-3xl sm:rounded-3xl w-full max-w-md max-h-[90vh] overflow-y-auto neo-brutal-shadow-lg"
      >
        <div className="p-6 space-y-6">
          <div className="flex items-center justify-between">
            <h2 className="text-2xl font-bold flex items-center gap-2" data-testid="settings-title">
              <SettingsIcon className="w-6 h-6" />
              Settings
            </h2>
            <button
              data-testid="close-settings-button"
              onClick={onClose}
              className="bg-white border-2 border-[#121212] rounded-full p-2 w-8 h-8 flex items-center justify-center neo-brutal-shadow-sm active:translate-y-[2px] active:translate-x-[2px] active:shadow-none transition-all duration-150"
            >
              ✕
            </button>
          </div>

          {/* User Info */}
          <div className="bg-white border-2 border-[#121212] rounded-2xl p-4 neo-brutal-shadow-sm">
            <p className="text-sm text-[#52525B]">Logged in as</p>
            <p className="text-lg font-bold" data-testid="settings-username">{user?.name}</p>
            {partner && (
              <p className="text-sm text-[#52525B] mt-1">Connected with {partner.name} 💕</p>
            )}
          </div>

          {/* Daily Reminder */}
          <div className="bg-white border-2 border-[#121212] rounded-2xl p-4 neo-brutal-shadow-sm space-y-4">
            <div className="flex items-center justify-between">
              <div className="flex items-center gap-2">
                <Bell className="w-5 h-5" />
                <Label htmlFor="daily-reminder" className="text-base font-bold cursor-pointer">
                  Daily Reminder
                </Label>
              </div>
              <Switch
                id="daily-reminder"
                data-testid="daily-reminder-toggle"
                checked={settings.dailyReminderEnabled}
                onCheckedChange={(v) => setSettings({ ...settings, dailyReminderEnabled: v })}
              />
            </div>
            {settings.dailyReminderEnabled && (
              <div>
                <Label className="text-sm text-[#52525B]">Remind me daily at</Label>
                <Input
                  data-testid="daily-reminder-time-input"
                  type="time"
                  value={settings.dailyReminderTime}
                  onChange={(e) => setSettings({ ...settings, dailyReminderTime: e.target.value })}
                  className="border-2 border-[#121212] rounded-xl bg-white focus-visible:ring-0 mt-2"
                />
              </div>
            )}
          </div>

          {/* Inactivity Reminder */}
          <div className="bg-white border-2 border-[#121212] rounded-2xl p-4 neo-brutal-shadow-sm space-y-4">
            <div className="flex items-center justify-between">
              <div className="flex items-center gap-2">
                <Clock className="w-5 h-5" />
                <Label htmlFor="inactivity-reminder" className="text-base font-bold cursor-pointer">
                  Inactivity Alert
                </Label>
              </div>
              <Switch
                id="inactivity-reminder"
                data-testid="inactivity-reminder-toggle"
                checked={settings.inactivityReminderEnabled}
                onCheckedChange={(v) => setSettings({ ...settings, inactivityReminderEnabled: v })}
              />
            </div>
            {settings.inactivityReminderEnabled && (
              <div>
                <Label className="text-sm text-[#52525B]">
                  Notify me when partner hasn't sent in (hours)
                </Label>
                <Input
                  data-testid="inactivity-hours-input"
                  type="number"
                  min={1}
                  max={168}
                  value={settings.inactivityHours}
                  onChange={(e) =>
                    setSettings({ ...settings, inactivityHours: parseInt(e.target.value) || 24 })
                  }
                  className="border-2 border-[#121212] rounded-xl bg-white focus-visible:ring-0 mt-2"
                />
              </div>
            )}
          </div>

          <Button
            data-testid="save-settings-button"
            onClick={saveSettings}
            disabled={saving}
            className="w-full bg-[#FF7A9F] hover:bg-[#ff6b8f] text-white border-2 border-[#121212] rounded-xl py-6 text-lg font-bold neo-brutal-shadow active:translate-y-[4px] active:translate-x-[4px] active:shadow-none transition-all duration-150"
          >
            {saving ? 'Saving...' : 'Save Settings'}
          </Button>

          <Button
            data-testid="logout-button"
            onClick={() => {
              logout();
              onClose();
            }}
            variant="outline"
            className="w-full border-2 border-[#121212] rounded-xl py-4 text-base font-bold bg-white hover:bg-[#FFF9F0] neo-brutal-shadow-sm active:translate-y-[2px] active:translate-x-[2px] active:shadow-none transition-all duration-150"
          >
            <LogOut className="w-4 h-4 mr-2" />
            Log Out
          </Button>
        </div>
      </motion.div>
    </motion.div>
  );
}
