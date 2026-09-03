import { NextResponse } from 'next/server';
import db from '@/lib/db';

export async function GET() {
  try {
    const todos = db.prepare('SELECT * FROM todos ORDER BY createdAt DESC').all();
    return NextResponse.json(todos);
  } catch {
    return NextResponse.json({ error: 'Failed to fetch todos' }, { status: 500 });
  }
}

export async function POST(request: Request) {
  try {
    const body = await request.json();
    const { title, category, priority, dueDate, tags } = body;

    if (!title) {
      return NextResponse.json({ error: 'Title is required' }, { status: 400 });
    }

    const stmt = db.prepare(`
      INSERT INTO todos (title, category, priority, dueDate, tags) 
      VALUES (?, ?, ?, ?, ?)
    `);
    
    const result = stmt.run(
      title, 
      category || 'Personal', 
      priority || 'Medium', 
      dueDate || null,
      tags ? JSON.stringify(tags) : '[]'
    );
    
    const newTodo = db.prepare('SELECT * FROM todos WHERE id = ?').get(result.lastInsertRowid);
    
    return NextResponse.json(newTodo, { status: 201 });
  } catch {
    return NextResponse.json({ error: 'Failed to create todo' }, { status: 500 });
  }
}
