import React, { useState, useEffect } from 'react';
import axios from 'axios';
import {
  BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip, Legend, ResponsiveContainer
} from 'recharts';
import { FileText, MessageSquare, TrendingUp, Zap } from 'lucide-react';

const API = process.env.REACT_APP_API_URL;

interface DashboardData {
  comparison_data: any[];
  total_queries: number;
  total_documents: number;
}

export default function DashboardPage() {
  const [data, setData] = useState<DashboardData | null>(null);

  useEffect(() => {
    axios.get(`${API}/evaluation/dashboard`).then(res => setData(res.data));
  }, []);

  if (!data) {
    return (
      <div className="max-w-6xl mx-auto p-8 text-center text-gray-400">
        <div className="w-8 h-8 border-2 border-blue-500 border-t-transparent rounded-full animate-spin mx-auto mb-3" />
        Loading dashboard...
      </div>
    );
  }

  const chartData = data.comparison_data.map((d: any) => ({
    name: `${d.chunking_strategy}/${d.search_type}`,
    faithfulness: Math.round(d.avg_faithfulness * 100),
    relevancy: Math.round(d.avg_relevancy * 100),
  }));

  return (
    <div className="max-w-6xl mx-auto p-8">
      <div className="mb-8">
        <h2 className="text-3xl font-bold mb-2">Analytics Dashboard</h2>
        <p className="text-gray-400">System performance and evaluation metrics</p>
      </div>

      <div className="grid grid-cols-4 gap-4 mb-8">
        <StatCard
          icon={<FileText className="text-blue-400" />}
          label="Documents"
          value={data.total_documents}
          color="blue"
        />
        <StatCard
          icon={<MessageSquare className="text-green-400" />}
          label="Queries"
          value={data.total_queries}
          color="green"
        />
        <StatCard
          icon={<TrendingUp className="text-purple-400" />}
          label="Evaluations"
          value={data.comparison_data.length}
          color="purple"
        />
        <StatCard
          icon={<Zap className="text-yellow-400" />}
          label="Strategies"
          value={new Set(data.comparison_data.map((d: any) => d.chunking_strategy)).size}
          color="yellow"
        />
      </div>

      {chartData.length > 0 ? (
        <div className="bg-gray-900 rounded-xl p-6 border border-gray-800">
          <h3 className="font-semibold mb-6">Strategy Performance Comparison</h3>
          <ResponsiveContainer width="100%" height={350}>
            <BarChart data={chartData}>
              <CartesianGrid strokeDasharray="3 3" stroke="#374151" />
              <XAxis dataKey="name" stroke="#9CA3AF" style={{ fontSize: '12px' }} />
              <YAxis stroke="#9CA3AF" domain={[0, 100]} />
              <Tooltip
                contentStyle={{
                  backgroundColor: '#1F2937',
                  border: '1px solid #374151',
                  borderRadius: '8px',
                }}
              />
              <Legend />
              <Bar dataKey="faithfulness" fill="#3B82F6" name="Faithfulness %" radius={[4, 4, 0, 0]} />
              <Bar dataKey="relevancy" fill="#10B981" name="Relevancy %" radius={[4, 4, 0, 0]} />
            </BarChart>
          </ResponsiveContainer>
        </div>
      ) : (
        <div className="bg-gray-900 rounded-xl p-8 border border-gray-800 text-center text-gray-400">
          <TrendingUp className="mx-auto mb-3 opacity-30" size={48} />
          <p>Run evaluations to see comparison charts here</p>
        </div>
      )}
    </div>
  );
}

function StatCard({ icon, label, value, color }: any) {
  return (
    <div className="bg-gray-900 rounded-xl p-5 border border-gray-800">
      <div className="flex items-center gap-3 mb-2">
        <div className={`w-8 h-8 bg-${color}-500/10 rounded-lg flex items-center justify-center`}>
          {icon}
        </div>
        <span className="text-sm text-gray-400">{label}</span>
      </div>
      <p className="text-2xl font-bold">{value}</p>
    </div>
  );
}