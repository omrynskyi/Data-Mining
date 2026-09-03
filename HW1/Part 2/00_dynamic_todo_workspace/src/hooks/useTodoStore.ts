'use client';

import { useCallback, useRef, useState } from 'react';
import type { Todo } from '@/lib/db';

/**
 * Optimistic task mutations with rollback.
 *
 * Every view used to fire a `fetch` and swallow failures with `console.error`,
 * so a dropped request left the UI showing state the database never accepted.
 * Here each mutation snapshots the list, applies the change immediately, and
 * restores the snapshot plus surfaces a message if the request fails.
 */
export function useTodoStore(initialTodos: Todo[]) {
  const [todos, setTodos] = useState<Todo[]>(initialTodos);
  const [error, setError] = useState<string | null>(null);
  const errorTimer = useRef<ReturnType<typeof setTimeout> | null>(null);

  const raise = useCallback((message: string) => {
    setError(message);
    if (errorTimer.current) clearTimeout(errorTimer.current);
    errorTimer.current = setTimeout(() => setError(null), 5000);
  }, []);

  const dismissError = useCallback(() => {
    if (errorTimer.current) clearTimeout(errorTimer.current);
    setError(null);
  }, []);

  const patch = useCallback(
    async (id: number, changes: Partial<Todo>, failureMessage: string) => {
      let snapshot: Todo[] = [];
      setTodos((current) => {
        snapshot = current;
        return current.map((t) => (t.id === id ? { ...t, ...changes } : t));
      });

      try {
        const res = await fetch(`/api/todos/${id}`, {
          method: 'PUT',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify(changes),
        });
        if (!res.ok) throw new Error(String(res.status));
        const saved: Todo = await res.json();
        // Reconcile with the server row so derived fields (completedAt) are real.
        setTodos((current) =>
          current.map((t) => (t.id === id ? { ...t, ...saved, subtasks: t.subtasks } : t))
        );
      } catch {
        setTodos(snapshot);
        raise(failureMessage);
      }
    },
    [raise]
  );

  const toggle = useCallback(
    (id: number, completed: number) => {
      const changes: Partial<Todo> = { completed };
      // Completing from the list should also settle the board column.
      changes.status = completed === 1 ? 'Done' : 'To Do';
      return patch(id, changes, 'Could not save that change. It has been undone.');
    },
    [patch]
  );

  const setStatus = useCallback(
    (id: number, status: string) =>
      patch(
        id,
        { status, completed: status === 'Done' ? 1 : 0 },
        'Could not move that task. It has been put back.'
      ),
    [patch]
  );

  const rename = useCallback(
    (id: number, title: string) => patch(id, { title }, 'Could not rename that task.'),
    [patch]
  );

  const remove = useCallback(
    async (id: number) => {
      let snapshot: Todo[] = [];
      setTodos((current) => {
        snapshot = current;
        return current.filter((t) => t.id !== id);
      });

      try {
        const res = await fetch(`/api/todos/${id}`, { method: 'DELETE' });
        if (!res.ok) throw new Error(String(res.status));
      } catch {
        setTodos(snapshot);
        raise('Could not delete that task. It has been restored.');
      }
    },
    [raise]
  );

  const add = useCallback((todo: Todo) => {
    setTodos((current) => [{ ...todo, subtasks: [] }, ...current]);
  }, []);

  return { todos, error, dismissError, add, toggle, setStatus, rename, remove };
}
