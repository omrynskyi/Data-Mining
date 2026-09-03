import { NextResponse } from 'next/server';
import db from '@/lib/db';
import type { Subtask } from '@/lib/db';

export async function PUT(
  request: Request,
  { params }: { params: Promise<{ id: string }> }
) {
  try {
    const { id } = await params;
    const body = await request.json();
    const { completed, title } = body;
    
    const currentSubtask = db.prepare('SELECT * FROM subtasks WHERE id = ?').get(id) as Subtask | undefined;
    if (!currentSubtask) {
      return NextResponse.json({ error: 'Subtask not found' }, { status: 404 });
    }

    const stmt = db.prepare(`
      UPDATE subtasks 
      SET 
        title = COALESCE(?, title),
        completed = COALESCE(?, completed)
      WHERE id = ?
    `);

    stmt.run(
      title !== undefined ? title : currentSubtask.title,
      completed !== undefined ? completed : currentSubtask.completed,
      id
    );

    const updatedSubtask = db.prepare('SELECT * FROM subtasks WHERE id = ?').get(id);
    return NextResponse.json(updatedSubtask);
  } catch {
    return NextResponse.json({ error: 'Failed to update subtask' }, { status: 500 });
  }
}

export async function DELETE(
  request: Request,
  { params }: { params: Promise<{ id: string }> }
) {
  try {
    const { id } = await params;
    const stmt = db.prepare('DELETE FROM subtasks WHERE id = ?');
    const result = stmt.run(id);
    
    if (result.changes === 0) {
      return NextResponse.json({ error: 'Subtask not found' }, { status: 404 });
    }
    
    return NextResponse.json({ message: 'Subtask deleted successfully' });
  } catch {
    return NextResponse.json({ error: 'Failed to delete subtask' }, { status: 500 });
  }
}
