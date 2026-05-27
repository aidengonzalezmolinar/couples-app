import React, { useState, useEffect } from 'react';
import { AuthProvider, useAuth } from './context/AuthContext';
import { Toaster } from './components/ui/sonner';
import OnboardingPage from './pages/OnboardingPage';
import CameraPage from './pages/CameraPage';
import GalleryPage from './pages/GalleryPage';
import NotificationsPage from './pages/NotificationsPage';
import ChatPage from './pages/ChatPage';
import BottomNav from './components/BottomNav';
import SettingsModal from './components/SettingsModal';
import StreakBadge from './components/StreakBadge';
import { motion, AnimatePresence } from 'framer-motion';
import { Settings as SettingsIcon } from 'lucide-react';
import axios from 'axios';

const BACKEND_URL = process.env.REACT_APP_BACKEND_URL;
const API = `${BACKEND_URL}/api`;

function AppContent() {
  const { user, partner, loading } = useAuth();
  const [activeTab, setActiveTab] = useState('camera');
  const [unreadCount, setUnreadCount] = useState(0);
  const [unreadMessages, setUnreadMessages] = useState(0);
  const [onboardingComplete, setOnboardingComplete] = useState(false);
  const [showSettings, setShowSettings] = useState(false);

  useEffect(() => {
    if (user) {
      loadUnreadCount();
      loadUnreadMessages();
      const interval = setInterval(() => {
        loadUnreadCount();
        loadUnreadMessages();
      }, 15000);
      return () => clearInterval(interval);
    }
  }, [user]);

  const loadUnreadCount = async () => {
    if (!user) return;
    try {
      const { data } = await axios.get(`${API}/notifications/unread-count`, {
        params: { userId: user.id },
      });
      setUnreadCount(data.count);
    } catch (error) {
      console.error('Failed to load unread count:', error);
    }
  };

  const loadUnreadMessages = async () => {
    if (!user) return;
    try {
      const { data } = await axios.get(`${API}/messages/unread-count`, {
        params: { userId: user.id },
      });
      setUnreadMessages(data.count);
    } catch (error) {
      console.error('Failed to load unread messages:', error);
    }
  };

  if (loading) {
    return (
      <div className="min-h-screen bg-[#FFF9F0] flex items-center justify-center">
        <p className="text-xl text-[#52525B]">Loading...</p>
      </div>
    );
  }

  if (!user || (!partner && !onboardingComplete)) {
    return <OnboardingPage onComplete={() => setOnboardingComplete(true)} />;
  }

  const renderPage = () => {
    switch (activeTab) {
      case 'camera':
        return <CameraPage key="camera" />;
      case 'gallery':
        return <GalleryPage key="gallery" />;
      case 'chat':
        return <ChatPage key="chat" />;
      case 'notifications':
        return <NotificationsPage key="notifications" />;
      default:
        return <CameraPage key="camera" />;
    }
  };

  return (
    <div className="min-h-screen bg-[#FFF9F0] overflow-hidden" data-testid="main-app">
      {/* Header */}
      <div className="bg-white border-b-2 border-[#121212] p-4">
        <div className="max-w-2xl mx-auto flex items-center justify-between">
          <div className="flex items-center gap-3">
            <img
              src="https://static.prod-images.emergentagent.com/jobs/8b85d457-dc7c-433b-90f1-7f21f596c0e8/images/31fde269e39fc2ca86dac4b7dbaf37cd6dd0c99a2897a3acd6daa943002b4ad5.png"
              alt="Memory Link"
              className="w-10 h-10"
            />
            <div>
              <h1 className="text-lg font-bold" data-testid="app-title">Memory Link</h1>
              {partner && (
                <p className="text-xs text-[#52525B]" data-testid="partner-name">
                  with {partner.name}
                </p>
              )}
            </div>
          </div>

          <div className="flex items-center gap-2">
            <StreakBadge />
            <button
              data-testid="open-settings-button"
              onClick={() => setShowSettings(true)}
              className="bg-white border-2 border-[#121212] rounded-full p-2 neo-brutal-shadow-sm active:translate-y-[2px] active:translate-x-[2px] active:shadow-none transition-all duration-150"
            >
              <SettingsIcon className="w-4 h-4" />
            </button>
          </div>
        </div>
      </div>

      {/* Content */}
      <div className="h-[calc(100vh-80px)] overflow-hidden">
        <AnimatePresence mode="wait">
          <motion.div
            key={activeTab}
            initial={{ opacity: 0, x: 20 }}
            animate={{ opacity: 1, x: 0 }}
            exit={{ opacity: 0, x: -20 }}
            transition={{ duration: 0.2 }}
            className="h-full"
          >
            {renderPage()}
          </motion.div>
        </AnimatePresence>
      </div>

      {/* Bottom Navigation */}
      <BottomNav
        activeTab={activeTab}
        setActiveTab={setActiveTab}
        unreadCount={unreadCount}
        unreadMessages={unreadMessages}
      />

      {/* Settings Modal */}
      <AnimatePresence>
        {showSettings && <SettingsModal onClose={() => setShowSettings(false)} />}
      </AnimatePresence>
    </div>
  );
}

function App() {
  useEffect(() => {
    // Register service worker
    if ('serviceWorker' in navigator) {
      window.addEventListener('load', () => {
        navigator.serviceWorker
          .register('/service-worker.js')
          .then((registration) => {
            console.log('Service Worker registered with scope:', registration.scope);
          })
          .catch((error) => {
            console.error('Service Worker registration failed:', error);
          });
      });
    }

    // Listen for service worker messages
    if ('serviceWorker' in navigator) {
      navigator.serviceWorker.addEventListener('message', (event) => {
        if (event.data.type === 'NOTIFICATION_CLICKED') {
          console.log('Notification clicked:', event.data.url);
        }
      });
    }
  }, []);

  return (
    <AuthProvider>
      <AppContent />
      <Toaster position="top-center" />
    </AuthProvider>
  );
}

export default App;
