import { motion, useReducedMotion } from 'framer-motion';
import type { ReactNode } from 'react';
import { cn } from '../../utils/cn';

type MainContentProps = {
  routeKey: string;
  headerHeight: number;
  interactionLocked?: boolean;
  children: ReactNode;
};

export default function MainContent({
  routeKey,
  headerHeight,
  interactionLocked = false,
  children
}: MainContentProps) {
  const prefersReducedMotion = useReducedMotion();

  return (
    <main
      className={cn(
        'overflow-x-hidden',
        interactionLocked ? 'overflow-hidden touch-none overscroll-none' : 'overflow-y-auto'
      )}
      style={{ height: `calc(100vh - ${headerHeight}px)` }}
    >
      <motion.div
        key={routeKey}
        initial={prefersReducedMotion ? false : { opacity: 0, y: 10 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ duration: prefersReducedMotion ? 0 : 0.18, ease: 'easeOut' }}
        className="mx-auto w-full max-w-[1580px] px-3 py-3 sm:px-4 sm:py-4 lg:px-5 lg:py-5"
      >
        <div className="page-canvas">{children}</div>
      </motion.div>
    </main>
  );
}
