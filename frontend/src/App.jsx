import React from 'react';
import { Toaster } from 'react-hot-toast';
import { useStream } from './hooks/useStream';
import { ChatInput } from './components/ChatInput';
import { QualitySelector } from './components/QualitySelector';
import { AgentTimeLine } from './components/AgentTimeLine';
import { ResponseViewer } from './components/ResponseViewer';
import { MetadataFooter } from './components/MetadataFooter';

function App() {
  const {
    response,
    timeline, // lowercase 'l'
    metadata,
    loading,
    quality,
    setQuality,
    generate
  } = useStream();

  return (
    <div className="min-h-screen flex flex-col items-center py-12 px-4 sm:px-6">
      <Toaster position="top-center" />
      
      {/* Header */}
      <header className="text-center mb-10">
        <h1 className="text-3xl font-bold tracking-tight text-gray-900 mb-2">
          Agentic AI System
        </h1>
        <p className="text-gray-500 font-medium">Multi-Agent AI Assistant</p>
      </header>

      {/* Main Container */}
      <main className="w-full max-w-[900px] flex flex-col gap-6">
        
        {/* Controls Layer */}
        <section className="flex flex-col items-center">
          <QualitySelector 
            selected={quality} 
            onChange={setQuality} 
            disabled={loading} 
          />
          <div className="w-full max-w-[700px]">
            <ChatInput onGenerate={generate} loading={loading} />
          </div>
        </section>

        {/* Execution Details & Output */}
        {(timeline.length > 0 || response) && (
          <section className="mt-6 flex flex-col gap-6 w-full animate-in fade-in slide-in-from-bottom-4 duration-500">
            {/* Fixed the typo here: changed timeLine to timeline */}
            <AgentTimeLine timeline={timeline} />
            <ResponseViewer response={response} loading={loading} />
            <MetadataFooter metadata={metadata} />
          </section>
        )}
        
      </main>
    </div>
  );
}

export default App;