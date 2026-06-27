import React from 'react';

const QUALITY_OPTIONS = [
  { label: 'Fast', value: 5 },
  { label: 'Balanced', value: 7 },
  { label: 'High', value: 9 },
  { label: 'Maximum', value: 10 },
];

export const QualitySelector = ({ selected, onChange, disabled }) => {
  return (
    <div className="flex flex-wrap gap-2 mb-6">
      {QUALITY_OPTIONS.map((opt) => (
        <button
          key={opt.value}
          disabled={disabled}
          onClick={() => onChange(opt.value)}
          className={`px-4 py-2 rounded-full text-sm font-medium transition-colors ${
            selected === opt.value
              ? 'bg-black text-white'
              : 'bg-white text-gray-600 hover:bg-gray-100 border border-gray-200'
          } ${disabled ? 'opacity-50 cursor-not-allowed' : 'cursor-pointer'}`}
        >
          {opt.label}
        </button>
      ))}
    </div>
  );
};