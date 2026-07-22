import React, { useState } from 'react';
import axios from 'axios';
import toast from 'react-hot-toast';
import { Send, CheckCircle, AlertCircle, Sparkles, Zap, Clock } from 'lucide-react';

const API = process.env.REACT_APP_API_URL;

interface Source {
  content: string;
  document_id: string;
  score: number;
}

interface Message {
  question: string;
  answer: string;
  confidence: number;
  sources: Source[];
  rewritten_question: string | null;
  latency_ms: number;
  chunks_found: number;
}

export default function ChatPage() {
  const [question, setQuestion] = useState('');
  const [searchType, setSearchType] = useState('hybrid');
  const [useRewriting, setUseRewriting] = useState(true);
  const [loading, setLoading] = useState(false);
  const [messages, setMessages] = useState<Message[]>([]);

  const ask = async () => {
    if (!question.trim()) return;

    setLoading(true);
    const currentQuestion = question;
    setQuestion('');

    try {
      const res = await axios.post(`${API}/queries/ask`, {
        question: currentQuestion,
        search_type: searchType,
        use_query_rewriting: useRewriting,
        top_k: 5,
      });

      setMessages(prev => [res.data, ...prev]);
} catch (err: any) {
  const errorMsg = err.response?.data?.detail || err.message || '';
  
  if (errorMsg.includes('quota') || errorMsg.includes('rate') || errorMsg.includes('429')) {
    toast.error('Rate limit reached. Please wait 60 seconds and try again.', { duration: 5000 });
  } else if (errorMsg.includes('Network') || err.code === 'ERR_NETWORK') {
    toast.error('Cannot connect to backend. Check if server is running.');
  } else {
    toast.error(errorMsg || 'Something went wrong. Please try again.');
  }
  setQuestion(currentQuestion);
} finally {
      setLoading(false);
    }
  };

  return (
    <div className="max-w-4xl mx-auto p-8">
      <div className="mb-8">
        <h2 className="text-3xl font-bold mb-2">Ask Questions</h2>
        <p className="text-gray-400">Query your documents with AI-powered retrieval</p>
      </div>

      <div className="bg-gray-900 rounded-xl p-6 border border-gray-800 mb-6">
        <div className="flex gap-4 mb-4">
          <div className="flex-1">
            <label className="block text-sm font-medium text-gray-400 mb-2">
              Search Method
            </label>
            <select
              value={searchType}
              onChange={e => setSearchType(e.target.value)}
              className="w-full bg-gray-800 border border-gray-700 rounded-lg px-4 py-2 text-white focus:outline-none focus:border-blue-500"
            >
              <option value="vector">Vector (Semantic Similarity)</option>
              <option value="bm25">BM25 (Keyword Match)</option>
              <option value="hybrid">Hybrid (Best Quality)</option>
            </select>
          </div>
          <div className="flex items-end">
            <label className="flex items-center gap-2 cursor-pointer bg-gray-800 px-4 py-2 rounded-lg border border-gray-700 hover:border-blue-500 transition">
              <input
                type="checkbox"
                checked={useRewriting}
                onChange={e => setUseRewriting(e.target.checked)}
                className="w-4 h-4 accent-blue-500"
              />
              <Sparkles size={14} className="text-purple-400" />
              <span className="text-sm text-gray-300">Query Rewriting</span>
            </label>
          </div>
        </div>

        <div className="flex gap-3">
          <input
            value={question}
            onChange={e => setQuestion(e.target.value)}
            onKeyDown={e => e.key === 'Enter' && !loading && ask()}
            placeholder="Ask anything about your documents..."
            className="flex-1 bg-gray-800 border border-gray-700 rounded-lg px-4 py-3 text-white placeholder-gray-500 focus:outline-none focus:border-blue-500"
            disabled={loading}
          />
          <button
            onClick={ask}
            disabled={loading || !question.trim()}
            className="bg-blue-600 hover:bg-blue-700 disabled:bg-gray-700 disabled:cursor-not-allowed px-6 py-3 rounded-lg flex items-center gap-2 transition font-medium"
          >
            {loading ? (
              <div className="w-4 h-4 border-2 border-white border-t-transparent rounded-full animate-spin" />
            ) : (
              <>
                <Send size={16} />
                Ask
              </>
            )}
          </button>
        </div>
      </div>

      <div className="space-y-6">
        {messages.map((msg, i) => (
          <div key={i} className="bg-gray-900 rounded-xl p-6 border border-gray-800">
            <div className="mb-4">
              <p className="text-xs font-medium text-gray-500 uppercase mb-1">Question</p>
              <p className="text-white font-medium">{msg.question}</p>
              {msg.rewritten_question && msg.rewritten_question !== msg.question && (
                <div className="mt-2 flex items-start gap-2 text-sm">
                  <Sparkles size={14} className="text-purple-400 mt-0.5 flex-shrink-0" />
                  <p className="text-purple-300">
                    <span className="text-gray-500">Rewritten as: </span>
                    {msg.rewritten_question}
                  </p>
                </div>
              )}
            </div>

            <div className="flex items-center gap-3 mb-4 flex-wrap">
              <div className={`flex items-center gap-1 text-xs px-2 py-1 rounded-full ${
                msg.confidence > 0.7 ? 'bg-green-500/10 text-green-400' : 
                msg.confidence > 0.4 ? 'bg-yellow-500/10 text-yellow-400' : 
                'bg-red-500/10 text-red-400'
              }`}>
                {msg.confidence > 0.7 ? <CheckCircle size={12} /> : <AlertCircle size={12} />}
                {Math.round(msg.confidence * 100)}% confidence
              </div>
              <div className="flex items-center gap-1 text-xs text-gray-500">
                <Clock size={12} />
                {msg.latency_ms}ms
              </div>
              <div className="flex items-center gap-1 text-xs text-gray-500">
                <Zap size={12} />
                {msg.chunks_found} chunks found
              </div>
            </div>

            <div className="bg-gray-800 rounded-lg p-4 mb-4">
              <p className="text-gray-200 whitespace-pre-wrap leading-relaxed">{msg.answer}</p>
            </div>

            {msg.sources && msg.sources.length > 0 && (
              <div>
                <p className="text-xs font-medium text-gray-500 uppercase mb-2">
                  Sources Used
                </p>
                <div className="space-y-2">
                  {msg.sources.map((s, j) => (
                    <div key={j} className="bg-gray-800/50 rounded p-3 text-sm border border-gray-800">
                      <div className="flex items-start gap-2">
                        <span className="text-blue-400 font-medium flex-shrink-0">
                          [{j + 1}]
                        </span>
                        <div className="flex-1">
                          <p className="text-gray-300">{s.content}</p>
                          <p className="text-xs text-gray-600 mt-1">
                            Relevance: {(s.score * 100).toFixed(1)}%
                          </p>
                        </div>
                      </div>
                    </div>
                  ))}
                </div>
              </div>
            )}
          </div>
        ))}

        {messages.length === 0 && !loading && (
          <div className="text-center py-12 text-gray-500">
            <MessageIconEmpty />
            <p>Start by asking a question about your uploaded documents</p>
          </div>
        )}
      </div>
    </div>
  );
}

function MessageIconEmpty() {
  return (
    <svg className="mx-auto mb-3 opacity-30" width="48" height="48" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
      <path d="M21 15a2 2 0 0 1-2 2H7l-4 4V5a2 2 0 0 1 2-2h14a2 2 0 0 1 2 2z" />
    </svg>
  );
}