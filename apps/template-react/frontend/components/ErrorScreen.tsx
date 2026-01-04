'use client';

interface ErrorScreenProps {
  error: Error;
}

export const ErrorScreen = ({ error }: ErrorScreenProps) => {
  const handleReload = () => {
    window.location.reload();
  };

  return (
    <div className="flex h-screen w-screen items-center justify-center bg-background p-4">
      <div className="flex flex-col items-center gap-4 text-center">
        <div className="text-6xl">⚠️</div>

        <h1 className="text-xl font-bold text-foreground">
          Initialization Failed
        </h1>

        <p className="text-sm text-muted-foreground">
          {error.message}
        </p>

        <button
          onClick={handleReload}
          className="rounded-lg bg-primary px-6 py-3 text-primary-foreground transition hover:opacity-80"
        >
          Reload App
        </button>
      </div>
    </div>
  );
};
