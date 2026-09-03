import TodoList from '@/components/TodoList';
import PageHeader from '@/components/PageHeader';
import { getTodosWithSubtasks } from '@/lib/db';

export const dynamic = 'force-dynamic';

export default async function Home() {
  const todos = getTodosWithSubtasks();
  const open = todos.filter((t) => t.completed === 0).length;

  return (
    <>
      <PageHeader
        title="List"
        subtitle={
          open === 0
            ? 'Nothing outstanding. Add a task to get going.'
            : `${open} task${open === 1 ? '' : 's'} still open across every category.`
        }
      />
      <TodoList initialTodos={todos} />
    </>
  );
}
