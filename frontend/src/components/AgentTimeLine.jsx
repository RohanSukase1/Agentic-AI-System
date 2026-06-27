import React from 'react';
import { StatusIcon } from './StatusIcon';

export const AgentTimeLine = ({ timeline }) => {
  if (!timeline || timeline.length === 0) return null;

  return (
    <div className="bg-white rounded-2xl border border-gray-100 p-6 shadow-sm mb-6">
      <h3 className="text-sm font-semibold text-gray-500 mb-4 uppercase tracking-wider">Agent Execution</h3>
      <div className="space-y-4">
        {timeline.map((step, idx) => (
          <div key={idx} className="flex items-start gap-4">
            <div className="mt-0.5">
              <StatusIcon status={step.status} />
            </div>
            <div>
              <div className="flex items-center gap-2">
                <span className="font-medium text-gray-900 capitalize">{step.agent}</span>
                {step.status === 'running' && (
                  <span className="text-xs bg-blue-50 text-blue-600 px-2 py-0.5 rounded-full font-medium">
                    Active
                  </span>
                )}
              </div>
              <p className="text-sm text-gray-500 mt-0.5">
                {step.status === 'running' && step.message ? step.message : step.task}
              </p>
            </div>
          </div>
        ))}
      </div>
    </div>
  );
};