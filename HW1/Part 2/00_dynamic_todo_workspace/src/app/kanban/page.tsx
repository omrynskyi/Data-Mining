import KanbanBoard from '@/components/KanbanBoard';
import PageHeader from '@/components/PageHeader';
import { getTodosWithSubtasks } from '@/lib/db';

export const dynamic = 'force-dynamic';

export default async function KanbanPage() {
  const todos = getTodosWithSubtasks();

  return (
    <>
      <PageHeader
        title="Board"
        subtitle="Drag a card between columns, or move it with the arrow buttons."
      />
      <KanbanBoard initialTodos={todos} />
    </>
  );
}
