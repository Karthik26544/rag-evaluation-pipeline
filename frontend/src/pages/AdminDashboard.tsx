import React, { useState, useEffect } from 'react';
import axios from 'axios';
import {
  BarChart, Bar, LineChart, Line, PieChart, Pie, Cell,
  XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer, Legend
} from 'recharts';
import { Users, FileText, MessageSquare, Zap, TrendingUp, Clock, Award, Trash2 } from 'lucide-react';
import toast from 'react-hot-toast';

const API = process.env.REACT_APP_API_URL;

const COLORS = ['#3B82F6', '#10B981', '#F59E0B', '#8B5CF6', '#EF4444'];

export default function AdminDashboard() {
  const [stats, setStats] = useState<any>(null);
  const [users, setUsers] = useState<any[]>([]);
  const [queries, setQueries] = useState<any[]>([]);
  const [analytics, setAnalytics] = useState<any>(null);
  const [activeTab, setActiveTab] = useState('overview');

  useEffect(() => {
    fetchAll();
    const interval = setInterval(fetchAll, 30000);
    return () => clearInterval(interval);
  }, []);

  const fetchAll = async () => {
    try {
      const [s, u, q, a] = await Promise.all([
        axios.get(`${API}/admin/stats`),
        axios.get(`${API}/admin/users`),
        axios.get(`${API}/admin/queries/recent`),
        axios.get(`${API}/admin/analytics/growth`),
      ]);
      setStats(s.data);
      setUsers(u.data.users);
      setQueries(q.data.queries);
      setAnalytics(a.data);
    } catch (err) {
      console.error(err);
    }
  };

  const deleteUser = async (userId: string) => {
    if (!window.confirm('Delete this user?')) return;
    try {
      await axios.delete(`${API}/admin/users/${userId}`);
      toast.success('User deleted');
      fetchAll();
    } catch (err: any) {
      toast.error(err.response?.data?.detail || 'Failed');
    }
  };

  if (!stats) {
    return (
      <div className="max-w-6xl mx-auto p-8 text-center text-gray-400">
        <div className="w-8 h-8 border-2 border-blue-500 border-t-transparent rounded-full animate-spin mx-auto mb-3" />
        Loading admin dashboard...
      </div>
    );
  }

  return (
    <div className="max-w-6xl mx-auto p-8">
      <div className="mb-8">
        <div className="flex items-center gap-2 mb-2">
          <Award className="text-yellow-400" />
          <h2 className="text-3xl font-bold">Admin Dashboard</h2>
        </div>
        <p className="text-gray-400">Platform analytics and user management</p>
      </div>

      <div className="grid grid-cols-4 gap-4 mb-6">
        <StatCard icon={<Users className="text-blue-400" />} label="Total Users" value={stats.total_users} sub={`+${stats.new_users_week} this week`} />
        <StatCard icon={<FileText className="text-green-400" />} label="Documents" value={stats.total_documents} />
        <StatCard icon={<MessageSquare className="text-purple-400" />} label="Queries" value={stats.total_queries} sub={`${stats.queries_today} today`} />
        <StatCard icon={<TrendingUp className="text-yellow-400" />} label="Evaluations" value={stats.total_evaluations} />
      </div>

      <div className="grid grid-cols-2 gap-4 mb-8">
        <div className="bg-gray-900 rounded-xl p-5 border border-gray-800">
          <div className="flex items-center gap-2 mb-2">
            <Clock className="text-blue-400" size={18} />
            <span className="text-sm text-gray-400">Avg Response Time</span>
          </div>
          <p className="text-2xl font-bold">{stats.avg_latency_ms}ms</p>
        </div>
        <div className="bg-gray-900 rounded-xl p-5 border border-gray-800">
          <div className="flex items-center gap-2 mb-2">
            <Zap className="text-green-400" size={18} />
            <span className="text-sm text-gray-400">Avg Confidence</span>
          </div>
          <p className="text-2xl font-bold">{Math.round(stats.avg_confidence * 100)}%</p>
        </div>
      </div>

      <div className="flex gap-2 mb-4 border-b border-gray-800">
        {['overview', 'users', 'queries'].map(tab => (
          <button
            key={tab}
            onClick={() => setActiveTab(tab)}
            className={`px-4 py-2 capitalize transition ${
              activeTab === tab
                ? 'text-white border-b-2 border-blue-500'
                : 'text-gray-500 hover:text-white'
            }`}
          >
            {tab}
          </button>
        ))}
      </div>

      {activeTab === 'overview' && analytics && (
        <div className="grid grid-cols-2 gap-6">
          <div className="bg-gray-900 rounded-xl p-6 border border-gray-800">
            <h3 className="font-semibold mb-4">User Growth (30 days)</h3>
            <ResponsiveContainer width="100%" height={250}>
              <LineChart data={analytics.users_growth}>
                <CartesianGrid strokeDasharray="3 3" stroke="#374151" />
                <XAxis dataKey="date" stroke="#9CA3AF" style={{ fontSize: '10px' }} />
                <YAxis stroke="#9CA3AF" />
                <Tooltip contentStyle={{ backgroundColor: '#1F2937', border: '1px solid #374151' }} />
                <Line type="monotone" dataKey="count" stroke="#3B82F6" strokeWidth={2} />
              </LineChart>
            </ResponsiveContainer>
          </div>

          <div className="bg-gray-900 rounded-xl p-6 border border-gray-800">
            <h3 className="font-semibold mb-4">Query Growth (30 days)</h3>
            <ResponsiveContainer width="100%" height={250}>
              <LineChart data={analytics.queries_growth}>
                <CartesianGrid strokeDasharray="3 3" stroke="#374151" />
                <XAxis dataKey="date" stroke="#9CA3AF" style={{ fontSize: '10px' }} />
                <YAxis stroke="#9CA3AF" />
                <Tooltip contentStyle={{ backgroundColor: '#1F2937', border: '1px solid #374151' }} />
                <Line type="monotone" dataKey="count" stroke="#10B981" strokeWidth={2} />
              </LineChart>
            </ResponsiveContainer>
          </div>

          <div className="bg-gray-900 rounded-xl p-6 border border-gray-800 col-span-2">
            <h3 className="font-semibold mb-4">Search Method Distribution</h3>
            <ResponsiveContainer width="100%" height={250}>
              <PieChart>
                <Pie
                  data={analytics.search_distribution}
                  dataKey="count"
                  nameKey="search_type"
                  cx="50%"
                  cy="50%"
                  outerRadius={80}
                  label
                >
                  {analytics.search_distribution.map((_: any, i: number) => (
                    <Cell key={i} fill={COLORS[i % COLORS.length]} />
                  ))}
                </Pie>
                <Tooltip contentStyle={{ backgroundColor: '#1F2937', border: '1px solid #374151' }} />
                <Legend />
              </PieChart>
            </ResponsiveContainer>
          </div>
        </div>
      )}

      {activeTab === 'users' && (
        <div className="bg-gray-900 rounded-xl border border-gray-800 overflow-hidden">
          <table className="w-full">
            <thead>
              <tr className="border-b border-gray-800 bg-gray-800/50">
                <th className="text-left px-4 py-3 text-xs font-medium text-gray-500 uppercase">Name</th>
                <th className="text-left px-4 py-3 text-xs font-medium text-gray-500 uppercase">Email</th>
                <th className="text-left px-4 py-3 text-xs font-medium text-gray-500 uppercase">Docs</th>
                <th className="text-left px-4 py-3 text-xs font-medium text-gray-500 uppercase">Queries</th>
                <th className="text-left px-4 py-3 text-xs font-medium text-gray-500 uppercase">Joined</th>
                <th className="text-left px-4 py-3 text-xs font-medium text-gray-500 uppercase">Actions</th>
              </tr>
            </thead>
            <tbody>
              {users.map(u => (
                <tr key={u.id} className="border-b border-gray-800 last:border-0">
                  <td className="px-4 py-3">
                    <div className="flex items-center gap-2">
                      {u.name}
                      {u.is_admin && (
                        <span className="text-xs bg-yellow-500/10 text-yellow-400 px-2 py-0.5 rounded">Admin</span>
                      )}
                    </div>
                  </td>
                  <td className="px-4 py-3 text-gray-400">{u.email}</td>
                  <td className="px-4 py-3">{u.doc_count}</td>
                  <td className="px-4 py-3">{u.query_count}</td>
                  <td className="px-4 py-3 text-gray-400 text-sm">{new Date(u.created_at).toLocaleDateString()}</td>
                  <td className="px-4 py-3">
                    <button onClick={() => deleteUser(u.id)} className="text-red-400 hover:text-red-300">
                      <Trash2 size={16} />
                    </button>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}

      {activeTab === 'queries' && (
        <div className="space-y-3">
          {queries.map(q => (
            <div key={q.id} className="bg-gray-900 rounded-lg p-4 border border-gray-800">
              <div className="flex items-start justify-between mb-2">
                <p className="font-medium">{q.question}</p>
                <span className="text-xs text-gray-500">{new Date(q.created_at).toLocaleString()}</span>
              </div>
              <p className="text-sm text-gray-400 mb-2 line-clamp-2">{q.answer}</p>
              <div className="flex gap-3 text-xs text-gray-500">
                <span>By: {q.user_name || 'Anonymous'}</span>
                <span>Confidence: {Math.round(q.confidence_score * 100)}%</span>
                <span>Latency: {q.latency_ms}ms</span>
                <span>Method: {q.search_type}</span>
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}

function StatCard({ icon, label, value, sub }: any) {
  return (
    <div className="bg-gray-900 rounded-xl p-5 border border-gray-800">
      <div className="flex items-center gap-3 mb-2">
        {icon}
        <span className="text-sm text-gray-400">{label}</span>
      </div>
      <p className="text-2xl font-bold">{value}</p>
      {sub && <p className="text-xs text-green-400 mt-1">{sub}</p>}
    </div>
  );
}