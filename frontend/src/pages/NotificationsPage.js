import React, { useState, useEffect } from 'react';
import { useAuth } from '../context/AuthContext';
import { Button } from '../components/ui/button';
import { Alert, AlertDescription, AlertTitle } from '../components/ui/alert';
import { motion } from 'framer-motion';
import { Bell, BellOff, Check } from 'lucide-react';
import axios from 'axios';
import { subscribeUserToPush } from '../lib/pushClient';
import { toast } from 'sonner';

const BACKEND_URL = process.env.REACT_APP_BACKEND_URL;
const API = `${BACKEND_URL}/api`;

export default function NotificationsPage() {
  const { user } = useAuth();
  const [notifications, setNotifications] = useState([]);
  const [unreadCount, setUnreadCount] = useState(0);
  const [permission, setPermission] = useState('default');
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    if ('Notification' in window) {
      setPermission(Notification.permission);
    } else {
      setPermission('unsupported');
    }
    loadNotifications();
    loadUnreadCount();
  }, [user]);

  const loadNotifications = async () => {
    if (!user) return;
    try {
      const { data } = await axios.get(`${API}/notifications`, {
        params: { userId: user.id },
      });
      setNotifications(data);
    } catch (error) {
      console.error('Failed to load notifications:', error);
    } finally {
      setLoading(false);
    }
  };

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

  const requestPermission = async () => {
    if (!('Notification' in window)) return;
    const result = await Notification.requestPermission();
    setPermission(result);

    if (result === 'granted') {
      await setupPushSubscription();
    }
  };

  const setupPushSubscription = async () => {
    try {
      const { data: config } = await axios.get(`${API}/push/vapid-public-key`);
      const subscription = await subscribeUserToPush(config.publicKey);

      if (subscription) {
        await axios.post(
          `${API}/push/subscribe`,
          subscription.toJSON(),
          { params: { userId: user.id } }
        );
        toast.success('Notifications enabled!');
      }
    } catch (error) {
      console.error('Failed to setup push subscription:', error);
      toast.error('Failed to setup notifications');
    }
  };

  const markAsRead = async (notificationId) => {
    try {
      await axios.patch(`${API}/notifications/${notificationId}/read`, null, {
        params: { userId: user.id },
      });
      loadNotifications();
      loadUnreadCount();
    } catch (error) {
      console.error('Failed to mark as read:', error);
    }
  };

  return (
    <div className="h-full overflow-y-auto p-6 pb-24">
      <div className="max-w-2xl mx-auto space-y-6">
        {/* Permission Alert */}
        {permission === 'unsupported' && (
          <Alert className="border-2 border-[#121212] neo-brutal-shadow" data-testid="notification-unsupported-alert">
            <BellOff className="h-5 w-5" />
            <AlertTitle>Notifications not supported</AlertTitle>
            <AlertDescription>
              Your browser does not support system notifications. You will still see in-app alerts.
            </AlertDescription>
          </Alert>
        )}

        {permission === 'denied' && (
          <Alert className="border-2 border-[#121212] neo-brutal-shadow" data-testid="notification-blocked-alert">
            <BellOff className="h-5 w-5" />
            <AlertTitle>Notifications blocked</AlertTitle>
            <AlertDescription>
              You have blocked notifications for this site. Please enable notifications in your browser settings.
            </AlertDescription>
          </Alert>
        )}

        {permission === 'default' && (
          <Alert className="border-2 border-[#121212] neo-brutal-shadow bg-[#BEE3F8]" data-testid="enable-notifications-alert">
            <Bell className="h-5 w-5" />
            <AlertTitle>Enable notifications</AlertTitle>
            <AlertDescription className="mb-3">
              Turn on notifications so we can remind you about scheduled events and let you know when your partner shares new photos.
            </AlertDescription>
            <Button
              data-testid="enable-notifications-button"
              onClick={requestPermission}
              className="bg-[#FFE270] hover:bg-[#ffd960] text-[#121212] border-2 border-[#121212] rounded-xl font-bold neo-brutal-shadow-sm active:translate-y-[2px] active:translate-x-[2px] active:shadow-none transition-all duration-150"
            >
              Enable notifications
            </Button>
          </Alert>
        )}

        {/* Notifications List */}
        <div>
          <div className="flex items-center justify-between mb-4">
            <h2 className="text-2xl font-bold" data-testid="notifications-title">Notifications</h2>
            {unreadCount > 0 && (
              <span className="bg-[#FF7A9F] text-white border-2 border-[#121212] rounded-full px-4 py-1 font-bold neo-brutal-shadow-sm" data-testid="unread-count">
                {unreadCount} new
              </span>
            )}
          </div>

          {loading ? (
            <p className="text-[#52525B] text-center py-8">Loading notifications...</p>
          ) : notifications.length === 0 ? (
            <div className="bg-white border-2 border-[#121212] rounded-2xl p-8 text-center neo-brutal-shadow" data-testid="no-notifications">
              <p className="text-[#52525B]">No notifications yet</p>
            </div>
          ) : (
            <div className="space-y-3">
              {notifications.map((notif, index) => (
                <motion.div
                  key={notif.id || index}
                  initial={{ opacity: 0, x: -20 }}
                  animate={{ opacity: 1, x: 0 }}
                  transition={{ delay: index * 0.05 }}
                  className={`bg-white border-2 border-[#121212] rounded-xl p-4 neo-brutal-shadow-sm ${
                    notif.isRead ? 'opacity-60' : ''
                  }`}
                  data-testid={`notification-${notif.id}`}
                >
                  <div className="flex items-start justify-between gap-3">
                    <div className="flex-1">
                      <h3 className="font-bold mb-1" data-testid={`notification-title-${notif.id}`}>{notif.title}</h3>
                      <p className="text-sm text-[#52525B] mb-2" data-testid={`notification-message-${notif.id}`}>
                        {notif.message}
                      </p>
                      <p className="text-xs text-[#52525B]" data-testid={`notification-time-${notif.id}`}>
                        {new Date(notif.createdAt).toLocaleString()}
                      </p>
                    </div>

                    {!notif.isRead && (
                      <button
                        data-testid={`mark-read-button-${notif.id}`}
                        onClick={() => markAsRead(notif.id)}
                        className="bg-[#FFE270] hover:bg-[#ffd960] border-2 border-[#121212] rounded-full p-2 neo-brutal-shadow-sm active:translate-y-[1px] active:translate-x-[1px] active:shadow-none transition-all duration-150"
                      >
                        <Check className="w-4 h-4" />
                      </button>
                    )}
                  </div>
                </motion.div>
              ))}
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
