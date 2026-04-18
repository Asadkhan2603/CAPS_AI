import { useEffect, useState } from 'react';
import { Link, useNavigate } from 'react-router-dom';
import { ArrowRight, Mail, ArrowLeft, CheckCircle2 } from 'lucide-react';
import { motion } from 'framer-motion';
import Card from '../components/ui/Card';
import Spinner from '../components/ui/Spinner';
import { useToast } from '../hooks/useToast';
import { pushApiErrorToast } from '../utils/errorToast';
import { formatApiError } from '../utils/apiError';
import { apiClient } from '../services/apiClient';

export default function ForgotPasswordPage() {
  const navigate = useNavigate();
  const { pushToast } = useToast();
  
  const [email, setEmail] = useState('');
  const [error, setError] = useState('');
  const [loading, setLoading] = useState(false);
  const [submitted, setSubmitted] = useState(false);

  async function onSubmit(event) {
    event.preventDefault();
    setError('');
    setLoading(true);
    
    try {
      // Call forgot-password endpoint
      const response = await apiClient.post('/auth/forgot-password', { email });
      
      setSubmitted(true);
      pushToast({
        title: 'Reset link sent',
        description: `Check your email at ${email} for password reset instructions.`,
        variant: 'success'
      });
      
      // Redirect to login after 3 seconds
      setTimeout(() => {
        navigate('/login');
      }, 3000);
    } catch (err) {
      setError(formatApiError(err, 'Failed to send reset link'));
      pushApiErrorToast(pushToast, err, 'Failed to send reset link');
    } finally {
      setLoading(false);
    }
  }

  return (
    <main className="auth-shell relative flex min-h-screen items-center justify-center overflow-hidden p-4">
      <div className="absolute inset-0 z-0">
        <div className="auth-wallpaper" />
        <motion.div
          animate={{ scale: [1, 1.1, 1], rotate: [0, 5, 0] }}
          transition={{ duration: 20, repeat: Infinity, ease: 'linear' }}
          className="auth-orb left-[-10%] top-[-10%] h-[600px] w-[600px] bg-cyan-500/10 blur-[120px]"
        />
        <motion.div
          animate={{ scale: [1, 1.2, 1], rotate: [0, -5, 0] }}
          transition={{ duration: 25, repeat: Infinity, ease: 'linear' }}
          className="auth-orb right-[-5%] top-[20%] h-[500px] w-[500px] bg-blue-600/10 blur-[100px]"
        />
      </div>

      <section className="relative z-10 mx-auto w-full max-w-md">
        <motion.div
          initial={{ opacity: 0, y: 40, scale: 0.95 }}
          animate={{ opacity: 1, y: 0, scale: 1 }}
          transition={{ duration: 0.7, ease: [0.22, 1, 0.36, 1] }}
        >
          <div className="mb-8 text-center">
            <motion.div
              initial={{ scale: 0 }}
              animate={{ scale: 1 }}
              transition={{ type: 'spring', stiffness: 260, damping: 20, delay: 0.3 }}
              className="mx-auto mb-4 grid h-16 w-16 place-items-center rounded-2xl bg-gradient-to-br from-sky-500 to-indigo-600 text-white shadow-lg shadow-sky-500/20"
            >
              <Mail size={32} />
            </motion.div>
            <h1 className="text-3xl font-bold text-white">Reset Password</h1>
            <p className="mt-2 text-slate-400">
              {submitted ? 'Check your email for reset instructions' : 'We\'ll send you a link to reset your password'}
            </p>
          </div>

          <Card className="auth-card overflow-hidden !rounded-[2.5rem] !border-white/20 !bg-white/10 !shadow-[0_8px_32px_0_rgba(0,0,0,0.37)] !backdrop-blur-2xl">
            <div className="space-y-6 p-8 sm:p-10">
              {!submitted ? (
                <form className="space-y-5" onSubmit={onSubmit}>
                  <div className="space-y-2">
                    <label className="ml-1 text-xs font-bold uppercase tracking-wider text-slate-400">
                      Email Address
                    </label>
                    <div className="group relative">
                      <Mail
                        className="absolute left-4 top-1/2 -translate-y-1/2 text-slate-500 transition-colors group-focus-within:text-sky-400"
                        size={18}
                      />
                      <input
                        className="input-auth pl-12"
                        type="email"
                        placeholder="name@university.edu"
                        required
                        value={email}
                        onChange={(e) => setEmail(e.target.value)}
                        disabled={loading}
                      />
                    </div>
                  </div>

                  {error && (
                    <motion.div
                      initial={{ opacity: 0, height: 0 }}
                      animate={{ opacity: 1, height: 'auto' }}
                      className="rounded-xl border border-rose-500/20 bg-rose-500/10 px-4 py-3 text-center text-xs font-medium text-rose-400"
                    >
                      <p>{error}</p>
                    </motion.div>
                  )}

                  <motion.button
                    whileHover={{ scale: 1.03, filter: 'brightness(1.1)', boxShadow: '0 0 25px rgba(79, 70, 229, 0.5)' }}
                    whileTap={{ scale: 0.97 }}
                    className="flex w-full items-center justify-center gap-2 rounded-2xl bg-gradient-to-r from-brand-500 to-brand-600 py-4 text-sm font-bold text-white shadow-lg transition-all disabled:cursor-not-allowed disabled:opacity-50"
                    type="submit"
                    disabled={loading}
                  >
                    {loading ? (
                      <>
                        <Spinner size="sm" />
                        <span>Sending...</span>
                      </>
                    ) : (
                      <>
                        <span>Send Reset Link</span>
                        <ArrowRight size={18} />
                      </>
                    )}
                  </motion.button>
                </form>
              ) : (
                <div className="space-y-4 py-4 text-center">
                  <motion.div
                    initial={{ scale: 0 }}
                    animate={{ scale: 1 }}
                    transition={{ type: 'spring', stiffness: 260, damping: 20 }}
                    className="flex justify-center"
                  >
                    <CheckCircle2 size={48} className="text-emerald-400" />
                  </motion.div>
                  <div className="space-y-2">
                    <h2 className="text-xl font-bold text-white">Check your email</h2>
                    <p className="text-sm text-slate-400">
                      We've sent password reset instructions to<br />
                      <span className="font-semibold text-sky-300">{email}</span>
                    </p>
                  </div>
                  <p className="text-xs text-slate-500">
                    Redirecting to login in 3 seconds...
                  </p>
                </div>
              )}

              <div className="border-t border-white/10 pt-6">
                <Link
                  to="/login"
                  className="inline-flex items-center gap-2 text-xs font-semibold text-sky-400 transition-colors hover:text-sky-300"
                >
                  <ArrowLeft size={16} />
                  Back to login
                </Link>
              </div>
            </div>
          </Card>
        </motion.div>
      </section>
    </main>
  );
}
