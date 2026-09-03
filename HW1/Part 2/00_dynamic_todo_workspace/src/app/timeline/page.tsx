import Timeline from '@/components/Timeline';
import PageHeader from '@/components/PageHeader';
import db from '@/lib/db';
import type { Todo } from '@/lib/db';

export const dynamic = 'force-dynamic';

export default async function TimelinePage() {
  const todos = db
    .prepare('SELECT * FROM todos WHERE dueDate IS NOT NULL ORDER BY dueDate ASC')
    .all() as Todo[];

  return (
    <>
      <PageHeader title="Timeline" subtitle="Everything with a due date, in the order it lands." />
      <Timeline todos={todos} />
    </>
  );
}
