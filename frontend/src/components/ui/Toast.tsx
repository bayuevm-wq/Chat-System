'use client';

import { useEffect } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { CheckCircle2, AlertCircle, Info, X } from 'lucide-react';
import { useChatStore, ToastMessage } from '@/shared/store';

export default function ToastStack() {
  const toasts = useChatStore((state) => state.toasts);

  return (
    <div className="fixed bottom-5 right-5 z-50 flex flex-col gap-3 max-w-sm w-full pointer-events-none">
      <AnimatePresence>
        {toasts.map((toast) => (
          <ToastItem key={toast.id} toast={toast} />
        ))}
      </AnimatePresence>
    </div>
  );
}

function ToastItem({ toast }: { toast: ToastMessage }) {
  const removeToast = useChatStore((state) => state.removeToast);

  useEffect(() => {
    const timer = setTimeout(() => {
      removeToast(toast.id);
    }, 4000); // Auto-dismiss after 4 seconds

    return () => clearTimeout(timer);
  }, [toast.id, removeToast]);

  const config = {
    success: {
      bg: 'bg-emerald-950/90 border-emerald-500/20 text-emerald-300',
      icon: <CheckCircle2 className="h-5 w-5 text-emerald-400 shrink-0" />,
    },
    error: {
      bg: 'bg-rose-950/90 border-rose-500/20 text-rose-300',
      icon: <AlertCircle className="h-5 w-5 text-rose-400 shrink-0" />,
    },
    warning: {
      bg: 'bg-amber-950/90 border-amber-500/20 text-amber-300',
      icon: <AlertCircle className="h-5 w-5 text-amber-400 shrink-0" />,
    },
    info: {
      bg: 'bg-[#151824]/90 border-indigo-500/10 text-indigo-300',
      icon: <Info className="h-5 w-5 text-indigo-400 shrink-0" />,
    },
  };

  const style = config[toast.type] || config.info;

  return (
    <motion.div
      initial={{ opacity: 0, y: 15, scale: 0.95 }}
      animate={{ opacity: 1, y: 0, scale: 1 }}
      exit={{ opacity: 0, scale: 0.9, transition: { duration: 0.15 } }}
      className={`pointer-events-auto flex items-center justify-between gap-4 p-4 rounded-xl border backdrop-blur-md shadow-2xl ${style.bg}`}
    >
      <div className="flex items-center gap-3">
        {style.icon}
        <p className="text-sm font-medium tracking-wide leading-relaxed">{toast.message}</p>
      </div>
      <button
        onClick={() => removeToast(toast.id)}
        className="text-gray-400 hover:text-white hover:bg-white/5 p-1 rounded-lg transition-colors cursor-pointer shrink-0"
      >
        <X className="h-4 w-4" />
      </button>
    </motion.div>
  );
}
