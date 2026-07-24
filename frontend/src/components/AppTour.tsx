import { useEffect, useCallback } from 'react';
import { driver } from 'driver.js';
import 'driver.js/dist/driver.css';
import { useAuth } from '../context/AuthContext';

const TOUR_STORAGE_KEY = 'rag_tour_completed';

interface Props {
  forceStart?: boolean;
  onComplete?: () => void;
}

export default function AppTour({ forceStart = false, onComplete }: Props) {
  const { user } = useAuth();

  const startTour = useCallback(() => {
    if (!user) return;

    const driverObj = driver({
      showProgress: true,
      animate: true,
      overlayColor: 'rgba(0, 0, 0, 0.75)',
      progressText: 'Step {{current}} of {{total}}',
      nextBtnText: 'Next →',
      prevBtnText: '← Back',
      doneBtnText: 'Finish Tour ✓',
      onDestroyed: () => {
        localStorage.setItem(TOUR_STORAGE_KEY, 'true');
        if (onComplete) onComplete();
      },
      steps: [
        {
          element: 'nav',
          popover: {
            title: '👋 Welcome to RAG Pipeline!',
description: `Hi ${user?.name}! Let me walk you through this AI-powered document Q&A system. This tour has 10 quick steps.`,
            side: 'bottom',
            align: 'center',
          }
        },
        {
          element: 'a[href="/"]',
          popover: {
            title: '📄 Upload Documents',
            description: 'Start by uploading your documents here. We support PDF, DOCX, TXT, and Markdown files. Choose from 3 chunking strategies for different content types.',
            side: 'bottom',
            align: 'start',
          }
        },
        {
          element: 'a[href="/chat"]',
          popover: {
            title: '💬 Ask Questions',
            description: 'Ask questions about your documents. Our AI uses hybrid search (vector + BM25), query rewriting, and cross-encoder reranking to give you accurate answers with source citations.',
            side: 'bottom',
            align: 'start',
          }
        },
        {
          element: 'a[href="/history"]',
          popover: {
            title: '📋 Your History',
            description: 'View all your past questions and answers. Search through them, see confidence scores, and delete old queries anytime.',
            side: 'bottom',
            align: 'start',
          }
        },
        {
          element: 'a[href="/evaluate"]',
          popover: {
            title: '📊 Evaluation Pipeline',
            description: 'The gold feature! Compare different retrieval strategies quantitatively. Add test questions with expected answers and see which strategy works best (measured by faithfulness and relevancy).',
            side: 'bottom',
            align: 'start',
          }
        },
        {
          element: 'a[href="/dashboard"]',
          popover: {
            title: '📈 Analytics Dashboard',
            description: 'See system-wide metrics: total documents, queries processed, strategy comparisons, and performance charts.',
            side: 'bottom',
            align: 'start',
          }
        },
...(user?.is_admin ? [{
          element: 'a[href="/admin"]',
          popover: {
            title: '👑 Admin Panel (Admin Only)',
            description: 'Since you are an admin, you have access to user management, platform analytics, cost tracking, feedback review, and CSV data export.',
            side: 'bottom' as const,
            align: 'start' as const,
          }
        }] : []),
        {
          element: '#feedback-btn',
          popover: {
            title: '💬 Share Your Feedback',
            description: 'Love the app? Have suggestions? Click this button anytime to rate your experience and send feedback. Your input helps us improve!',
            side: 'bottom',
            align: 'end',
          }
        },
        {
          element: '#tour-btn',
          popover: {
            title: '❓ Need a Refresher?',
            description: 'Click this help button anytime to restart this tour and see all features again.',
            side: 'bottom',
            align: 'end',
          }
        },
        {
          element: 'nav button[title="Logout"]',
          popover: {
            title: '🎉 You are all set!',
            description: 'Great job! Start by uploading a document, then ask questions. Your Gemini API is rate-limited (10 queries/min), and answers are cached to save resources. Click "Finish Tour" to begin!',
            side: 'bottom',
            align: 'end',
          }
        }
      ]
    });

    driverObj.drive();
  }, [user, onComplete]);

  useEffect(() => {
    const tourCompleted = localStorage.getItem(TOUR_STORAGE_KEY);
    
    if (!user) return;
    if (!forceStart && tourCompleted === 'true') return;
    
    const timer = setTimeout(() => {
      startTour();
    }, 500);
    
    return () => clearTimeout(timer);
  }, [forceStart, user, startTour]);

  return null;
}

export function startTourManually() {
  localStorage.removeItem(TOUR_STORAGE_KEY);
  window.location.reload();
}