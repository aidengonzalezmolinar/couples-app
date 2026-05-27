import React, { useState, useEffect } from 'react';
import { useAuth } from '../context/AuthContext';
import { motion, AnimatePresence } from 'framer-motion';
import { Heart, MessageCircle, Send, Sparkles } from 'lucide-react';
import { Input } from '../components/ui/input';
import axios from 'axios';
import { toast } from 'sonner';

const BACKEND_URL = process.env.REACT_APP_BACKEND_URL;
const API = `${BACKEND_URL}/api`;

export default function GalleryPage() {
  const { user } = useAuth();
  const [photos, setPhotos] = useState([]);
  const [memories, setMemories] = useState([]);
  const [loading, setLoading] = useState(true);
  const [commentingOn, setCommentingOn] = useState(null);
  const [commentText, setCommentText] = useState('');

  useEffect(() => {
    loadPhotos();
    loadMemories();
  }, [user]);

  const loadPhotos = async () => {
    if (!user) return;
    try {
      const { data } = await axios.get(`${API}/photos`, {
        params: { userId: user.id },
      });
      setPhotos(data);
    } catch (error) {
      console.error('Failed to load photos:', error);
    } finally {
      setLoading(false);
    }
  };

  const loadMemories = async () => {
    if (!user) return;
    try {
      const { data } = await axios.get(`${API}/photos/memories`, {
        params: { userId: user.id },
      });
      setMemories(data);
    } catch (error) {
      console.error('Failed to load memories:', error);
    }
  };

  const handleReact = async (photoId) => {
    try {
      await axios.post(`${API}/photos/${photoId}/react`, null, {
        params: { userId: user.id, emoji: '❤️' },
      });
      toast.success('Reacted with heart!');
      loadPhotos();
    } catch (error) {
      console.error('Failed to react:', error);
    }
  };

  const handleComment = async (photoId) => {
    if (!commentText.trim()) return;
    try {
      await axios.post(
        `${API}/photos/${photoId}/comment`,
        { text: commentText },
        { params: { userId: user.id } }
      );
      toast.success('Comment added!');
      setCommentText('');
      setCommentingOn(null);
      loadPhotos();
    } catch (error) {
      console.error('Failed to comment:', error);
    }
  };

  const getImageUrl = (photoId) => {
    return `${API}/photos/${photoId}/download?userId=${user.id}`;
  };

  const hasUserReacted = (photo) => {
    return photo.reactions?.some((r) => r.userId === user.id);
  };

  if (loading) {
    return (
      <div className="h-full flex items-center justify-center">
        <p className="text-[#52525B]">Loading photos...</p>
      </div>
    );
  }

  const renderPhotoCard = (photo, index) => (
    <motion.div
      key={photo.id}
      initial={{ opacity: 0, y: 20 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ delay: index * 0.05 }}
      className={`bg-white border-2 border-[#121212] rounded-2xl overflow-hidden neo-brutal-shadow-lg ${index % 2 === 0 ? '-rotate-1' : 'rotate-1'} hover:rotate-0 transition-transform duration-300`}
      data-testid={`photo-card-${photo.id}`}
    >
      <div className="aspect-square bg-white">
        <img
          src={getImageUrl(photo.id)}
          alt="Memory"
          className="w-full h-full object-cover"
          data-testid={`photo-image-${photo.id}`}
        />
      </div>

      <div className="p-6 space-y-4">
        {photo.caption && (
          <p className="text-lg" data-testid={`photo-caption-${photo.id}`}>{photo.caption}</p>
        )}

        <div className="flex items-center justify-between">
          <div className="flex items-center gap-2">
            {photo.reactions?.map((reaction, idx) => (
              <span key={idx} className="text-2xl" data-testid={`reaction-${photo.id}-${idx}`}>
                {reaction.emoji}
              </span>
            ))}
          </div>

          <div className="flex items-center gap-2">
            <button
              data-testid={`comment-toggle-${photo.id}`}
              onClick={() => setCommentingOn(commentingOn === photo.id ? null : photo.id)}
              className="bg-[#BEE3F8] hover:bg-[#a8d3e8] border-2 border-[#121212] rounded-full p-3 neo-brutal-shadow-sm active:translate-y-[2px] active:translate-x-[2px] active:shadow-none transition-all duration-150"
            >
              <MessageCircle className="w-5 h-5" />
            </button>
            {!hasUserReacted(photo) && (
              <button
                data-testid={`react-button-${photo.id}`}
                onClick={() => handleReact(photo.id)}
                className="bg-[#FF7A9F] hover:bg-[#ff6b8f] text-white border-2 border-[#121212] rounded-full p-3 neo-brutal-shadow-sm active:translate-y-[2px] active:translate-x-[2px] active:shadow-none transition-all duration-150"
              >
                <Heart className="w-5 h-5" fill="white" />
              </button>
            )}
          </div>
        </div>

        {/* Comments List */}
        {photo.comments && photo.comments.length > 0 && (
          <div className="space-y-2 pt-2 border-t-2 border-[#121212]/10">
            {photo.comments.map((c) => (
              <div key={c.id} className="text-sm" data-testid={`comment-${c.id}`}>
                <span className="font-bold">{c.userName}:</span>{' '}
                <span className="text-[#52525B]">{c.text}</span>
              </div>
            ))}
          </div>
        )}

        {/* Comment Input */}
        <AnimatePresence>
          {commentingOn === photo.id && (
            <motion.div
              initial={{ opacity: 0, height: 0 }}
              animate={{ opacity: 1, height: 'auto' }}
              exit={{ opacity: 0, height: 0 }}
              className="flex gap-2 overflow-hidden"
            >
              <Input
                data-testid={`comment-input-${photo.id}`}
                placeholder="Add a comment..."
                value={commentText}
                onChange={(e) => setCommentText(e.target.value)}
                onKeyPress={(e) => e.key === 'Enter' && handleComment(photo.id)}
                className="border-2 border-[#121212] rounded-xl bg-white focus-visible:ring-0 neo-brutal-shadow-sm flex-1"
              />
              <button
                data-testid={`comment-submit-${photo.id}`}
                onClick={() => handleComment(photo.id)}
                disabled={!commentText.trim()}
                className="bg-[#FFE270] hover:bg-[#ffd960] border-2 border-[#121212] rounded-xl p-3 neo-brutal-shadow-sm active:translate-y-[2px] active:translate-x-[2px] active:shadow-none transition-all duration-150 disabled:opacity-50"
              >
                <Send className="w-4 h-4" />
              </button>
            </motion.div>
          )}
        </AnimatePresence>

        <p className="text-sm text-[#52525B]" data-testid={`photo-date-${photo.id}`}>
          {new Date(photo.createdAt).toLocaleDateString('en-US', {
            month: 'long',
            day: 'numeric',
            year: 'numeric',
          })}
        </p>
      </div>
    </motion.div>
  );

  if (photos.length === 0 && memories.length === 0) {
    return (
      <div className="h-full flex items-center justify-center p-6">
        <div className="bg-white border-2 border-[#121212] rounded-3xl p-8 text-center neo-brutal-shadow-lg max-w-md">
          <h2 className="text-2xl font-bold mb-2" data-testid="no-photos-title">No photos yet</h2>
          <p className="text-[#52525B]">Start sharing moments with your partner!</p>
        </div>
      </div>
    );
  }

  return (
    <div className="h-full overflow-y-auto p-6 pb-24">
      <div className="max-w-2xl mx-auto space-y-8">
        {/* Memories Banner */}
        {memories.length > 0 && (
          <motion.div
            initial={{ opacity: 0, y: -20 }}
            animate={{ opacity: 1, y: 0 }}
            className="bg-[#FFE270] border-2 border-[#121212] rounded-2xl p-6 neo-brutal-shadow"
            data-testid="memories-banner"
          >
            <div className="flex items-center gap-2 mb-3">
              <Sparkles className="w-5 h-5" />
              <h3 className="text-lg font-bold">On This Day</h3>
            </div>
            <p className="text-sm text-[#52525B] mb-4">
              {memories.length} memory{memories.length !== 1 ? 'ies' : ''} from your past
            </p>
            <div className="grid grid-cols-3 gap-3">
              {memories.slice(0, 6).map((m) => (
                <div
                  key={m.id}
                  className="aspect-square bg-white border-2 border-[#121212] rounded-xl overflow-hidden neo-brutal-shadow-sm"
                  data-testid={`memory-${m.id}`}
                >
                  <img
                    src={getImageUrl(m.id)}
                    alt="Memory"
                    className="w-full h-full object-cover"
                  />
                </div>
              ))}
            </div>
          </motion.div>
        )}

        {/* Photos Feed */}
        {photos.map((photo, index) => renderPhotoCard(photo, index))}
      </div>
    </div>
  );
}
