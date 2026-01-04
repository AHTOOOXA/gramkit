'use client';

import { notFound } from 'next/navigation';
import { useGetCurrentUserUsersMeGet } from '@gen/hooks/useGetCurrentUserUsersMeGet';

export default function TestGenPage() {
  if (process.env.NODE_ENV === 'production') {
    notFound();
  }

  const { data, isLoading, error } = useGetCurrentUserUsersMeGet();

  return (
    <div className="flex min-h-screen flex-col items-center justify-center p-4">
      <div className="w-full max-w-md space-y-4">
        <h1 className="text-2xl font-bold">Kubb React Query Hook Test</h1>

        {isLoading && (
          <div className="rounded-lg border p-4">
            <p>Loading...</p>
          </div>
        )}

        {error && (
          <div className="rounded-lg border border-red-500 bg-red-50 p-4 text-red-900">
            <p className="font-bold">Error:</p>
            <pre className="mt-2 overflow-auto text-sm">
              {JSON.stringify(error, null, 2)}
            </pre>
          </div>
        )}

        {data && (
          <div className="rounded-lg border border-green-500 bg-green-50 p-4">
            <p className="font-bold text-green-900">Success! User data:</p>
            <pre className="mt-2 overflow-auto text-sm text-green-900">
              {JSON.stringify(data, null, 2)}
            </pre>
          </div>
        )}
      </div>
    </div>
  );
}
