import React, { useState, useEffect } from 'react';
import axios from 'axios';
import {
  LineChart, Line, PieChart, Pie, Cell,
  XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer, Legend
} from 'recharts';
import { 
  Users, FileText, MessageSquare, Zap, TrendingUp, Clock, Award, 
  Trash2, Search, Download, Eye, X, Shield, DollarSign, Activity
} from 'lucide-react';
import toast from 'react-hot-toast';

const API = process.env.REACT_APP_API_URL;

const COLORS = ['#3B82F6', '#10B981', '#F59E0B', '#8B5CF6', '#EF4444'];

const defaultStats = {
  total_users: 0, total_documents: 0, total_queries: 0,
  total_evaluations: 0, new_users_week: 0, queries_today: 0,
  avg_latency_ms: 0, avg_confidence: 0, active_today: 0,
  high_confidence_queries: 0, estimated_tokens_used: 0, estimated_cost_usd: 0
};

const defaultAnalytics = {
  users_growth: [],
  queries_growth: [],
  search_distribution: [],
  chunking_distribution: [],
  top_users: []
};

export default function AdminDashboard() {
  const [stats, setStats] = useState<any>(defaultStats);
  const [users, setUsers] = useState<any[]>([]);
  const [queries, setQueries] = useState<any[]>([]);
  const [analytics, setAnalytics] = useState<any>(defaultAnalytics);
  const [loaded, setLoaded] = useState(false);
const [activeTab, setActiveTab] = useState('overview');
const [feedbackList, setFeedbackList] = useState<any[]>([]);
const [feedbackStats, setFeedbackStats] = useState<any>(null);
  const [searchTerm, setSearchTerm] = useState('');
  const [selectedUser, setSelectedUser] = useState<any>(null);
  const [userDetails, setUserDetails] = useState<any>(null);

  useEffect(() => {
    fetchAll();
    const interval = setInterval(fetchAll, 30000);
    return () => clearInterval(interval);
  }, []);

const fetchAll = async () => {
    try {
      const results = await Promise.allSettled([
        axios.get(`${API}/admin/stats`),
        axios.get(`${API}/admin/users`),
        axios.get(`${API}/admin/queries/recent`),
        axios.get(`${API}/admin/analytics/growth`),
        axios.get(`${API}/feedback/all`),
        axios.get(`${API}/feedback/stats`),
      ]);
      
      if (results[0].status === 'fulfilled') {
        setStats({ ...defaultStats, ...results[0].value.data });
      }
      if (results[1].status === 'fulfilled') {
        setUsers(results[1].value.data?.users || []);
      }
      if (results[2].status === 'fulfilled') {
        setQueries(results[2].value.data?.queries || []);
      }
if (results[3].status === 'fulfilled') {
        setAnalytics({ ...defaultAnalytics, ...results[3].value.data });
      }
      if (results[4] && results[4].status === 'fulfilled') {
        setFeedbackList(results[4].value.data?.feedback || []);
      }
      if (results[5] && results[5].status === 'fulfilled') {
        setFeedbackStats(results[5].value.data || {});
      }
      
      setLoaded(true);
    } catch (err: any) {
      console.error('Admin fetch error:', err);
      setLoaded(true);
    }
  };

  const openUserDetails = async (user: any) => {
    setSelectedUser(user);
    try {
      const res = await axios.get(`${API}/admin/users/${user.id}/details`);
      setUserDetails(res.data);
    } catch (err) {
      toast.error('Failed to load user details');
    }
  };

  const closeUserDetails = () => {
    setSelectedUser(null);
    setUserDetails(null);
  };

  const deleteUser = async (userId: string, event: React.MouseEvent) => {
    event.stopPropagation();
    if (!window.confirm('Delete this user?')) return;
    try {
      await axios.delete(`${API}/admin/users/${userId}`);
      toast.success('User deleted');
      fetchAll();
    } catch (err: any) {
      toast.error(err.response?.data?.detail || 'Failed');
    }
  };

  const toggleAdmin = async (userId: string, event: React.MouseEvent) => {
    event.stopPropagation();
    try {
      await axios.post(`${API}/admin/users/${userId}/toggle-admin`);
      toast.success('Admin status updated');
      fetchAll();
    } catch (err: any) {
      toast.error(err.response?.data?.detail || 'Failed');
    }
  };

  const downloadCSV = async (type: 'users' | 'queries') => {
    try {
      const res = await axios.get(`${API}/admin/export/${type}`, { responseType: 'blob' });
      const url = window.URL.createObjectURL(new Blob([res.data]));
      const link = document.createElement('a');
      link.href = url;
      link.setAttribute('download', `${type}_${new Date().toISOString().split('T')[0]}.csv`);
      document.body.appendChild(link);
      link.click();
      link.remove();
      toast.success(`${type} exported`);
    } catch (err) {
      toast.error('Export failed');
    }
  };

  const filteredUsers = users.filter(u =>
    (u.name || '').toLowerCase().includes(searchTerm.toLowerCase()) ||
    (u.email || '').toLowerCase().includes(searchTerm.toLowerCase())
  );

  const pct = (n: number) => Math.round((Number(n) || 0) * 100);
  const num = (n: any) => Number(n) || 0;

  if (!loaded) {
    return (
      <div className="max-w-6xl mx-auto p-8 text-center text-gray-400">
        <div className="w-8 h-8 border-2 border-blue-500 border-t-transparent rounded-full animate-spin mx-auto mb-3" />
        Loading admin dashboard...
      </div>
    );
  }

  return (
    <div className="max-w-6xl mx-auto p-8">
      <div className="mb-8 flex items-center justify-between flex-wrap gap-4">
        <div>
          <div className="flex items-center gap-2 mb-2">
            <Award className="text-yellow-400" />
            <h2 className="text-3xl font-bold">Admin Dashboard</h2>
          </div>
          <p className="text-gray-400">Real-time platform analytics and user management</p>
        </div>
        <div className="flex gap-2">
          <button
            onClick={() => downloadCSV('users')}
            className="flex items-center gap-2 bg-gray-800 hover:bg-gray-700 px-4 py-2 rounded-lg transition text-sm"
          >
            <Download size={14} /> Export Users
          </button>
          <button
            onClick={() => downloadCSV('queries')}
            className="flex items-center gap-2 bg-gray-800 hover:bg-gray-700 px-4 py-2 rounded-lg transition text-sm"
          >
            <Download size={14} /> Export Queries
          </button>
        </div>
      </div>

      <div className="grid grid-cols-4 gap-4 mb-4">
        <StatCard icon={<Users className="text-blue-400" />} label="Total Users" value={num(stats.total_users)} sub={`+${num(stats.new_users_week)} this week`} />
        <StatCard icon={<Activity className="text-green-400" />} label="Active Today" value={num(stats.active_today)} />
        <StatCard icon={<FileText className="text-purple-400" />} label="Documents" value={num(stats.total_documents)} />
        <StatCard icon={<MessageSquare className="text-yellow-400" />} label="Total Queries" value={num(stats.total_queries)} sub={`${num(stats.queries_today)} today`} />
      </div>

      <div className="grid grid-cols-4 gap-4 mb-8">
        <StatCard icon={<Clock className="text-blue-400" />} label="Avg Latency" value={`${num(stats.avg_latency_ms)}ms`} />
        <StatCard icon={<Zap className="text-green-400" />} label="Avg Confidence" value={`${pct(stats.avg_confidence)}%`} />
        <StatCard icon={<TrendingUp className="text-purple-400" />} label="High Confidence" value={num(stats.high_confidence_queries)} sub={num(stats.total_queries) > 0 ? `${Math.round(num(stats.high_confidence_queries) / num(stats.total_queries) * 100)}% of queries` : '0%'} />
        <StatCard icon={<DollarSign className="text-yellow-400" />} label="Est. Cost" value={`$${num(stats.estimated_cost_usd).toFixed(4)}`} sub={`${(num(stats.estimated_tokens_used) / 1000).toFixed(0)}K tokens`} />
      </div>

      <div className="flex gap-2 mb-4 border-b border-gray-800">
{['overview', 'users', 'queries', 'feedback'].map(tab => (
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

      {activeTab === 'overview' && (
        <div className="grid grid-cols-2 gap-6">
          <div className="bg-gray-900 rounded-xl p-6 border border-gray-800">
            <h3 className="font-semibold mb-4">User Growth (30 days)</h3>
            {analytics.users_growth.length > 0 ? (
              <ResponsiveContainer width="100%" height={220}>
                <LineChart data={analytics.users_growth}>
                  <CartesianGrid strokeDasharray="3 3" stroke="#374151" />
                  <XAxis dataKey="date" stroke="#9CA3AF" style={{ fontSize: '10px' }} />
                  <YAxis stroke="#9CA3AF" />
                  <Tooltip contentStyle={{ backgroundColor: '#1F2937', border: '1px solid #374151' }} />
                  <Line type="monotone" dataKey="count" stroke="#3B82F6" strokeWidth={2} />
                </LineChart>
              </ResponsiveContainer>
            ) : (
              <p className="text-gray-500 text-center py-8 text-sm">Not enough data yet</p>
            )}
          </div>

          <div className="bg-gray-900 rounded-xl p-6 border border-gray-800">
            <h3 className="font-semibold mb-4">Query Growth (30 days)</h3>
            {analytics.queries_growth.length > 0 ? (
              <ResponsiveContainer width="100%" height={220}>
                <LineChart data={analytics.queries_growth}>
                  <CartesianGrid strokeDasharray="3 3" stroke="#374151" />
                  <XAxis dataKey="date" stroke="#9CA3AF" style={{ fontSize: '10px' }} />
                  <YAxis stroke="#9CA3AF" />
                  <Tooltip contentStyle={{ backgroundColor: '#1F2937', border: '1px solid #374151' }} />
                  <Line type="monotone" dataKey="count" stroke="#10B981" strokeWidth={2} />
                </LineChart>
              </ResponsiveContainer>
            ) : (
              <p className="text-gray-500 text-center py-8 text-sm">Not enough data yet</p>
            )}
          </div>

          <div className="bg-gray-900 rounded-xl p-6 border border-gray-800">
            <h3 className="font-semibold mb-4">Search Methods Used</h3>
            {analytics.search_distribution.length > 0 ? (
              <ResponsiveContainer width="100%" height={220}>
                <PieChart>
                  <Pie
                    data={analytics.search_distribution}
                    dataKey="count"
                    nameKey="search_type"
                    cx="50%"
                    cy="50%"
                    outerRadius={70}
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
            ) : (
              <p className="text-gray-500 text-center py-8 text-sm">No queries yet</p>
            )}
          </div>

          <div className="bg-gray-900 rounded-xl p-6 border border-gray-800">
            <h3 className="font-semibold mb-4">Top Users by Queries</h3>
            <div className="space-y-3">
              {analytics.top_users.length > 0 ? (
                analytics.top_users.map((u: any, i: number) => (
                  <div key={i} className="flex items-center justify-between p-3 bg-gray-800/50 rounded-lg">
                    <div className="flex items-center gap-3">
                      <div className="w-8 h-8 bg-gradient-to-br from-blue-500 to-purple-600 rounded-full flex items-center justify-center text-sm font-bold">
                        {i + 1}
                      </div>
                      <div>
                        <p className="font-medium text-sm">{u.name || 'Unknown'}</p>
                        <p className="text-xs text-gray-500">{u.email}</p>
                      </div>
                    </div>
                    <span className="text-lg font-bold text-blue-400">{num(u.query_count)}</span>
                  </div>
                ))
              ) : (
                <p className="text-center text-gray-500 py-4 text-sm">No user activity yet</p>
              )}
            </div>
          </div>
        </div>
      )}

      {activeTab === 'users' && (
        <div>
          <div className="mb-4 relative">
            <Search className="absolute left-3 top-3 text-gray-500" size={16} />
            <input
              value={searchTerm}
              onChange={e => setSearchTerm(e.target.value)}
              placeholder="Search users by name or email..."
              className="w-full bg-gray-900 border border-gray-800 rounded-lg pl-10 pr-4 py-2 text-white placeholder-gray-500 focus:outline-none focus:border-blue-500"
            />
          </div>

          <div className="bg-gray-900 rounded-xl border border-gray-800 overflow-hidden">
            <table className="w-full">
              <thead>
                <tr className="border-b border-gray-800 bg-gray-800/50">
                  <th className="text-left px-4 py-3 text-xs font-medium text-gray-500 uppercase">User</th>
                  <th className="text-left px-4 py-3 text-xs font-medium text-gray-500 uppercase">Docs</th>
                  <th className="text-left px-4 py-3 text-xs font-medium text-gray-500 uppercase">Queries</th>
                  <th className="text-left px-4 py-3 text-xs font-medium text-gray-500 uppercase">Confidence</th>
                  <th className="text-left px-4 py-3 text-xs font-medium text-gray-500 uppercase">Last Active</th>
                  <th className="text-left px-4 py-3 text-xs font-medium text-gray-500 uppercase">Actions</th>
                </tr>
              </thead>
              <tbody>
                {filteredUsers.map(u => (
                  <tr 
                    key={u.id} 
                    className="border-b border-gray-800 last:border-0 hover:bg-gray-800/30 cursor-pointer"
                    onClick={() => openUserDetails(u)}
                  >
                    <td className="px-4 py-3">
                      <div className="flex items-center gap-3">
                        <div className="w-8 h-8 bg-gradient-to-br from-blue-500 to-purple-600 rounded-full flex items-center justify-center text-sm font-bold">
                          {(u.name || 'U').charAt(0).toUpperCase()}
                        </div>
                        <div>
                          <div className="flex items-center gap-2">
                            <span className="font-medium">{u.name || 'Unknown'}</span>
                            {u.is_admin && (
                              <span className="text-xs bg-yellow-500/10 text-yellow-400 px-2 py-0.5 rounded flex items-center gap-1">
                                <Shield size={10} /> Admin
                              </span>
                            )}
                          </div>
                          <p className="text-xs text-gray-500">{u.email}</p>
                        </div>
                      </div>
                    </td>
                    <td className="px-4 py-3">{num(u.doc_count)}</td>
                    <td className="px-4 py-3">{num(u.query_count)}</td>
                    <td className="px-4 py-3">
                      {u.avg_confidence ? `${pct(u.avg_confidence)}%` : '-'}
                    </td>
                    <td className="px-4 py-3 text-gray-400 text-sm">
                      {u.last_activity ? new Date(u.last_activity).toLocaleDateString() : 'Never'}
                    </td>
                    <td className="px-4 py-3">
                      <div className="flex gap-1">
                        <button
                          onClick={(e) => { e.stopPropagation(); openUserDetails(u); }}
                          className="p-2 text-blue-400 hover:bg-blue-500/10 rounded transition"
                          title="View details"
                        >
                          <Eye size={14} />
                        </button>
                        <button
                          onClick={(e) => toggleAdmin(u.id, e)}
                          className="p-2 text-yellow-400 hover:bg-yellow-500/10 rounded transition"
                          title="Toggle admin"
                        >
                          <Shield size={14} />
                        </button>
                        <button
                          onClick={(e) => deleteUser(u.id, e)}
                          className="p-2 text-red-400 hover:bg-red-500/10 rounded transition"
                          title="Delete user"
                        >
                          <Trash2 size={14} />
                        </button>
                      </div>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      )}

{activeTab === 'feedback' && (
        <div>
          {feedbackStats && feedbackStats.total_feedback > 0 && (
            <div className="grid grid-cols-4 gap-4 mb-6">
              <div className="bg-gray-900 rounded-xl p-5 border border-gray-800">
                <p className="text-sm text-gray-400 mb-1">Total Feedback</p>
                <p className="text-2xl font-bold">{feedbackStats.total_feedback}</p>
              </div>
              <div className="bg-gray-900 rounded-xl p-5 border border-gray-800">
                <p className="text-sm text-gray-400 mb-1">Average Rating</p>
                <p className="text-2xl font-bold text-yellow-400">
                  ⭐ {parseFloat(feedbackStats.avg_rating).toFixed(1)}
                </p>
              </div>
              <div className="bg-gray-900 rounded-xl p-5 border border-gray-800">
                <p className="text-sm text-gray-400 mb-1">5-Star Reviews</p>
                <p className="text-2xl font-bold text-green-400">{feedbackStats.five_star}</p>
              </div>
              <div className="bg-gray-900 rounded-xl p-5 border border-gray-800">
                <p className="text-sm text-gray-400 mb-1">Needs Attention</p>
                <p className="text-2xl font-bold text-red-400">
                  {feedbackStats.one_star + feedbackStats.two_star}
                </p>
              </div>
            </div>
          )}

          <div className="space-y-3">
            {feedbackList.length === 0 ? (
              <p className="text-center text-gray-500 py-8">No feedback yet</p>
            ) : (
              feedbackList.map((f: any) => (
                <div key={f.id} className="bg-gray-900 rounded-lg p-4 border border-gray-800">
                  <div className="flex items-start justify-between mb-2">
                    <div className="flex items-center gap-3">
                      <div className="w-10 h-10 bg-gradient-to-br from-blue-500 to-purple-600 rounded-full flex items-center justify-center text-sm font-bold">
                        {(f.user_name || 'U').charAt(0).toUpperCase()}
                      </div>
                      <div>
                        <p className="font-medium">{f.user_name || 'Anonymous'}</p>
                        <p className="text-xs text-gray-500">{f.user_email}</p>
                      </div>
                    </div>
                    <div className="flex items-center gap-2">
                      <div className="text-yellow-400">
                        {'⭐'.repeat(f.rating)}
                      </div>
                      <span className="text-xs px-2 py-1 rounded-full bg-blue-500/10 text-blue-400">
                        {f.category}
                      </span>
                      <span className="text-xs text-gray-500">
                        {new Date(f.created_at).toLocaleDateString()}
                      </span>
                    </div>
                  </div>
                  {f.comment && (
                    <p className="text-sm text-gray-300 mt-2 pl-13">{f.comment}</p>
                  )}
                </div>
              ))
            )}
          </div>
        </div>
      )}
        <div className="space-y-3">
          {queries.length === 0 ? (
            <p className="text-center text-gray-500 py-8">No queries yet</p>
          ) : (
            queries.map(q => (
              <div key={q.id} className="bg-gray-900 rounded-lg p-4 border border-gray-800">
                <div className="flex items-start justify-between mb-2">
                  <p className="font-medium">{q.question}</p>
                  <span className="text-xs text-gray-500 flex-shrink-0 ml-3">
                    {new Date(q.created_at).toLocaleString()}
                  </span>
                </div>
                <p className="text-sm text-gray-400 mb-3 line-clamp-2">{q.answer}</p>
                <div className="flex gap-3 text-xs text-gray-500 flex-wrap">
                  <span>👤 {q.user_name || 'Anonymous'}</span>
                  <span>🎯 {pct(q.confidence_score)}%</span>
                  <span>⏱️ {num(q.latency_ms)}ms</span>
                  <span>🔍 {q.search_type}</span>
                </div>
              </div>
            ))
          )}
        </div>
      )}

      {selectedUser && userDetails && (
        <div className="fixed inset-0 bg-black/70 z-50 flex items-center justify-center p-4" onClick={closeUserDetails}>
          <div 
            className="bg-gray-900 border border-gray-800 rounded-xl max-w-3xl w-full max-h-[85vh] overflow-y-auto"
            onClick={e => e.stopPropagation()}
          >
            <div className="p-6 border-b border-gray-800 flex items-center justify-between sticky top-0 bg-gray-900">
              <div className="flex items-center gap-3">
                <div className="w-12 h-12 bg-gradient-to-br from-blue-500 to-purple-600 rounded-full flex items-center justify-center text-lg font-bold">
                  {(selectedUser.name || 'U').charAt(0).toUpperCase()}
                </div>
                <div>
                  <h3 className="text-xl font-bold">{selectedUser.name || 'Unknown'}</h3>
                  <p className="text-sm text-gray-400">{selectedUser.email}</p>
                </div>
              </div>
              <button onClick={closeUserDetails} className="p-2 hover:bg-gray-800 rounded-lg">
                <X size={20} />
              </button>
            </div>

            <div className="p-6">
              <div className="grid grid-cols-4 gap-3 mb-6">
                <div className="bg-gray-800/50 rounded-lg p-3">
                  <p className="text-xs text-gray-500 mb-1">Documents</p>
                  <p className="text-xl font-bold">{userDetails.documents?.length || 0}</p>
                </div>
                <div className="bg-gray-800/50 rounded-lg p-3">
                  <p className="text-xs text-gray-500 mb-1">Queries</p>
                  <p className="text-xl font-bold">{num(userDetails.stats?.total_queries)}</p>
                </div>
                <div className="bg-gray-800/50 rounded-lg p-3">
                  <p className="text-xs text-gray-500 mb-1">Avg Confidence</p>
                  <p className="text-xl font-bold">
                    {userDetails.stats?.avg_confidence ? `${pct(userDetails.stats.avg_confidence)}%` : '-'}
                  </p>
                </div>
                <div className="bg-gray-800/50 rounded-lg p-3">
                  <p className="text-xs text-gray-500 mb-1">Avg Latency</p>
                  <p className="text-xl font-bold">
                    {userDetails.stats?.avg_latency ? `${Math.round(userDetails.stats.avg_latency)}ms` : '-'}
                  </p>
                </div>
              </div>

              <div className="mb-6">
                <h4 className="font-semibold mb-2 text-sm text-gray-400 uppercase">Documents ({userDetails.documents?.length || 0})</h4>
                <div className="space-y-2 max-h-40 overflow-y-auto">
                  {(userDetails.documents || []).map((d: any) => (
                    <div key={d.id} className="bg-gray-800/50 rounded p-3 text-sm">
                      <div className="flex justify-between">
                        <span className="font-medium">{d.filename}</span>
                        <span className="text-gray-500 text-xs">{d.total_chunks} chunks</span>
                      </div>
                      <p className="text-xs text-gray-500 mt-1">
                        {d.chunking_strategy} • {new Date(d.upload_time).toLocaleDateString()}
                      </p>
                    </div>
                  ))}
                  {(!userDetails.documents || userDetails.documents.length === 0) && (
                    <p className="text-gray-500 text-sm">No documents uploaded</p>
                  )}
                </div>
              </div>

              <div>
                <h4 className="font-semibold mb-2 text-sm text-gray-400 uppercase">Recent Queries ({userDetails.queries?.length || 0})</h4>
                <div className="space-y-2 max-h-60 overflow-y-auto">
                  {(userDetails.queries || []).map((q: any) => (
                    <div key={q.id} className="bg-gray-800/50 rounded p-3 text-sm">
                      <p className="font-medium mb-1">{q.question}</p>
                      <p className="text-xs text-gray-400 line-clamp-2 mb-1">{q.answer}</p>
                      <div className="flex gap-3 text-xs text-gray-500">
                        <span>🎯 {pct(q.confidence_score)}%</span>
                        <span>⏱️ {num(q.latency_ms)}ms</span>
                        <span>🔍 {q.search_type}</span>
                      </div>
                    </div>
                  ))}
                  {(!userDetails.queries || userDetails.queries.length === 0) && (
                    <p className="text-gray-500 text-sm">No queries yet</p>
                  )}
                </div>
              </div>
            </div>
          </div>
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