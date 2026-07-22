import React from 'react';
import { BrowserRouter as Router, Routes, Route, Link, useLocation } from 'react-router-dom';
import { Toaster } from 'react-hot-toast';
import { Upload, MessageSquare, BarChart3, LayoutDashboard } from 'lucide-react';
import UploadPage from './pages/UploadPage';
import ChatPage from './pages/ChatPage';
import EvaluationPage from './pages/EvaluationPage';
import DashboardPage from './pages/DashboardPage';

function Navigation() {
  const location = useLocation();
  
  const links = [
    { path: '/', label: 'Upload', icon: Upload },
    { path: '/chat', label: 'Ask Questions', icon: MessageSquare },
    { path: '/evaluate', label: 'Evaluate', icon: BarChart3 },
    { path: '/dashboard', label: 'Dashboard', icon: LayoutDashboard },
  ];
  
  return (
    <nav className="bg-gray-900 border-b border-gray-800 px-6 py-4 sticky top-0 z-50">
      <div className="max-w-6xl mx-auto flex items-center justify-between">
        <div className="flex items-center gap-2">
          <div className="w-8 h-8 bg-gradient-to-br from-blue-500 to-purple-600 rounded-lg flex items-center justify-center">
            <span className="text-white font-bold">R</span>
          </div>
          <h1 className="text-xl font-bold bg-gradient-to-r from-blue-400 to-purple-400 bg-clip-text text-transparent">
            RAG Evaluation Pipeline
          </h1>
        </div>
        <div className="flex gap-1">
          {links.map(link => {
            const Icon = link.icon;
            const active = location.pathname === link.path;
            return (
              <Link
                key={link.path}
                to={link.path}
                className={`flex items-center gap-2 px-4 py-2 rounded-lg transition ${
                  active
                    ? 'bg-blue-600 text-white'
                    : 'text-gray-400 hover:text-white hover:bg-gray-800'
                }`}
              >
                <Icon size={16} />
                <span className="text-sm font-medium">{link.label}</span>
              </Link>
            );
          })}
        </div>
      </div>
    </nav>
  );
}

function App() {
  return (
    <Router>
      <Toaster 
        position="top-right"
        toastOptions={{
          style: {
            background: '#1F2937',
            color: '#fff',
            border: '1px solid #374151',
          },
        }}
      />
<div className="min-h-screen bg-gray-950 text-white">
  <Navigation />
  <div className="bg-gradient-to-r from-blue-600/10 to-purple-600/10 border-b border-blue-500/20 px-6 py-2">
    <div className="max-w-6xl mx-auto flex items-center justify-center gap-2 text-sm text-blue-300">
      <span>ℹ️</span>
      <span>
        Demo mode: Free Gemini API with rate limits (15 requests/min). 
        If you see an error, please wait a minute and try again.
      </span>
    </div>
  </div>
        <Routes>
          <Route path="/" element={<UploadPage />} />
          <Route path="/chat" element={<ChatPage />} />
          <Route path="/evaluate" element={<EvaluationPage />} />
          <Route path="/dashboard" element={<DashboardPage />} />
        </Routes>
      </div>
    </Router>
  );
}

export default App;