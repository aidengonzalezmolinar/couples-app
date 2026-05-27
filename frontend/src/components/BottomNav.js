import React from 'react';
import { Camera, Image, Bell, MessageSquare } from 'lucide-react';

export default function BottomNav({ activeTab, setActiveTab, unreadCount, unreadMessages }) {
  const tabs = [
    { id: 'camera', icon: Camera, label: 'Camera' },
    { id: 'gallery', icon: Image, label: 'Gallery' },
    { id: 'chat', icon: MessageSquare, label: 'Chat', badge: unreadMessages },
    { id: 'notifications', icon: Bell, label: 'Notifications', badge: unreadCount },
  ];

  return (
    <div className="fixed bottom-0 left-0 right-0 pb-6 px-6 z-40">
      <div className="max-w-md mx-auto pointer-events-auto">
        <div className="bg-white border-2 border-[#121212] rounded-full px-3 py-2 neo-brutal-shadow">
          <div className="flex items-center justify-around">
            {tabs.map((tab) => (
              <button
                key={tab.id}
                data-testid={`nav-${tab.id}`}
                onClick={() => setActiveTab(tab.id)}
                className="relative"
              >
                <div
                  className={`p-3 rounded-full transition-all duration-200 ${
                    activeTab === tab.id
                      ? 'bg-[#FF7A9F] text-white scale-110'
                      : 'text-[#52525B] hover:bg-[#FFF9F0]'
                  }`}
                >
                  <tab.icon className="w-5 h-5" />
                </div>
                {tab.badge > 0 && (
                  <span
                    className="absolute -top-1 -right-1 bg-[#FFE270] border-2 border-[#121212] text-[#121212] text-xs font-bold rounded-full min-w-[20px] h-5 px-1 flex items-center justify-center"
                    data-testid={tab.id === 'notifications' ? 'unread-badge' : `${tab.id}-badge`}
                  >
                    {tab.badge}
                  </span>
                )}
              </button>
            ))}
          </div>
        </div>
      </div>
    </div>
  );
}
