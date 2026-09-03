import type { LucideIcon } from 'lucide-react';

export default function EmptyState({
  icon: Icon,
  title,
  body,
  action,
}: {
  icon: LucideIcon;
  title: string;
  body: string;
  action?: React.ReactNode;
}) {
  return (
    <div className="empty">
      <span className="empty-icon" aria-hidden="true">
        <Icon size={20} strokeWidth={1.75} />
      </span>
      <p className="empty-title">{title}</p>
      <p className="empty-body">{body}</p>
      {action}
    </div>
  );
}
