import React from 'react';
import ReactMarkdown from 'react-markdown';
import { Sparkles } from 'lucide-react';

export const ResponseViewer = ({ response, loading }) => {
  if (!response && !loading) return null;

  return (
    <div className="bg-white rounded-2xl p-6 shadow-sm border border-gray-100 min-h-[150px]">
      <div className="flex items-center gap-2 mb-4 text-gray-800 font-semibold border-b border-gray-100 pb-4">
        <Sparkles className="w-5 h-5 text-indigo-500" />
        Response
      </div>
      
      <div className="prose prose-slate max-w-none prose-p:leading-relaxed prose-pre:bg-gray-50 prose-pre:border prose-pre:border-gray-200 prose-pre:text-gray-800">
        <ReactMarkdown>{response}</ReactMarkdown>
        {loading && (
          <span className="inline-block w-2 h-5 ml-1 bg-gray-400 animate-pulse align-middle"></span>
        )}
      </div>
    </div>
  );
};