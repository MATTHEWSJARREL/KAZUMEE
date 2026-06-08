import React from 'react';
import { useClipSearch } from '@/lib/ClipSearchContext';
import { apiFetch } from '@/lib/apiClient';

export default function ClipSearchResults() {
  const { results } = useClipSearch();

  if (!results || results.length === 0) return null;

  return (
    <div className="fixed right-4 top-16 w-80 bg-white/90 dark:bg-[#111] rounded shadow-lg p-3 z-50">
      <h3 className="text-sm font-semibold mb-2">Found Clips</h3>
      <ul className="text-xs">
        {results.map((clip, idx) => (
          <li key={idx} className="mb-2">
            <div className="font-medium">{clip.title}</div>
            <div className="text-[11px] text-gray-600 break-words">{clip.path}</div>
            <div className="mt-1">
              <button
                className="text-xs px-2 py-1 rounded bg-blue-500 text-white"
                onClick={async () => {
                  try {
                    await apiFetch('/clips/open', {
                      method: 'POST',
                      headers: { 'Content-Type': 'application/json' },
                      body: JSON.stringify({ path: clip.path }),
                    });
                  } catch (e) {
                    console.warn('Open clip failed', e);
                  }
                }}
              >
                Open
              </button>
            </div>
          </li>
        ))}
      </ul>
    </div>
  );
}
