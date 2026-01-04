import { LoadingSpinner } from './loading-spinner';

export function PageLoading() {
  return (
    <div className="flex h-screen items-center justify-center">
      <LoadingSpinner size="lg" />
    </div>
  );
}
