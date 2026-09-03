Project 00: Dynamic TODO Workspace

WHAT IT IS
A task manager web app. Built with Next.js and React. Tasks are stored in a real SQLite database on disk (not in memory), and the screen updates instantly using optimistic UI updates and small Framer Motion animations.

HOW TO RUN
Command: make 00   (or ./run --00)
Opens at: http://localhost:3000

FILES TO SHOW ON SCREEN
1. src/lib/db.ts - sets up the SQLite database and tables
2. src/app/page.tsx - the main page, loads todos and renders them

CODE - src/lib/db.ts (database setup)

import Database from 'better-sqlite3';
import path from 'path';

const dbPath = path.join(process.cwd(), 'todos.db');
const db = new Database(dbPath);

db.exec(`
  CREATE TABLE IF NOT EXISTS todos (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    title TEXT NOT NULL,
    category TEXT DEFAULT 'Personal',
    priority TEXT DEFAULT 'Medium',
    completed INTEGER DEFAULT 0,
    dueDate TEXT,
    createdAt TEXT DEFAULT CURRENT_TIMESTAMP,
    status TEXT DEFAULT 'To Do'
  );
`);

CODE - src/app/page.tsx (main page, server component)

export default async function Home() {
  const todos = getTodosWithSubtasks();
  const open = todos.filter((t) => t.completed === 0).length;

  return (
    <>
      <PageHeader title="List" subtitle={...} />
      <TodoList initialTodos={todos} />
    </>
  );
}

SCRIPT

Intro, 0:00 to 0:20
Say you are showing Project 00, the dynamic TODO workspace.
Launch it with make 00.
Mention this starts the Next.js dev server on localhost port 3000.

Live demo, 0:20 to 0:50
Add a new task, mark one complete, filter by category.
Point out the small animation when items are added or removed.
Explain that every action updates the screen right away, before the server even finishes responding. That is the optimistic update.

Code walkthrough, 0:50 to 1:20
Open src/lib/db.ts.
Explain this file creates the SQLite database file and the todos table the first time the app runs, so data survives restarts.
Open src/app/page.tsx.
Explain this is a server component. It reads directly from SQLite on the server, then passes the data down to the TodoList component for rendering.

Wrap up
Say that because tasks live in a real database file instead of memory, nothing is lost on refresh or restart. This concludes Project 00.
