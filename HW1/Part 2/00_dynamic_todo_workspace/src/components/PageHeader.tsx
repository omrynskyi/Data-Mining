export default function PageHeader({
  title,
  subtitle,
  actions,
}: {
  title: string;
  subtitle: string;
  actions?: React.ReactNode;
}) {
  return (
    <header className="page-head">
      <div>
        <h1 className="page-title">{title}</h1>
        <p className="page-sub">{subtitle}</p>
      </div>
      {actions}
    </header>
  );
}
