'use client';

import { AnimatePresence, motion } from 'framer-motion';
import { AlertCircle } from 'lucide-react';

/** Transient failure notice for optimistic mutations that had to roll back. */
export default function ErrorToast({
  message,
  onDismiss,
}: {
  message: string | null;
  onDismiss: () => void;
}) {
  return (
    <AnimatePresence>
      {message && (
        <motion.div
          className="toast"
          role="status"
          initial={{ opacity: 0, y: 12, x: '-50%' }}
          animate={{ opacity: 1, y: 0, x: '-50%' }}
          exit={{ opacity: 0, y: 12, x: '-50%' }}
          transition={{ duration: 0.18, ease: [0.16, 1, 0.3, 1] }}
        >
          <AlertCircle size={16} strokeWidth={1.75} />
          <span>{message}</span>
          <button type="button" className="toast-action" onClick={onDismiss}>
            Dismiss
          </button>
        </motion.div>
      )}
    </AnimatePresence>
  );
}
