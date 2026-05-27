import React, { useState, useEffect, useRef } from 'react';
import { useAuth } from '../context/AuthContext';
import { Button } from '../components/ui/button';
import { Input } from '../components/ui/input';
import { motion, AnimatePresence } from 'framer-motion';
import { Send } from 'lucide-react';
import axios from 'axios';

const BACKEND_URL = process.env.REACT_APP_BACKEND_URL;
const API = `${BACKEND_URL}/api`;

export default function ChatPage() {
  const { user, partner } = useAuth();
  const [messages, setMessages] = useState([]);
  const [text, setText] = useState('');
  const [sending, setSending] = useState(false);
  const messagesEndRef = useRef(null);

  useEffect(() => {
    loadMessages();
    markRead();
    const interval = setInterval(loadMessages, 5000);
    return () => clearInterval(interval);
  }, [user]);

  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [messages]);

  const loadMessages = async () => {
    if (!user) return;
    try {
      const { data } = await axios.get(`${API}/messages`, { params: { userId: user.id } });
      setMessages(data);
    } catch (e) {
      console.error(e);
    }
  };

  const markRead = async () => {
    if (!user) return;
    try {
      await axios.post(`${API}/messages/mark-read`, null, { params: { userId: user.id } });
    } catch (e) {
      console.error(e);
    }
  };

  const sendMessage = async () => {
    if (!text.trim() || sending) return;
    setSending(true);
    try {
      const { data } = await axios.post(
        `${API}/messages`,
        { text: text.trim() },
        { params: { userId: user.id } }
      );
      setMessages([...messages, data]);
      setText('');
    } catch (e) {
      console.error(e);
    } finally {
      setSending(false);
    }
  };

  return (
    <div className="h-full flex flex-col p-6 pb-24">
      <div className="max-w-2xl mx-auto w-full flex-1 flex flex-col">
        <div className="flex-1 overflow-y-auto space-y-3 mb-4" data-testid="messages-container">
          {messages.length === 0 ? (
            <div className="bg-white border-2 border-[#121212] rounded-2xl p-8 text-center neo-brutal-shadow mt-12" data-testid="no-messages">
              <p className="text-[#52525B]">No messages yet</p>
              <p className="text-sm text-[#52525B] mt-2">Start the conversation with {partner?.name || 'your partner'} 💕</p>
            </div>
          ) : (
            <AnimatePresence initial={false}>
              {messages.map((msg) => {
                const isMe = msg.senderId === user.id;
                return (
                  <motion.div
                    key={msg.id}
                    initial={{ opacity: 0, y: 10 }}
                    animate={{ opacity: 1, y: 0 }}
                    className={`flex ${isMe ? 'justify-end' : 'justify-start'}`}
                    data-testid={`message-${msg.id}`}
                  >
                    <div
                      className={`max-w-[75%] border-2 border-[#121212] rounded-2xl px-4 py-3 neo-brutal-shadow-sm ${
                        isMe ? 'bg-[#FF7A9F] text-white' : 'bg-white'
                      }`}
                    >
                      {!isMe && (
                        <p className="text-xs font-bold mb-1 text-[#52525B]">{msg.senderName}</p>
                      )}
                      <p className="break-words">{msg.text}</p>
                      <p className={`text-xs mt-1 ${isMe ? 'text-white/70' : 'text-[#52525B]'}`}>
                        {new Date(msg.createdAt).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })}
                      </p>
                    </div>
                  </motion.div>
                );
              })}
            </AnimatePresence>
          )}
          <div ref={messagesEndRef} />
        </div>

        <div className="flex gap-2 items-end">
          <Input
            data-testid="message-input"
            placeholder="Type a message..."
            value={text}
            onChange={(e) => setText(e.target.value)}
            onKeyPress={(e) => e.key === 'Enter' && sendMessage()}
            className="border-2 border-[#121212] rounded-xl bg-white focus-visible:ring-0 focus-visible:bg-[#FFF9F0] neo-brutal-shadow-sm p-4 flex-1"
          />
          <Button
            data-testid="send-message-button"
            onClick={sendMessage}
            disabled={!text.trim() || sending}
            className="bg-[#FFE270] hover:bg-[#ffd960] text-[#121212] border-2 border-[#121212] rounded-xl p-4 neo-brutal-shadow-sm active:translate-y-[2px] active:translate-x-[2px] active:shadow-none transition-all duration-150"
          >
            <Send className="w-5 h-5" />
          </Button>
        </div>
      </div>
    </div>
  );
}
