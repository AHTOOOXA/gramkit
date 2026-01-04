'use client';

import { useEffect, useRef, useState } from 'react';

interface UseScrollRevealOptions {
  threshold?: number;
  rootMargin?: string;
  triggerOnce?: boolean;
}

/**
 * Hook for scroll-triggered reveal animations using IntersectionObserver.
 * Returns a ref to attach to the element and whether it's visible.
 *
 * @example
 * const { ref, isVisible } = useScrollReveal();
 * <div ref={ref} className={isVisible ? 'motion-preset-fade' : 'opacity-0'}>
 */
export function useScrollReveal<T extends HTMLElement = HTMLDivElement>({
  threshold = 0.1,
  rootMargin = '0px 0px 100px 0px',
  triggerOnce = true,
}: UseScrollRevealOptions = {}) {
  const ref = useRef<T>(null);
  const [isVisible, setIsVisible] = useState(false);

  useEffect(() => {
    const element = ref.current;
    if (!element) return;

    // Skip if already visible and triggerOnce is true
    if (isVisible && triggerOnce) return;

    const observer = new IntersectionObserver(
      ([entry]) => {
        if (entry?.isIntersecting) {
          setIsVisible(true);
          if (triggerOnce) {
            observer.disconnect();
          }
        } else if (!triggerOnce) {
          setIsVisible(false);
        }
      },
      { threshold, rootMargin }
    );

    observer.observe(element);

    return () => {
      observer.disconnect();
    };
  }, [threshold, rootMargin, triggerOnce, isVisible]);

  return { ref, isVisible };
}
