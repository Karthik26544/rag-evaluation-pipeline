import React, { useState } from 'react';
import { BrowserRouter as Router, Routes, Route, Link, useLocation, Navigate } from 'react-router-dom';
import { Toaster } from 'react-hot-toast';
import { Upload, MessageSquare, BarChart3, LayoutDashboard, LogOut, Award, History, HelpCircle, MessageCircle, Menu, X } from 'lucide-react';
import { AuthProvider, useAuth } from './context/AuthContext';
import ProtectedRoute from './components/ProtectedRoute';
import UploadPage from './pages/UploadPage';
import ChatPage from './pages/ChatPage';
import EvaluationPage from './pages/EvaluationPage';
import DashboardPage from './pages/DashboardPage';
import LoginPage from './pages/LoginPage';
import RegisterPage from './pages/RegisterPage';
import AdminDashboard from './pages/AdminDashboard';
import HistoryPage from './pages/HistoryPage';
import AppTour, { startTourManually } from './components/AppTour';
import FeedbackModal from './components/FeedbackModal';

function Navigation() {
  const location = useLocation();
  const { user, logout } = useAuth();
  const [feedbackOpen, setFeedbackOpen] = useState(false);
  const [mobileMenuOpen, setMobileMenuOpen] = useState(false);

  if (!user) return null;

  const links = [
    { path: '/', label: 'Upload', icon: Upload },
    { path: '/chat', label: 'Ask', icon: MessageSquare },
    { path: '/history', label: 'History', icon: History },
    { path: '/evaluate', label: 'Evaluate', icon: BarChart3 },
    { path: '/dashboard', label: 'Dashboard', icon: LayoutDashboard },
  ];

  if (user.is_admin) {
    links.push({ path: '/admin', label: 'Admin', icon: Award });
  }

  const closeMobileMenu = () => setMobileMenuOpen(false);

  return (
    <>
      <nav className="bg-gray-900 border-b border-gray-800 px-4 md:px-6 py-4 sticky top-0 z-50">
        <div className="max-w-6xl mx-auto flex items-center justify-between">
          {/* Logo */}
          <div className="flex items-center gap-2">
            <div className="w-8 h-8 bg-gradient-to-br from-blue-500 to-purple-600 rounded-lg flex items-center justify-center flex-shrink-0">
              <span className="text-white font-bold">R</span>
            </div>
            <h1 className="text-lg md:text-xl font-bold bg-gradient-to-r from-blue-400 to-purple-400 bg-clip-text text-transparent">
              RAG Pipeline
            </h1>
          </div>
          
          {/* Desktop Navigation - Hidden on mobile */}
          <div className="hidden lg:flex items-center gap-1">
            {links.map(link => {
              const Icon = link.icon;
              const active = location.pathname === link.path;
              return (
                <Link
                  key={link.path}
                  to={link.path}
                  className={`flex items-center gap-2 px-3 py-2 rounded-lg transition ${
                    active
                      ? 'bg-blue-600 text-white'
                      : 'text-gray-400 hover:text-white hover:bg-gray-800'
                  }`}
                >
                  <Icon size={14} />
                  <span className="text-sm">{link.label}</span>
                </Link>
              );
            })}
            
            <div className="ml-4 flex items-center gap-2 border-l border-gray-800 pl-4">
              <div className="w-8 h-8 bg-gradient-to-br from-blue-500 to-purple-600 rounded-full flex items-center justify-center text-sm font-bold">
                {user.name.charAt(0).toUpperCase()}
              </div>
              <span className="text-sm text-gray-300 max-w-[100px] truncate">{user.name}</span>
              <button
                onClick={() => setFeedbackOpen(true)}
                className="p-2 text-gray-400 hover:text-yellow-400 transition"
                title="Send Feedback"
                id="feedback-btn"
              >
                <MessageCircle size={16} />
              </button>
              <button
                onClick={startTourManually}
                className="p-2 text-gray-400 hover:text-blue-400 transition"
                title="Start Tour"
                id="tour-btn"
              >
                <HelpCircle size={16} />
              </button>
              <button
                onClick={logout}
                className="p-2 text-gray-400 hover:text-red-400 transition"
                title="Logout"
              >
                <LogOut size={16} />
              </button>
            </div>
          </div>

          {/* Mobile: User avatar + Hamburger button */}
          <div className="flex lg:hidden items-center gap-2">
            <div className="w-8 h-8 bg-gradient-to-br from-blue-500 to-purple-600 rounded-full flex items-center justify-center text-sm font-bold">
              {user.name.charAt(0).toUpperCase()}
            </div>
            <button
              onClick={() => setMobileMenuOpen(!mobileMenuOpen)}
              className="p-2 text-gray-400 hover:text-white hover:bg-gray-800 rounded-lg transition"
              aria-label="Toggle menu"
            >
              {mobileMenuOpen ? <X size={22} /> : <Menu size={22} />}
            </button>
          </div>
        </div>
      </nav>

      {/* Mobile Menu Overlay */}
      {mobileMenuOpen && (
        <div 
          className="lg:hidden fixed inset-0 bg-black/70 z-40"
          onClick={closeMobileMenu}
        />
      )}

      {/* Mobile Menu Slide-in Panel */}
      <div 
        className={`lg:hidden fixed top-0 right-0 h-full w-72 bg-gray-900 border-l border-gray-800 z-50 transform transition-transform duration-300 ease-in-out ${
          mobileMenuOpen ? 'translate-x-0' : 'translate-x-full'
        }`}
      >
        {/* Header */}
        <div className="p-4 border-b border-gray-800 flex items-center justify-between">
          <div className="flex items-center gap-3">
            <div className="w-10 h-10 bg-gradient-to-br from-blue-500 to-purple-600 rounded-full flex items-center justify-center font-bold">
              {user.name.charAt(0).toUpperCase()}
            </div>
            <div>
              <p className="font-medium text-sm">{user.name}</p>
              <p className="text-xs text-gray-500">{user.email}</p>
              {user.is_admin && (
                <span className="text-xs bg-yellow-500/10 text-yellow-400 px-2 py-0.5 rounded inline-block mt-1">
                  Admin
                </span>
              )}
            </div>
          </div>
          <button
            onClick={closeMobileMenu}
            className="p-2 text-gray-400 hover:text-white hover:bg-gray-800 rounded-lg transition"
          >
            <X size={20} />
          </button>
        </div>

        {/* Navigation Links */}
        <div className="p-4 space-y-1">
          <p className="text-xs uppercase text-gray-500 font-semibold mb-2 px-3">Navigation</p>
          {links.map(link => {
            const Icon = link.icon;
            const active = location.pathname === link.path;
            return (
              <Link
                key={link.path}
                to={link.path}
                onClick={closeMobileMenu}
                className={`flex items-center gap-3 px-3 py-3 rounded-lg transition ${
                  active
                    ? 'bg-blue-600 text-white'
                    : 'text-gray-300 hover:text-white hover:bg-gray-800'
                }`}
              >
                <Icon size={18} />
                <span className="text-sm font-medium">{link.label}</span>
              </Link>
            );
          })}
        </div>

        {/* Actions */}
        <div className="p-4 border-t border-gray-800 space-y-1">
          <p className="text-xs uppercase text-gray-500 font-semibold mb-2 px-3">Actions</p>
          <button
            onClick={() => { setFeedbackOpen(true); closeMobileMenu(); }}
            className="w-full flex items-center gap-3 px-3 py-3 text-gray-300 hover:text-yellow-400 hover:bg-gray-800 rounded-lg transition"
          >
            <MessageCircle size={18} />
            <span className="text-sm font-medium">Send Feedback</span>
          </button>
          <button
            onClick={() => { startTourManually(); closeMobileMenu(); }}
            className="w-full flex items-center gap-3 px-3 py-3 text-gray-300 hover:text-blue-400 hover:bg-gray-800 rounded-lg transition"
          >
            <HelpCircle size={18} />
            <span className="text-sm font-medium">Start Tour</span>
          </button>
          <button
            onClick={() => { logout(); closeMobileMenu(); }}
            className="w-full flex items-center gap-3 px-3 py-3 text-gray-300 hover:text-red-400 hover:bg-gray-800 rounded-lg transition"
          >
            <LogOut size={18} />
            <span className="text-sm font-medium">Logout</span>
          </button>
        </div>
      </div>

      <FeedbackModal isOpen={feedbackOpen} onClose={() => setFeedbackOpen(false)} />
    </>
  );
}

function AppContent() {
  return (
    <div className="min-h-screen bg-gray-950 text-white">
      <Navigation />
      <AppTour />
      <Routes>
        <Route path="/login" element={<LoginPage />} />
        <Route path="/register" element={<RegisterPage />} />
        
        <Route path="/" element={<ProtectedRoute><UploadPage /></ProtectedRoute>} />
        <Route path="/chat" element={<ProtectedRoute><ChatPage /></ProtectedRoute>} />
        <Route path="/history" element={<ProtectedRoute><HistoryPage /></ProtectedRoute>} />
        <Route path="/evaluate" element={<ProtectedRoute><EvaluationPage /></ProtectedRoute>} />
        <Route path="/dashboard" element={<ProtectedRoute><DashboardPage /></ProtectedRoute>} />
        <Route path="/admin" element={<ProtectedRoute adminOnly><AdminDashboard /></ProtectedRoute>} />
        
        <Route path="*" element={<Navigate to="/" replace />} />
      </Routes>
    </div>
  );
}

function App() {
  return (
    <AuthProvider>
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
        <AppContent />
      </Router>
    </AuthProvider>
  );
}

export default App;