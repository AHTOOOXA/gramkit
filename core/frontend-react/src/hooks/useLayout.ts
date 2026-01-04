import { useEffect, useState } from 'react';

export interface UseLayoutReturn {
  width: number;
  height: number;
  isMobile: boolean;
  isTablet: boolean;
  isDesktop: boolean;
}

export function useLayout(): UseLayoutReturn {
  const [dimensions, setDimensions] = useState({
    width: typeof window !== 'undefined' ? window.innerWidth : 0,
    height: typeof window !== 'undefined' ? window.innerHeight : 0,
  });

  useEffect(() => {
    const handleResize = () => {
      setDimensions({
        width: window.innerWidth,
        height: window.innerHeight,
      });
    };

    window.addEventListener('resize', handleResize);
    return () => window.removeEventListener('resize', handleResize);
  }, []);

  return {
    width: dimensions.width,
    height: dimensions.height,
    isMobile: dimensions.width < 768,
    isTablet: dimensions.width >= 768 && dimensions.width < 1024,
    isDesktop: dimensions.width >= 1024,
  };
}
