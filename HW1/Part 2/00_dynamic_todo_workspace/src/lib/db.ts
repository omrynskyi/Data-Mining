import Database from 'better-sqlite3';
import path from 'path';

// Connect to a local SQLite database file in the project root
const dbPath = path.join(process.cwd(), 'todos.db');
const db = new Database(dbPath);

// Initialize the database with the todos table if it doesn't exist
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
  
  CREATE TABLE IF NOT EXISTS subtasks (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    todo_id INTEGER NOT NULL,
    title TEXT NOT NULL,
    completed INTEGER DEFAULT 0,
    createdAt TEXT DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (todo_id) REFERENCES todos(id) ON DELETE CASCADE
  );
`);

// Try to add the columns if they don't exist (for existing databases)
try {
  db.exec(`ALTER TABLE todos ADD COLUMN status TEXT DEFAULT 'To Do';`);
} catch {
  // Column already exists on databases created before this migration.
}

try {
  db.exec(`ALTER TABLE todos ADD COLUMN tags TEXT DEFAULT '[]';`);
} catch {
  // Column already exists on databases created before this migration.
}

try {
  db.exec(`ALTER TABLE todos ADD COLUMN completedAt TEXT;`);
} catch {
  // Column already exists on databases created before this migration.
}

export interface Todo {
  id: number;
  title: string;
  category: string;
  priority: string;
  completed: number;
  dueDate: string | null;
  createdAt: string;
  status: string;
  tags?: string;
  completedAt?: string | null;
  subtasks?: Subtask[];
}

export interface Subtask {
  id: number;
  todo_id: number;
  title: string;
  completed: number;
  createdAt: string;
}

/** Todos newest-first with their subtasks attached, shared by the views. */
export function getTodosWithSubtasks(where = ''): Todo[] {
  const todos = db
    .prepare(`SELECT * FROM todos ${where} ORDER BY createdAt DESC`)
    .all() as Todo[];
  const subtasksFor = db.prepare(
    'SELECT * FROM subtasks WHERE todo_id = ? ORDER BY createdAt ASC'
  );
  return todos.map((todo) => ({
    ...todo,
    subtasks: subtasksFor.all(todo.id) as Subtask[],
  }));
}

export default db;
