'use client';

import { useEffect } from 'react';

import { Button } from '@/components/ui/button';
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from '@/components/ui/card';

export default function Error({
  error,
  reset,
}: {
  error: Error & { digest?: string };
  reset: () => void;
}) {
  useEffect(() => {
    console.error('Error boundary:', error);
  }, [error]);

  return (
    <div className="flex min-h-screen items-center justify-center p-4">
      <Card className="w-full max-w-md">
        <CardHeader className="text-center">
          <CardTitle>Something went wrong</CardTitle>
          <CardDescription>
            An error occurred while rendering this page
          </CardDescription>
        </CardHeader>
        <CardContent className="space-y-4">
          {process.env.NODE_ENV === 'development' && (
            <pre className="bg-muted rounded-md p-4 text-xs">
              {error.message}
            </pre>
          )}
          <Button onClick={reset} className="w-full">
            Try again
          </Button>
        </CardContent>
      </Card>
    </div>
  );
}
