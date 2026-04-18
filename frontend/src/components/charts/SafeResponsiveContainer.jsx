import { useEffect, useRef, useState } from 'react';
import { ResponsiveContainer } from 'recharts';

export default function SafeResponsiveContainer({
  width = '100%',
  height = '100%',
  minWidth = 0,
  minHeight = 1,
  debounce = 16,
  children,
  ...props
}) {
  const containerRef = useRef(null);
  const [isReady, setIsReady] = useState(false);

  useEffect(() => {
    const element = containerRef.current;
    if (!element) {
      return undefined;
    }

    const updateSizeState = () => {
      const nextWidth = element.clientWidth;
      const nextHeight = element.clientHeight;
      setIsReady(nextWidth > 0 && nextHeight > 0);
    };

    updateSizeState();

    if (typeof ResizeObserver === 'undefined') {
      window.addEventListener('resize', updateSizeState);
      return () => {
        window.removeEventListener('resize', updateSizeState);
      };
    }

    const observer = new ResizeObserver(() => {
      updateSizeState();
    });
    observer.observe(element);

    return () => {
      observer.disconnect();
    };
  }, []);

  return (
    <div ref={containerRef} style={{ width, height, minWidth, minHeight }}>
      {isReady ? (
        <ResponsiveContainer
          width="100%"
          height="100%"
          minWidth={minWidth}
          minHeight={minHeight}
          debounce={debounce}
          {...props}
        >
          {children}
        </ResponsiveContainer>
      ) : null}
    </div>
  );
}
