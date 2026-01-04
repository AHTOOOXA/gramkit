'use client';

import { useState } from 'react';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Lock, CheckCircle, XCircle } from 'lucide-react';
import { useDemoProtectedActionAdminDemoActionPost } from '@/src/gen/hooks/useDemoProtectedActionAdminDemoActionPost';

interface Props {
  canExecute: boolean;
}

export function ProtectedActionDemo({ canExecute }: Props) {
  const [result, setResult] = useState<{ success: boolean; message: string } | null>(null);

  const { mutate, isPending } = useDemoProtectedActionAdminDemoActionPost({
    mutation: {
      onSuccess: (data) => {
        setResult({ success: true, message: data.message });
      },
      onError: () => {
        setResult({ success: false, message: 'Access denied - owner role required' });
      },
    },
  });

  return (
    <Card>
      <CardHeader>
        <CardTitle>Try Protected Action</CardTitle>
      </CardHeader>
      <CardContent className="space-y-4">
        <p className="text-sm text-muted-foreground">
          This action requires <strong>owner</strong> role. Click to see what happens with your current role.
        </p>

        <Button
          onClick={() => {
            mutate();
          }}
          disabled={isPending}
          variant={canExecute ? 'default' : 'secondary'}
          className="active:scale-95 hover:-translate-y-0.5 hover:shadow-md hover:shadow-primary/20 transition-all duration-150"
        >
          <Lock className="h-4 w-4 mr-2" />
          Execute Protected Action
        </Button>

        {result && (
          <div className={`flex items-center gap-2 p-3 rounded-lg ${
            result.success
              ? 'bg-green-50 text-green-700 dark:bg-green-900/20 dark:text-green-400 motion-preset-pop motion-duration-[0.3s]'
              : 'bg-red-50 text-red-700 dark:bg-red-900/20 dark:text-red-400 motion-preset-shake motion-duration-[0.4s]'
          }`}
          key={result.success ? 'success' : 'error'}>
            {result.success ? (
              <CheckCircle className="h-5 w-5" />
            ) : (
              <XCircle className="h-5 w-5" />
            )}
            <span>{result.message}</span>
          </div>
        )}
      </CardContent>
    </Card>
  );
}
