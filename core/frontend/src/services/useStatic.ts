export function useStatic() {
  const apiHost = import.meta.env.VITE_API_HOST;
  if (!apiHost) {
    throw new Error(
      'VITE_API_HOST environment variable is required.\n' +
      'Set it in your .env file, for example: VITE_API_HOST=http://localhost:3000'
    );
  }

  const getStaticUrl = (path: string): string => {
    return `${apiHost}/static/${path}`;
  };

  const preloadImage = (path: string): Promise<void> =>
    new Promise((resolve, reject) => {
      const img = new Image();
      img.onload = () => resolve();
      img.onerror = () => reject(new Error(`Failed to load image: ${path}`));
      img.src = getStaticUrl(path);
    });

  return { getStaticUrl, preloadImage };
}
