export function Section({
  title,
  action,
  children,
}: {
  title: string;
  action?: React.ReactNode;
  children: React.ReactNode;
}) {
  return (
    <section className="section">
      <div className="section-header">
        <div className="section-title">{title}</div>
        {action}
      </div>
      {children}
    </section>
  );
}