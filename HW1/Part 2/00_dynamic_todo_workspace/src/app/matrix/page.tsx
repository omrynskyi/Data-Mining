import EisenhowerMatrix from '@/components/EisenhowerMatrix';
import PageHeader from '@/components/PageHeader';
import db from '@/lib/db';
import type { Todo } from '@/lib/db';

export const dynamic = 'force-dynamic';

export default async function MatrixPage() {
  const todos = db.prepare('SELECT * FROM todos WHERE completed = 0').all() as Todo[];

  return (
    <>
      <PageHeader
        title="Matrix"
        subtitle="Open work split by how soon it is due and how much it matters."
      />
      <EisenhowerMatrix todos={todos} />
    </>
  );
}
