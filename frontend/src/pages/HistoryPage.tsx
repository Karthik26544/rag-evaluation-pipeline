import React, { useState, useEffect } from 'react';
import axios from 'axios';
import { History, Search, Trash2, Clock, Zap, Database } from 'lucide-react';
import toast from 'react-hot-toast';

const API = process.env.REACT_APP_API_URL;

interface Query {
  id: string;
  question: string;
  answer: string;
  confidence_score: number;
  latency_ms: number;
  search_type: string;
  sources: any[];
  created_at: string;
}

export default function HistoryPage() {
  const [queries, setQueries] = useState<Query[]>([]);
  const [loading, setLoading] = useState(true);
  const [searchTerm, setSearchTerm] = useState('');
  const [expandedId, setExpandedId] = useState<string | null>(null);

  useEffect(() => {
    fetchHistory();
  }, []);

  const fetchHistory = async () => {
    try {
      const res = await axios.get(`${API}/queries/my-history`);
      setQueries(res.data.queries);
    } catch (err) {
      toast.error('Failed to load history');
    } finally {
      setLoading(false);
    }
  };

  const deleteQuery = async (id: string, event: React.MouseEvent) => {
    event.stopPropagation();
    if (!window.confirm('Delete this query?')) return;
    try {
      await axios.delete(`${API}/queries/my-history/${id}`);
      setQueries(prev => prev.filter(q => q.id !== id));
      toast.success('Deleted');
    } catch (err) {
      toast.error('Failed to delete');
    }
  };

  const filtered = queries.filter(q =>
    q.question.toLowerCase().includes(searchTerm.toLowerCase()) ||
    q.answer.toLowerCase().includes(searchTerm.toLowerCase())
  );

  if (loading) {
    return (
      <div className="max-w-4xl mx-auto p-8 text-center text-gray-400">
        <div className="w-8 h-8 border-2 border-blue-500 border-t-transparent rounded-full animate-spin mx-auto mb-3" />
        Loading history...
      </div>
    );
  }

  return (
    <div className="max-w-4xl mx-auto p-8">
      <div className="mb-8">
        <div className="flex items-center gap-2 mb-2">
          <History className="text-blue-400" />
          <h2 className="text-3xl font-bold">My History</h2>
        </div>
        <p className="text-gray-400">All your past questions and answers ({queries.length})</p>
      </div>

      <div className="mb-6 relative">
        <Search className="absolute left-3 top-3 text-gray-500" size={16} />
        <input
          value={searchTerm}
          onChange={e => setSearchTerm(e.target.value)}
          placeholder="Search your questions and answers..."
          className="w-full bg-gray-900 border border-gray-800 rounded-lg pl-10 pr-4 py-2 text-white placeholder-gray-500 focus:outline-none focus:border-blue-500"
        />
      </div>

      <div className="space-y-3">
        {filtered.length === 0 ? (
          <div className="bg-gray-900 rounded-xl p-8 border border-gray-800 text-center">
            <History className="mx-auto mb-3 text-gray-600" size={48} />
            <p className="text-gray-500">
              {searchTerm ? 'No matching queries found' : 'No questions asked yet. Head to the Ask page!'}
            </p>
          </div>
        ) : (
          filtered.map(q => (
            <div
              key={q.id}
              className="bg-gray-900 rounded-lg border border-gray-800 hover:border-gray-700 transition cursor-pointer"
              onClick={() => setExpandedId(expandedId === q.id ? null : q.id)}
            >
              <div className="p-4">
                <div className="flex items-start justify-between mb-2 gap-3">
                  <p className="font-medium flex-1">{q.question}</p>
                  <div className="flex items-center gap-2 flex-shrink-0">
                    <span className="text-xs text-gray-500">
                      {new Date(q.created_at).toLocaleDateString()}
                    </span>
                    <button
                      onClick={(e) => deleteQuery(q.id, e)}
                      className="p-1 text-gray-500 hover:text-red-400 transition"
                    >
                      <Trash2 size={14} />
                    </button>
                  </div>
                </div>

                <p className={`text-sm text-gray-400 ${expandedId === q.id ? '' : 'line-clamp-2'}`}>
                  {q.answer}
                </p>

                <div className="flex gap-3 mt-3 text-xs text-gray-500 flex-wrap">
                  <span className="flex items-center gap-1">
                    <Zap size={11} /> {Math.round((q.confidence_score || 0) * 100)}%
                  </span>
                  <span className="flex items-center gap-1">
                    <Clock size={11} /> {q.latency_ms}ms
                  </span>
                  <span className="flex items-center gap-1">
                    <Database size={11} /> {q.search_type}
                  </span>
                  {q.latency_ms < 200 && (
                    <span className="bg-green-500/10 text-green-400 px-2 py-0.5 rounded">
                      💾 Cached
                    </span>
                  )}
                </div>

                {expandedId === q.id && q.sources && q.sources.length > 0 && (
                  <div className="mt-4 pt-4 border-t border-gray-800">
                    <p className="text-xs text-gray-500 uppercase mb-2">Sources</p>
                    <div className="space-y-2">
                      {q.sources.map((s: any, i: number) => (
                        <div key={i} className="bg-gray-800/50 p-2 rounded text-xs text-gray-300">
                          <span className="text-blue-400">[{i + 1}]</span> {s.content}
                        </div>
                      ))}
                    </div>
                  </div>
                )}
              </div>
            </div>
          ))
        )}
      </div>
    </div>
  );
}