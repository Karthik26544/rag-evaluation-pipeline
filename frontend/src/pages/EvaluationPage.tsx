import React, { useState } from 'react';
import axios from 'axios';
import toast from 'react-hot-toast';
import { Play, Plus, Trash2, Award } from 'lucide-react';

const API = process.env.REACT_APP_API_URL;

interface EvalQuestion {
  question: string;
  ground_truth: string;
}

interface EvalResult {
  chunking_strategy: string;
  search_type: string;
  faithfulness: number;
  answer_relevancy: number;
  avg_latency_ms: number;
  questions_evaluated: number;
}

export default function EvaluationPage() {
  const [evalName, setEvalName] = useState('Evaluation Run 1');
  const [questions, setQuestions] = useState<EvalQuestion[]>([
    { question: '', ground_truth: '' }
  ]);
  const [running, setRunning] = useState(false);
  const [results, setResults] = useState<EvalResult[]>([]);
  const [bestCombo, setBestCombo] = useState('');

  const addQuestion = () => {
    setQuestions(prev => [...prev, { question: '', ground_truth: '' }]);
  };

  const removeQuestion = (i: number) => {
    setQuestions(prev => prev.filter((_, idx) => idx !== i));
  };

  const updateQuestion = (i: number, field: string, value: string) => {
    setQuestions(prev =>
      prev.map((q, idx) => idx === i ? { ...q, [field]: value } : q)
    );
  };

  const runEvaluation = async () => {
    const valid = questions.filter(q => q.question.trim() && q.ground_truth.trim());
    if (valid.length === 0) {
      return toast.error('Add at least one question with expected answer');
    }

    setRunning(true);
    const t = toast.loading('Running evaluation... this takes 2-5 minutes');

    try {
      const res = await axios.post(`${API}/evaluation/run`, {
        evaluation_name: evalName,
        questions: valid,
        chunking_strategies: ['recursive'],
        search_types: ['vector', 'hybrid'],
      }, { timeout: 600000 });

      toast.dismiss(t);
      toast.success('Evaluation complete!');
      setResults(res.data.results);
      setBestCombo(res.data.best_combination);
    } catch (err: any) {
      toast.dismiss(t);
      toast.error('Evaluation failed. Check backend logs.');
    } finally {
      setRunning(false);
    }
  };

  return (
    <div className="max-w-4xl mx-auto p-8">
      <div className="mb-8">
        <h2 className="text-3xl font-bold mb-2">Evaluation Pipeline</h2>
        <p className="text-gray-400">Compare strategies using LLM-as-judge metrics</p>
      </div>

      <div className="bg-gray-900 rounded-xl p-6 border border-gray-800 mb-6">
        <label className="block text-sm font-medium text-gray-400 mb-2">
          Evaluation Name
        </label>
        <input
          value={evalName}
          onChange={e => setEvalName(e.target.value)}
          className="w-full bg-gray-800 border border-gray-700 rounded-lg px-4 py-2 text-white focus:outline-none focus:border-blue-500"
        />
      </div>

      <div className="bg-gray-900 rounded-xl p-6 border border-gray-800 mb-6">
        <h3 className="font-semibold mb-1">Test Dataset</h3>
        <p className="text-sm text-gray-500 mb-4">
          Provide questions with expected ground truth answers
        </p>

        <div className="space-y-4">
          {questions.map((q, i) => (
            <div key={i} className="bg-gray-800/50 rounded-lg p-4 border border-gray-800">
              <div className="flex items-start gap-3">
                <span className="w-8 h-8 bg-blue-500/10 text-blue-400 rounded-full flex items-center justify-center text-sm font-medium flex-shrink-0">
                  {i + 1}
                </span>
                <div className="flex-1 space-y-2">
                  <input
                    value={q.question}
                    onChange={e => updateQuestion(i, 'question', e.target.value)}
                    placeholder="Question"
                    className="w-full bg-gray-800 border border-gray-700 rounded-lg px-3 py-2 text-white text-sm focus:outline-none focus:border-blue-500"
                  />
                  <input
                    value={q.ground_truth}
                    onChange={e => updateQuestion(i, 'ground_truth', e.target.value)}
                    placeholder="Expected answer (ground truth)"
                    className="w-full bg-gray-800 border border-gray-700 rounded-lg px-3 py-2 text-white text-sm focus:outline-none focus:border-blue-500"
                  />
                </div>
                <button
                  onClick={() => removeQuestion(i)}
                  className="p-2 text-gray-500 hover:text-red-400 transition"
                >
                  <Trash2 size={16} />
                </button>
              </div>
            </div>
          ))}
        </div>

        <button
          onClick={addQuestion}
          className="mt-4 flex items-center gap-2 text-blue-400 hover:text-blue-300 text-sm font-medium transition"
        >
          <Plus size={16} /> Add Question
        </button>
      </div>

      <button
        onClick={runEvaluation}
        disabled={running}
        className="w-full bg-gradient-to-r from-green-600 to-emerald-600 hover:from-green-700 hover:to-emerald-700 disabled:from-gray-700 disabled:to-gray-700 py-3 rounded-xl flex items-center justify-center gap-2 transition font-semibold"
      >
        {running ? (
          <>
            <div className="w-4 h-4 border-2 border-white border-t-transparent rounded-full animate-spin" />
            Running Evaluation...
          </>
        ) : (
          <>
            <Play size={18} />
            Run Evaluation
          </>
        )}
      </button>

      {results.length > 0 && (
        <div className="mt-8">
          {bestCombo && (
            <div className="mb-4 p-4 bg-gradient-to-r from-yellow-500/10 to-orange-500/10 border border-yellow-500/30 rounded-xl flex items-center gap-3">
              <Award className="text-yellow-400" />
              <div>
                <p className="text-sm text-gray-400">Best Performing Combination</p>
                <p className="text-lg font-semibold text-yellow-300 capitalize">{bestCombo}</p>
              </div>
            </div>
          )}

          <h3 className="text-lg font-semibold mb-4">Results</h3>
          <div className="bg-gray-900 rounded-xl border border-gray-800 overflow-hidden">
            <table className="w-full">
              <thead>
                <tr className="border-b border-gray-800 bg-gray-800/50">
                  <th className="text-left px-4 py-3 text-xs font-medium text-gray-500 uppercase">Strategy</th>
                  <th className="text-left px-4 py-3 text-xs font-medium text-gray-500 uppercase">Search</th>
                  <th className="text-left px-4 py-3 text-xs font-medium text-gray-500 uppercase">Faithfulness</th>
                  <th className="text-left px-4 py-3 text-xs font-medium text-gray-500 uppercase">Relevancy</th>
                  <th className="text-left px-4 py-3 text-xs font-medium text-gray-500 uppercase">Latency</th>
                </tr>
              </thead>
              <tbody>
                {results.map((r, i) => (
                  <tr key={i} className="border-b border-gray-800 last:border-0">
                    <td className="px-4 py-3 capitalize font-medium">{r.chunking_strategy}</td>
                    <td className="px-4 py-3 capitalize">{r.search_type}</td>
                    <td className="px-4 py-3">
                      <div className="flex items-center gap-2">
                        <div className="w-20 bg-gray-800 rounded-full h-2">
                          <div
                            className="bg-blue-500 h-2 rounded-full"
                            style={{ width: `${r.faithfulness * 100}%` }}
                          />
                        </div>
                        <span className="text-sm font-medium">{Math.round(r.faithfulness * 100)}%</span>
                      </div>
                    </td>
                    <td className="px-4 py-3">
                      <div className="flex items-center gap-2">
                        <div className="w-20 bg-gray-800 rounded-full h-2">
                          <div
                            className="bg-green-500 h-2 rounded-full"
                            style={{ width: `${r.answer_relevancy * 100}%` }}
                          />
                        </div>
                        <span className="text-sm font-medium">{Math.round(r.answer_relevancy * 100)}%</span>
                      </div>
                    </td>
                    <td className="px-4 py-3 text-sm text-gray-400">{r.avg_latency_ms}ms</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      )}
    </div>
  );
}