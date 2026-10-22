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
    new Promise((resolve) => {
      const img = new Image();
      const timeout = setTimeout(() => resolve(), 10000);
      img.onload = () => { clearTimeout(timeout); resolve(); };
      img.onerror = () => { clearTimeout(timeout); resolve(); };
      img.src = getStaticUrl(path);
    });

  return { getStaticUrl, preloadImage };
}
