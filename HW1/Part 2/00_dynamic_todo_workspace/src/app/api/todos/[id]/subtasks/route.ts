import { NextResponse } from 'next/server';
import db from '@/lib/db';

export async function POST(
  request: Request,
  { params }: { params: Promise<{ id: string }> }
) {
  try {
    const { id } = await params;
    const body = await request.json();
    const { title } = body;

    if (!title) {
      return NextResponse.json({ error: 'Title is required' }, { status: 400 });
    }

    const stmt = db.prepare(`
      INSERT INTO subtasks (todo_id, title) 
      VALUES (?, ?)
    `);
    
    const result = stmt.run(id, title);
    
    const newSubtask = db.prepare('SELECT * FROM subtasks WHERE id = ?').get(result.lastInsertRowid);
    
    return NextResponse.json(newSubtask, { status: 201 });
  } catch {
    return NextResponse.json({ error: 'Failed to create subtask' }, { status: 500 });
  }
}
