import { useEffect, useState, RefObject } from 'react';

export function usePlaceholderHeight(ref: RefObject<HTMLElement>) {
  const [height, setHeight] = useState(0);

  useEffect(() => {
    const calculateHeight = () => {
      if (!ref.current) return;

      const element = ref.current;
      const styles = window.getComputedStyle(element);

      const elementHeight = element.getBoundingClientRect().height;
      const marginTop = parseFloat(styles.marginTop);
      const marginBottom = parseFloat(styles.marginBottom);
      const paddingTop = parseFloat(styles.paddingTop);
      const paddingBottom = parseFloat(styles.paddingBottom);

      setHeight(elementHeight + marginTop + marginBottom + paddingTop + paddingBottom);
    };

    calculateHeight();

    // Recalculate on window resize
    window.addEventListener('resize', calculateHeight);
    return () => window.removeEventListener('resize', calculateHeight);
  }, [ref]);

  return height;
}
