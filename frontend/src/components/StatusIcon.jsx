import React from 'react';
import { CheckCircle2, Circle, Loader2 } from 'lucide-react';

export const StatusIcon = ({ status }) => {
  if (status === 'completed') {
    return <CheckCircle2 className="w-5 h-5 text-green-500" />;
  }
  if (status === 'running') {
    return <Loader2 className="w-5 h-5 text-blue-500 animate-spin" />;
  }
  return <Circle className="w-5 h-5 text-gray-300" />;
};