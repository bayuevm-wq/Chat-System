'use client';

import { useState } from 'react';
import { useRouter } from 'next/navigation';
import Link from 'next/link';
import { motion } from 'framer-motion';
import { MessageSquare, Mail, Lock, AlertCircle, ArrowRight } from 'lucide-react';
import { api } from '@/shared/api';
import { useChatStore } from '@/shared/store';

export default function LoginPage() {
  const router = useRouter();
  const loginStore = useChatStore((state) => state.login);
  
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!email || !password) {
      setError('Please fill in all fields');
      return;
    }

    setError(null);
    setLoading(true);

    try {
      const response = await api.login({ email, password });
      loginStore(response.user, response.access_token, response.refresh_token);
      router.push('/dashboard');
    } catch (err: any) {
      setError(err.message || 'Login failed. Please check credentials.');
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="relative flex min-h-screen w-full items-center justify-center bg-[#090b11] px-4 py-12 overflow-hidden">
      {/* Visual background gradient glow effects */}
      <div className="absolute top-1/4 left-1/4 h-72 w-72 rounded-full bg-indigo-600/10 blur-[100px] pointer-events-none"></div>
      <div className="absolute bottom-1/4 right-1/4 h-82 w-82 rounded-full bg-blue-600/15 blur-[120px] pointer-events-none"></div>

      <motion.div
        initial={{ opacity: 0, y: 20 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ duration: 0.4, ease: 'easeOut' }}
        className="z-10 w-full max-w-md rounded-2xl glass-panel p-8 shadow-2xl"
      >
        <div className="flex flex-col items-center gap-2 mb-8 text-center">
          <div className="flex h-12 w-12 items-center justify-center rounded-xl bg-indigo-500/15 text-indigo-400 mb-2">
            <MessageSquare className="h-6 w-6" />
          </div>
          <h2 className="text-2xl font-bold tracking-tight text-white">Welcome Back</h2>
          <p className="text-sm text-gray-400">Connect to your distributed workspace</p>
        </div>

        {error && (
          <motion.div
            initial={{ opacity: 0, scale: 0.95 }}
            animate={{ opacity: 1, scale: 1 }}
            className="flex items-center gap-3 rounded-lg bg-rose-500/10 border border-rose-500/20 p-4 text-sm text-rose-400 mb-6"
          >
            <AlertCircle className="h-5 w-5 shrink-0" />
            <p>{error}</p>
          </motion.div>
        )}

        <form onSubmit={handleSubmit} className="flex flex-col gap-5">
          <div className="flex flex-col gap-1.5">
            <label className="text-xs font-semibold text-gray-300 tracking-wide uppercase">Email Address</label>
            <div className="relative">
              <Mail className="absolute top-1/2 left-3 h-5 w-5 -translate-y-1/2 text-gray-400" />
              <input
                type="email"
                placeholder="you@example.com"
                value={email}
                onChange={(e) => setEmail(e.target.value)}
                className="w-full pl-10 pr-4 py-3 rounded-lg text-sm text-white glass-input"
              />
            </div>
          </div>

          <div className="flex flex-col gap-1.5">
            <div className="flex items-center justify-between">
              <label className="text-xs font-semibold text-gray-300 tracking-wide uppercase">Password</label>
              <a href="#" className="text-xs text-indigo-400 hover:text-indigo-300 transition-colors">Forgot?</a>
            </div>
            <div className="relative">
              <Lock className="absolute top-1/2 left-3 h-5 w-5 -translate-y-1/2 text-gray-400" />
              <input
                type="password"
                placeholder="••••••••"
                value={password}
                onChange={(e) => setPassword(e.target.value)}
                className="w-full pl-10 pr-4 py-3 rounded-lg text-sm text-white glass-input"
              />
            </div>
          </div>

          <motion.button
            whileHover={{ scale: 1.01 }}
            whileTap={{ scale: 0.99 }}
            type="submit"
            disabled={loading}
            className="flex h-12 w-full items-center justify-center gap-2 rounded-lg bg-indigo-600 font-medium text-white shadow-lg shadow-indigo-600/20 hover:bg-indigo-500 transition-colors disabled:opacity-50 disabled:cursor-not-allowed mt-4"
          >
            {loading ? (
              <div className="h-5 w-5 animate-spin rounded-full border-2 border-white border-t-transparent"></div>
            ) : (
              <>
                Sign In
                <ArrowRight className="h-4 w-4" />
              </>
            )}
          </motion.button>
        </form>

        <p className="text-center text-sm text-gray-400 mt-8">
          Don't have an account?{' '}
          <Link href="/auth/register" className="font-semibold text-indigo-400 hover:text-indigo-300 transition-colors">
            Sign Up
          </Link>
        </p>
      </motion.div>
    </div>
  );
}
