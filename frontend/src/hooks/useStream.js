import { useState } from 'react';
import { useCallback } from 'react';
import { executeStream } from '../services/streamAPI';
import toast from 'react-hot-toast';

export const useStream = () => {
  const [response, setResponse] = useState("");
  const [timeline, setTimeline] = useState([]);
  const [metadata, setMetadata] = useState(null);
  const [loading, setLoading] = useState(false);
  const [quality, setQuality] = useState(9); // Default to High

  const generate = useCallback(async (prompt) => {
    if (!prompt.trim()) {
      toast.error("Please enter a prompt");
      return;
    }

    setResponse("");
    setTimeline([]);
    setMetadata(null);
    setLoading(true);

    executeStream(
      prompt,
      quality,
      (event) => {
        switch (event.type) {
          case 'plan':
            // Initialize timeline as 'waiting' for all steps
            setTimeline(event.data.map(step => ({ ...step, status: 'waiting' })));
            break;
            
          case 'status':
            setTimeline(prev => prev.map(step => 
              step.agent === event.agent 
                ? { ...step, status: 'running', message: event.message } 
                : step
            ));
            break;
            
          case 'token':
            setResponse(prev => prev + event.content);
            break;
            
          case 'agent_complete':
            setTimeline(prev => prev.map(step => 
              step.agent === event.agent 
                ? { ...step, status: 'completed' } 
                : step
            ));
            break;
            
          case 'metadata':
            setMetadata(event.data);
            break;
            
          case 'final':
            setLoading(false);
            break;
            
          default:
            console.warn("Unknown event type:", event.type);
        }
      },
      (error) => {
        console.error("Stream error:", error);
        toast.error("Failed to connect to the agentic system.");
        setLoading(false);
      },
      () => {
        setLoading(false);
      }
    );
  }, [quality]);

  return {
    response,
    timeline,
    metadata,
    loading,
    quality,
    setQuality,
    generate
  };
};


