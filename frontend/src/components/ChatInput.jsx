import React, { useState } from 'react';
import { Send, Square } from 'lucide-react';

export const ChatInput = ({ onGenerate, loading }) => {
  const [prompt, setPrompt] = useState('');

  const handleSubmit = (e) => {
    e.preventDefault();
    if (!loading && prompt.trim()) {
      onGenerate(prompt);
    }
  };

  const handleKeyDown = (e) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      handleSubmit(e);
    }
  };

  return (
    <form onSubmit={handleSubmit} className="relative w-full shadow-sm rounded-2xl bg-white border border-gray-200 focus-within:ring-2 focus-within:ring-blue-100 focus-within:border-blue-300 transition-all">
      <textarea
        value={prompt}
        onChange={(e) => setPrompt(e.target.value)}
        onKeyDown={handleKeyDown}
        placeholder="Ask anything..."
        className="w-full min-h-[100px] p-4 pr-14 bg-transparent outline-none resize-none text-gray-800 placeholder-gray-400"
        disabled={loading}
      />
      <div className="absolute bottom-3 right-3">
        <button
          type={loading ? "button" : "submit"}
          disabled={!prompt.trim() && !loading}
          className={`p-2 rounded-xl flex items-center justify-center transition-colors ${
            loading 
              ? 'bg-gray-200 text-gray-500 cursor-not-allowed'
              : prompt.trim()
                ? 'bg-black text-white hover:bg-gray-800'
                : 'bg-gray-100 text-gray-400 cursor-not-allowed'
          }`}
        >
          {loading ? <Square className="w-5 h-5 fill-current" /> : <Send className="w-5 h-5" />}
        </button>
      </div>
    </form>
  );
};