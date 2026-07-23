import React from 'react';
import { BrowserRouter as Router, Routes, Route, Link, useLocation, Navigate } from 'react-router-dom';
import { Toaster } from 'react-hot-toast';
import { Upload, MessageSquare, BarChart3, LayoutDashboard, LogOut, User, Award } from 'lucide-react';
import { AuthProvider, useAuth } from './context/AuthContext';
import ProtectedRoute from './components/ProtectedRoute';
import UploadPage from './pages/UploadPage';
import ChatPage from './pages/ChatPage';
import EvaluationPage from './pages/EvaluationPage';
import DashboardPage from './pages/DashboardPage';
import LoginPage from './pages/LoginPage';
import RegisterPage from './pages/RegisterPage';
import AdminDashboard from './pages/AdminDashboard';

function Navigation() {
  const location = useLocation();
  const { user, logout } = useAuth();

  if (!user) return null;

  const links = [
    { path: '/', label: 'Upload', icon: Upload },
    { path: '/chat', label: 'Ask', icon: MessageSquare },
    { path: '/evaluate', label: 'Evaluate', icon: BarChart3 },
    { path: '/dashboard', label: 'Dashboard', icon: LayoutDashboard },
  ];

  if (user.is_admin) {
    links.push({ path: '/admin', label: 'Admin', icon: Award });
  }

  return (
    <nav className="bg-gray-900 border-b border-gray-800 px-6 py-4 sticky top-0 z-50">
      <div className="max-w-6xl mx-auto flex items-center justify-between">
        <div className="flex items-center gap-2">
          <div className="w-8 h-8 bg-gradient-to-br from-blue-500 to-purple-600 rounded-lg flex items-center justify-center">
            <span className="text-white font-bold">R</span>
          </div>
          <h1 className="text-xl font-bold bg-gradient-to-r from-blue-400 to-purple-400 bg-clip-text text-transparent">
            RAG Pipeline
          </h1>
        </div>
        
        <div className="flex items-center gap-1">
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
            <span className="text-sm text-gray-300">{user.name}</span>
            <button
              onClick={logout}
              className="p-2 text-gray-400 hover:text-red-400 transition"
              title="Logout"
            >
              <LogOut size={16} />
            </button>
          </div>
        </div>
      </div>
    </nav>
  );
}

function AppContent() {
  return (
    <div className="min-h-screen bg-gray-950 text-white">
      <Navigation />
      <Routes>
        <Route path="/login" element={<LoginPage />} />
        <Route path="/register" element={<RegisterPage />} />
        
        <Route path="/" element={<ProtectedRoute><UploadPage /></ProtectedRoute>} />
        <Route path="/chat" element={<ProtectedRoute><ChatPage /></ProtectedRoute>} />
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