import { NextResponse } from 'next/server';
import db from '@/lib/db';
import type { Todo } from '@/lib/db';

export async function PUT(
  request: Request,
  { params }: { params: Promise<{ id: string }> }
) {
  try {
    const { id } = await params;
    const body = await request.json();
    
    // We can update any of these fields
    const { title, category, priority, completed, dueDate, status, tags, completedAt } = body;
    
    const currentTodo = db.prepare('SELECT * FROM todos WHERE id = ?').get(id) as Todo | undefined;
    if (!currentTodo) {
      return NextResponse.json({ error: 'Todo not found' }, { status: 404 });
    }

    // Auto-set completedAt if completing now and not explicitly passed
    let finalCompletedAt = completedAt;
    if (completed === 1 && currentTodo.completed === 0 && finalCompletedAt === undefined) {
      finalCompletedAt = new Date().toISOString();
    } else if (completed === 0 && currentTodo.completed === 1 && finalCompletedAt === undefined) {
      finalCompletedAt = null;
    }

    const stmt = db.prepare(`
      UPDATE todos 
      SET 
        title = COALESCE(?, title),
        category = COALESCE(?, category),
        priority = COALESCE(?, priority),
        completed = COALESCE(?, completed),
        dueDate = COALESCE(?, dueDate),
        status = COALESCE(?, status),
        tags = COALESCE(?, tags),
        completedAt = ?
      WHERE id = ?
    `);

    stmt.run(
      title !== undefined ? title : currentTodo.title,
      category !== undefined ? category : currentTodo.category,
      priority !== undefined ? priority : currentTodo.priority,
      completed !== undefined ? completed : currentTodo.completed,
      dueDate !== undefined ? dueDate : currentTodo.dueDate,
      status !== undefined ? status : currentTodo.status,
      tags !== undefined ? JSON.stringify(tags) : currentTodo.tags,
      finalCompletedAt !== undefined ? finalCompletedAt : currentTodo.completedAt,
      id
    );

    const updatedTodo = db.prepare('SELECT * FROM todos WHERE id = ?').get(id);
    return NextResponse.json(updatedTodo);
  } catch {
    return NextResponse.json({ error: 'Failed to update todo' }, { status: 500 });
  }
}

export async function DELETE(
  request: Request,
  { params }: { params: Promise<{ id: string }> }
) {
  try {
    const { id } = await params;
    const stmt = db.prepare('DELETE FROM todos WHERE id = ?');
    const result = stmt.run(id);
    
    if (result.changes === 0) {
      return NextResponse.json({ error: 'Todo not found' }, { status: 404 });
    }
    
    return NextResponse.json({ message: 'Todo deleted successfully' });
  } catch {
    return NextResponse.json({ error: 'Failed to delete todo' }, { status: 500 });
  }
}
