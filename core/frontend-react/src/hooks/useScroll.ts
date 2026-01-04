import { useEffect, useState } from 'react';

export interface UseScrollReturn {
  x: number;
  y: number;
  isScrolling: boolean;
  lock: () => void;
  unlock: () => void;
  scrollTo: (element: HTMLElement, offset?: number) => void;
}

function getScrollPosition(): { x: number; y: number } {
  return {
    x: window.scrollX || window.pageXOffset,
    y: window.scrollY || window.pageYOffset,
  };
}

export function useScroll(): UseScrollReturn {
  const [scrollPos, setScrollPos] = useState(getScrollPosition());
  const [isScrolling, setIsScrolling] = useState(false);

  useEffect(() => {
    let timeoutId: NodeJS.Timeout;

    const handleScroll = () => {
      setScrollPos(getScrollPosition());
      setIsScrolling(true);

      clearTimeout(timeoutId);
      timeoutId = setTimeout(() => {
        setIsScrolling(false);
      }, 150);
    };

    window.addEventListener('scroll', handleScroll, { passive: true });

    return () => {
      window.removeEventListener('scroll', handleScroll);
      clearTimeout(timeoutId);
    };
  }, []);

  const lock = () => {
    if (typeof window === 'undefined') return;
    document.body.style.overflow = 'hidden';
  };

  const unlock = () => {
    if (typeof window === 'undefined') return;
    document.body.style.overflow = 'unset';
  };

  const scrollTo = (element: HTMLElement, offset = 0) => {
    if (typeof window === 'undefined') return;
    window.scrollTo({
      top: element.offsetTop - offset,
      behavior: 'smooth',
    });
  };

  return {
    x: scrollPos.x,
    y: scrollPos.y,
    isScrolling,
    lock,
    unlock,
    scrollTo,
  };
}
