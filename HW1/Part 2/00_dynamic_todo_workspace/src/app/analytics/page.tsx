import AnalyticsDashboard from '@/components/AnalyticsDashboard';
import PageHeader from '@/components/PageHeader';
import db from '@/lib/db';
import type { Todo } from '@/lib/db';

export const dynamic = 'force-dynamic';

export default async function AnalyticsPage() {
  const todos = db.prepare('SELECT * FROM todos').all() as Todo[];

  return (
    <>
      <PageHeader title="Analytics" subtitle="Completion history, streaks, and progress by category." />
      <AnalyticsDashboard todos={todos} />
    </>
  );
}
