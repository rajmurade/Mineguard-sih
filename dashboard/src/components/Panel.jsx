export default function Panel({ title, right, children, className = "" }) {
  return (
    <section className={`panel flex flex-col ${className}`}>
      <header className="flex items-center justify-between border-b border-ops-border px-3 py-2">
        <h2 className="panel-title">{title}</h2>
        {right}
      </header>
      <div className="min-h-0 flex-1">{children}</div>
    </section>
  );
}