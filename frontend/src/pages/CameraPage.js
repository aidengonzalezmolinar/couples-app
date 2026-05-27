import React, { useState, useRef, useEffect } from 'react';
import { useAuth } from '../context/AuthContext';
import { Button } from '../components/ui/button';
import { Textarea } from '../components/ui/textarea';
import { motion, AnimatePresence } from 'framer-motion';
import { Camera, Upload, X } from 'lucide-react';
import axios from 'axios';
import { toast } from 'sonner';

const BACKEND_URL = process.env.REACT_APP_BACKEND_URL;
const API = `${BACKEND_URL}/api`;

export default function CameraPage() {
  const { user } = useAuth();
  const [capturedImage, setCapturedImage] = useState(null);
  const [caption, setCaption] = useState('');
  const [uploading, setUploading] = useState(false);
  const fileInputRef = useRef(null);

  const handleFileSelect = (e) => {
    const file = e.target.files[0];
    if (file) {
      const reader = new FileReader();
      reader.onload = (e) => {
        setCapturedImage({ url: e.target.result, file });
      };
      reader.readAsDataURL(file);
    }
  };

  const handleUpload = async () => {
    if (!capturedImage || !user) return;

    setUploading(true);
    try {
      const formData = new FormData();
      formData.append('file', capturedImage.file);
      formData.append('userId', user.id);
      formData.append('caption', caption || '');

      await axios.post(`${API}/photos/upload`, formData, {
        headers: { 'Content-Type': 'multipart/form-data' },
      });

      toast.success('Photo shared with your partner!');
      setCapturedImage(null);
      setCaption('');
    } catch (error) {
      console.error('Upload failed:', error);
      toast.error('Failed to upload photo');
    } finally {
      setUploading(false);
    }
  };

  return (
    <div className="h-full flex flex-col p-6 pb-24">
      <AnimatePresence mode="wait">
        {!capturedImage ? (
          <motion.div
            key="capture"
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            exit={{ opacity: 0 }}
            className="flex-1 flex flex-col items-center justify-center"
          >
            <div className="w-full max-w-md">
              <div className="bg-white border-2 border-[#121212] rounded-3xl p-8 text-center neo-brutal-shadow-lg mb-6">
                <Camera className="w-16 h-16 mx-auto mb-4 text-[#FF7A9F]" data-testid="camera-icon" />
                <h2 className="text-2xl font-bold mb-2">Share a moment</h2>
                <p className="text-[#52525B] mb-6">Capture or upload a photo for your partner</p>
              </div>

              <Button
                data-testid="select-photo-button"
                onClick={() => fileInputRef.current?.click()}
                className="w-full bg-[#FF7A9F] hover:bg-[#ff6b8f] text-white border-2 border-[#121212] rounded-2xl py-8 text-lg font-bold neo-brutal-shadow active:translate-y-[4px] active:translate-x-[4px] active:shadow-none transition-all duration-150"
              >
                <Upload className="w-6 h-6 mr-2" />
                Select Photo
              </Button>

              <input
                ref={fileInputRef}
                type="file"
                accept="image/*"
                capture="environment"
                onChange={handleFileSelect}
                className="hidden"
              />
            </div>
          </motion.div>
        ) : (
          <motion.div
            key="preview"
            initial={{ opacity: 0, scale: 0.9 }}
            animate={{ opacity: 1, scale: 1 }}
            exit={{ opacity: 0, scale: 0.9 }}
            className="flex-1 flex flex-col"
          >
            <div className="flex-1 flex flex-col">
              <div className="relative bg-white border-2 border-[#121212] rounded-3xl overflow-hidden neo-brutal-shadow-lg mb-4">
                <img
                  src={capturedImage.url}
                  alt="Captured"
                  className="w-full h-auto"
                  data-testid="captured-image-preview"
                />
                <button
                  data-testid="remove-photo-button"
                  onClick={() => setCapturedImage(null)}
                  className="absolute top-4 right-4 bg-white border-2 border-[#121212] rounded-full p-2 neo-brutal-shadow-sm hover:bg-[#FFF9F0] active:translate-y-[2px] active:translate-x-[2px] active:shadow-none transition-all duration-150"
                >
                  <X className="w-5 h-5" />
                </button>
              </div>

              <div className="space-y-4">
                <Textarea
                  data-testid="caption-input"
                  placeholder="Add a caption... (optional)"
                  value={caption}
                  onChange={(e) => setCaption(e.target.value)}
                  className="border-2 border-[#121212] rounded-xl bg-white focus-visible:ring-0 focus-visible:bg-[#FFF9F0] neo-brutal-shadow p-4 resize-none"
                  rows={3}
                />

                <Button
                  data-testid="send-photo-button"
                  onClick={handleUpload}
                  disabled={uploading}
                  className="w-full bg-[#FFE270] hover:bg-[#ffd960] text-[#121212] border-2 border-[#121212] rounded-xl py-6 text-lg font-bold neo-brutal-shadow active:translate-y-[4px] active:translate-x-[4px] active:shadow-none transition-all duration-150"
                >
                  {uploading ? 'Sending...' : 'Send to Partner'}
                </Button>
              </div>
            </div>
          </motion.div>
        )}
      </AnimatePresence>
    </div>
  );
}
