import React from 'react';
import { Clock, CheckCircle, Activity } from 'lucide-react';

export const MetadataFooter = ({ metadata }) => {
  if (!metadata) return null;

  const qualityMap = {
    5: 'Fast',
    7: 'Balanced',
    9: 'High',
    10: 'Maximum'
  };

  return (
    <div className="mt-6 flex flex-wrap gap-4 text-sm text-gray-500 justify-center">
      <div className="flex items-center gap-1.5 bg-gray-50 px-3 py-1.5 rounded-lg border border-gray-100">
        <Clock className="w-4 h-4" />
        <span>{metadata.execution_time} sec</span>
      </div>
      <div className="flex items-center gap-1.5 bg-gray-50 px-3 py-1.5 rounded-lg border border-gray-100">
        <Activity className="w-4 h-4" />
        <span>Quality: {qualityMap[metadata.quality_level] || metadata.quality_level}</span>
      </div>
      <div className="flex items-center gap-1.5 bg-gray-50 px-3 py-1.5 rounded-lg border border-gray-100">
        <CheckCircle className="w-4 h-4" />
        <span>{metadata.passes} Passes</span>
      </div>
    </div>
  );
};