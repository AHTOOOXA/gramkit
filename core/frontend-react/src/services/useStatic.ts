export function useStatic() {
  const apiHost = process.env.NEXT_PUBLIC_API_HOST;
  if (!apiHost) {
    throw new Error(
      'NEXT_PUBLIC_API_HOST environment variable is required.\n' +
      'Set it in your .env file, for example: NEXT_PUBLIC_API_HOST=http://localhost:3000'
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
