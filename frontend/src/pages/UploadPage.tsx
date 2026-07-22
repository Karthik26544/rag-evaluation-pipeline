import React, { useState, useEffect } from 'react';
import axios from 'axios';
import toast from 'react-hot-toast';
import { Upload, FileText, Trash2, CheckCircle } from 'lucide-react';

const API = process.env.REACT_APP_API_URL;

interface Document {
  id: string;
  filename: string;
  file_type: string;
  total_chunks: number;
  chunking_strategy: string;
  status: string;
  upload_time: string;
}

export default function UploadPage() {
  const [file, setFile] = useState<File | null>(null);
  const [strategy, setStrategy] = useState('recursive');
  const [uploading, setUploading] = useState(false);
  const [documents, setDocuments] = useState<Document[]>([]);

  useEffect(() => {
    fetchDocuments();
  }, []);

  const fetchDocuments = async () => {
    try {
      const res = await axios.get(`${API}/documents/list`);
      setDocuments(res.data.documents);
    } catch (err) {
      console.error(err);
    }
  };

  const handleUpload = async () => {
    if (!file) return toast.error('Please select a file');

    setUploading(true);
    const form = new FormData();
    form.append('file', file);
    form.append('chunking_strategy', strategy);

    try {
      const res = await axios.post(`${API}/documents/upload`, form);
      toast.success(`Uploaded! ${res.data.total_chunks} chunks created`);
      setFile(null);
      fetchDocuments();
    } catch (err: any) {
      toast.error(err.response?.data?.detail || 'Upload failed');
    } finally {
      setUploading(false);
    }
  };

  const handleDelete = async (id: string) => {
    try {
      await axios.delete(`${API}/documents/${id}`);
      toast.success('Document deleted');
      fetchDocuments();
    } catch (err) {
      toast.error('Delete failed');
    }
  };

  return (
    <div className="max-w-4xl mx-auto p-8">
      <div className="mb-8">
        <h2 className="text-3xl font-bold mb-2">Upload Documents</h2>
<p className="text-gray-400">Add PDFs, DOCX, TXT, or Markdown files to your knowledge base</p>
</div>

<div className="bg-blue-500/10 border border-blue-500/30 rounded-lg p-4 mb-6 flex items-start gap-3">
  <span className="text-2xl">💡</span>
  <div className="text-sm">
    <p className="font-medium text-blue-300 mb-1">Tips for best results</p>
    <ul className="text-blue-200/70 space-y-1 list-disc list-inside">
      <li>Keep documents under 5MB for faster processing</li>
      <li>Recursive chunking works best for most documents</li>
      <li>Uploads use local embeddings, no API cost</li>
    </ul>
  </div>
</div>

      <div className="bg-gray-900 rounded-xl p-6 border border-gray-800 mb-8">
        <div className="mb-4">
          <label className="block text-sm font-medium text-gray-400 mb-2">
            Select File
          </label>
          <div className="border-2 border-dashed border-gray-700 rounded-lg p-8 text-center hover:border-blue-500 transition cursor-pointer">
            <input
              type="file"
              accept=".pdf,.docx,.txt,.md"
              onChange={e => setFile(e.target.files?.[0] || null)}
              className="hidden"
              id="file-input"
            />
            <label htmlFor="file-input" className="cursor-pointer">
              <Upload className="mx-auto mb-3 text-gray-500" size={32} />
              {file ? (
                <div>
                  <p className="text-white font-medium">{file.name}</p>
                  <p className="text-sm text-gray-500 mt-1">
                    {(file.size / 1024).toFixed(1)} KB
                  </p>
                </div>
              ) : (
                <div>
                  <p className="text-gray-400">Click to select a file</p>
                  <p className="text-sm text-gray-600 mt-1">PDF, DOCX, TXT, or MD</p>
                </div>
              )}
            </label>
          </div>
        </div>

        <div className="mb-6">
          <label className="block text-sm font-medium text-gray-400 mb-2">
            Chunking Strategy
          </label>
          <select
            value={strategy}
            onChange={e => setStrategy(e.target.value)}
            className="w-full bg-gray-800 border border-gray-700 rounded-lg px-4 py-2 text-white focus:outline-none focus:border-blue-500"
          >
            <option value="fixed">Fixed Size (500 chars, no overlap)</option>
            <option value="recursive">Recursive (respects paragraphs) - Recommended</option>
            <option value="sentence">Sentence-based (groups related sentences)</option>
          </select>
        </div>

        <button
          onClick={handleUpload}
          disabled={uploading || !file}
          className="w-full bg-blue-600 hover:bg-blue-700 disabled:bg-gray-700 disabled:cursor-not-allowed px-6 py-3 rounded-lg flex items-center justify-center gap-2 transition font-medium"
        >
          {uploading ? (
            <>
              <div className="w-4 h-4 border-2 border-white border-t-transparent rounded-full animate-spin" />
              Processing...
            </>
          ) : (
            <>
              <Upload size={16} />
              Upload & Process
            </>
          )}
        </button>
      </div>

      <div>
        <h3 className="text-xl font-semibold mb-4 flex items-center gap-2">
          Uploaded Documents
          <span className="text-sm text-gray-500 font-normal">({documents.length})</span>
        </h3>

        <div className="space-y-3">
          {documents.map(doc => (
            <div
              key={doc.id}
              className="bg-gray-900 rounded-lg p-4 border border-gray-800 flex items-center justify-between hover:border-gray-700 transition"
            >
              <div className="flex items-center gap-4">
                <div className="w-10 h-10 bg-blue-500/10 rounded-lg flex items-center justify-center">
                  <FileText className="text-blue-400" size={20} />
                </div>
                <div>
                  <p className="font-medium">{doc.filename}</p>
                  <div className="flex items-center gap-3 text-sm text-gray-500 mt-1">
                    <span>{doc.total_chunks} chunks</span>
                    <span>•</span>
                    <span className="capitalize">{doc.chunking_strategy}</span>
                    <span>•</span>
                    <span className="flex items-center gap-1 text-green-400">
                      <CheckCircle size={12} />
                      {doc.status}
                    </span>
                  </div>
                </div>
              </div>
              <button
                onClick={() => handleDelete(doc.id)}
                className="p-2 text-gray-500 hover:text-red-400 hover:bg-red-500/10 rounded-lg transition"
              >
                <Trash2 size={18} />
              </button>
            </div>
          ))}

          {documents.length === 0 && (
            <div className="text-center py-12 text-gray-500">
              <FileText className="mx-auto mb-3 opacity-30" size={48} />
              <p>No documents uploaded yet</p>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}