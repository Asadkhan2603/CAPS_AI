import { useEffect, useState } from 'react';
import { motion } from 'framer-motion';

const STRENGTH_CONFIG = {
  0: { label: 'Very Weak', color: 'bg-rose-500', textColor: 'text-rose-400', width: '20%' },
  1: { label: 'Weak', color: 'bg-orange-500', textColor: 'text-orange-400', width: '40%' },
  2: { label: 'Fair', color: 'bg-yellow-500', textColor: 'text-yellow-400', width: '60%' },
  3: { label: 'Good', color: 'bg-lime-500', textColor: 'text-lime-400', width: '80%' },
  4: { label: 'Strong', color: 'bg-emerald-500', textColor: 'text-emerald-400', width: '100%' }
};

export function PasswordStrengthMeter({ password, userInputs = [] }) {
  const [score, setScore] = useState(0);

  useEffect(() => {
    let active = true;

    if (!password) {
      setScore(0);
      return () => {
        active = false;
      };
    }

    async function evaluateStrength() {
      try {
        const { default: zxcvbn } = await import('zxcvbn');
        if (!active) {
          return;
        }
        const result = zxcvbn(password, userInputs);
        setScore(result.score);
      } catch (err) {
        if (import.meta.env.DEV) {
          console.error('Password strength calculation error:', err);
        }
        if (active) {
          setScore(0);
        }
      }
    }

    evaluateStrength();

    return () => {
      active = false;
    };
  }, [password, userInputs]);

  if (!password) {
    return null;
  }

  const config = STRENGTH_CONFIG[score];

  return (
    <motion.div
      initial={{ opacity: 0, height: 0 }}
      animate={{ opacity: 1, height: 'auto' }}
      exit={{ opacity: 0, height: 0 }}
      className="space-y-2"
      role="status"
      aria-live="polite"
      aria-label="Password strength indicator"
    >
      <div className="flex items-center justify-between text-xs">
        <span className="font-medium text-slate-400">Password Strength</span>
        <span className={`font-semibold ${config.textColor}`} aria-label={`Password strength is ${config.label}`}>{config.label}</span>
      </div>
      <div 
        className="h-1.5 w-full overflow-hidden rounded-full bg-white/10"
        role="progressbar"
        aria-label="Password strength meter"
        aria-valuenow={score}
        aria-valuemin={0}
        aria-valuemax={4}
        aria-valuetext={config.label}
      >
        <motion.div
          className={`h-full ${config.color}`}
          initial={{ width: '0%' }}
          animate={{ width: config.width }}
          transition={{ duration: 0.4, ease: 'easeOut' }}
          aria-hidden="true"
        />
      </div>
    </motion.div>
  );
}
