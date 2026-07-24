import React, { useState } from 'react';
import axios from 'axios';
import toast from 'react-hot-toast';
import { X, Star, Send } from 'lucide-react';

const API = process.env.REACT_APP_API_URL;

interface Props {
  isOpen: boolean;
  onClose: () => void;
}

export default function FeedbackModal({ isOpen, onClose }: Props) {
  const [rating, setRating] = useState(0);
  const [hoveredRating, setHoveredRating] = useState(0);
  const [comment, setComment] = useState('');
  const [category, setCategory] = useState('general');
  const [submitting, setSubmitting] = useState(false);

  if (!isOpen) return null;

  const handleSubmit = async () => {
    if (rating === 0) {
      toast.error('Please select a rating');
      return;
    }

    setSubmitting(true);
    try {
      await axios.post(`${API}/feedback/submit`, {
        rating,
        comment,
        category
      });
      
      toast.success('Thank you for your feedback! 🎉');
      setRating(0);
      setComment('');
      setCategory('general');
      onClose();
    } catch (err: any) {
      toast.error(err.response?.data?.detail || 'Failed to submit feedback');
    } finally {
      setSubmitting(false);
    }
  };

  const getRatingLabel = (r: number) => {
    if (r === 0) return 'Select rating';
    if (r === 1) return '😞 Poor';
    if (r === 2) return '😐 Fair';
    if (r === 3) return '🙂 Good';
    if (r === 4) return '😊 Great';
    if (r === 5) return '🤩 Excellent';
    return '';
  };

  const displayRating = hoveredRating || rating;

  return (
    <div 
      className="fixed inset-0 bg-black/70 z-[100] flex items-center justify-center p-4"
      onClick={onClose}
    >
      <div 
        className="bg-gray-900 border border-gray-800 rounded-xl max-w-md w-full"
        onClick={e => e.stopPropagation()}
      >
        <div className="p-6 border-b border-gray-800 flex items-center justify-between">
          <div>
            <h3 className="text-xl font-bold flex items-center gap-2">
              <Star className="text-yellow-400" size={20} />
              Share Your Feedback
            </h3>
            <p className="text-sm text-gray-400 mt-1">Help us improve!</p>
          </div>
          <button 
            onClick={onClose}
            className="p-2 hover:bg-gray-800 rounded-lg transition"
          >
            <X size={20} />
          </button>
        </div>

        <div className="p-6 space-y-4">
          <div>
            <label className="block text-sm text-gray-400 mb-3">
              How would you rate your experience?
            </label>
            <div className="flex justify-center gap-2 mb-2">
              {[1, 2, 3, 4, 5].map(star => (
                <button
                  key={star}
                  onClick={() => setRating(star)}
                  onMouseEnter={() => setHoveredRating(star)}
                  onMouseLeave={() => setHoveredRating(0)}
                  className="transition-transform hover:scale-110"
                >
                  <Star
                    size={40}
                    className={`transition-colors ${
                      star <= displayRating
                        ? 'fill-yellow-400 text-yellow-400'
                        : 'text-gray-600'
                    }`}
                  />
                </button>
              ))}
            </div>
            <p className="text-center text-sm text-gray-400">
              {getRatingLabel(displayRating)}
            </p>
          </div>

          <div>
            <label className="block text-sm text-gray-400 mb-2">
              What is this about?
            </label>
            <select
              value={category}
              onChange={e => setCategory(e.target.value)}
              className="w-full bg-gray-800 border border-gray-700 rounded-lg px-4 py-2 text-white focus:outline-none focus:border-blue-500"
            >
              <option value="general">General Feedback</option>
              <option value="ui">User Interface</option>
              <option value="performance">Performance</option>
              <option value="features">Feature Request</option>
              <option value="bug">Bug Report</option>
              <option value="ai_quality">AI Answer Quality</option>
            </select>
          </div>

          <div>
            <label className="block text-sm text-gray-400 mb-2">
              Tell us more (optional)
            </label>
            <textarea
              value={comment}
              onChange={e => setComment(e.target.value)}
              placeholder="What did you like? What could be improved?"
              rows={4}
              className="w-full bg-gray-800 border border-gray-700 rounded-lg px-4 py-2 text-white placeholder-gray-500 focus:outline-none focus:border-blue-500 resize-none"
            />
          </div>

          <button
            onClick={handleSubmit}
            disabled={submitting || rating === 0}
            className="w-full bg-gradient-to-r from-blue-600 to-purple-600 hover:from-blue-700 hover:to-purple-700 disabled:from-gray-700 disabled:to-gray-700 py-3 rounded-lg flex items-center justify-center gap-2 transition font-medium"
          >
            {submitting ? (
              <>
                <div className="w-4 h-4 border-2 border-white border-t-transparent rounded-full animate-spin" />
                Submitting...
              </>
            ) : (
              <>
                <Send size={16} />
                Submit Feedback
              </>
            )}
          </button>
        </div>
      </div>
    </div>
  );
}