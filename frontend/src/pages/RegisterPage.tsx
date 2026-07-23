import React, { useState } from 'react';
import { Link, useNavigate } from 'react-router-dom';
import toast from 'react-hot-toast';
import { UserPlus, Mail, Lock, User } from 'lucide-react';
import { useAuth } from '../context/AuthContext';

export default function RegisterPage() {
  const [name, setName] = useState('');
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [loading, setLoading] = useState(false);
  const { register } = useAuth();
  const navigate = useNavigate();

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    
    if (password.length < 6) {
      return toast.error('Password must be at least 6 characters');
    }
    
    setLoading(true);
    
    try {
      await register(name, email, password);
      toast.success('Account created! Welcome!');
      navigate('/');
    } catch (err: any) {
      toast.error(err.response?.data?.detail || 'Registration failed');
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="min-h-screen flex items-center justify-center p-8 bg-gray-950">
      <div className="w-full max-w-md">
        <div className="text-center mb-8">
          <div className="w-16 h-16 bg-gradient-to-br from-blue-500 to-purple-600 rounded-2xl flex items-center justify-center mx-auto mb-4">
            <span className="text-white text-2xl font-bold">R</span>
          </div>
          <h1 className="text-3xl font-bold bg-gradient-to-r from-blue-400 to-purple-400 bg-clip-text text-transparent">
            Create Account
          </h1>
          <p className="text-gray-400 mt-2">Join the RAG Pipeline platform</p>
        </div>

        <form onSubmit={handleSubmit} className="bg-gray-900 rounded-xl p-8 border border-gray-800 space-y-4">
          <div>
            <label className="block text-sm text-gray-400 mb-2">Full Name</label>
            <div className="relative">
              <User className="absolute left-3 top-3 text-gray-500" size={16} />
              <input
                type="text"
                value={name}
                onChange={e => setName(e.target.value)}
                required
                className="w-full bg-gray-800 border border-gray-700 rounded-lg pl-10 pr-4 py-2 text-white focus:outline-none focus:border-blue-500"
                placeholder="Your name"
              />
            </div>
          </div>

          <div>
            <label className="block text-sm text-gray-400 mb-2">Email</label>
            <div className="relative">
              <Mail className="absolute left-3 top-3 text-gray-500" size={16} />
              <input
                type="email"
                value={email}
                onChange={e => setEmail(e.target.value)}
                required
                className="w-full bg-gray-800 border border-gray-700 rounded-lg pl-10 pr-4 py-2 text-white focus:outline-none focus:border-blue-500"
                placeholder="you@example.com"
              />
            </div>
          </div>

          <div>
            <label className="block text-sm text-gray-400 mb-2">Password</label>
            <div className="relative">
              <Lock className="absolute left-3 top-3 text-gray-500" size={16} />
              <input
                type="password"
                value={password}
                onChange={e => setPassword(e.target.value)}
                required
                minLength={6}
                className="w-full bg-gray-800 border border-gray-700 rounded-lg pl-10 pr-4 py-2 text-white focus:outline-none focus:border-blue-500"
                placeholder="At least 6 characters"
              />
            </div>
          </div>

          <button
            type="submit"
            disabled={loading}
            className="w-full bg-blue-600 hover:bg-blue-700 disabled:bg-gray-700 py-3 rounded-lg flex items-center justify-center gap-2 transition font-medium"
          >
            {loading ? (
              <div className="w-4 h-4 border-2 border-white border-t-transparent rounded-full animate-spin" />
            ) : (
              <>
                <UserPlus size={16} />
                Create Account
              </>
            )}
          </button>

          <p className="text-center text-gray-400 text-sm">
            Already have an account?{' '}
            <Link to="/login" className="text-blue-400 hover:text-blue-300">
              Sign in
            </Link>
          </p>
        </form>
      </div>
    </div>
  );
}