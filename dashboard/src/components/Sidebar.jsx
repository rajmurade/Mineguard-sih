const SECTIONS = [
  { id: "overview", label: "Overview" },
  { id: "incidents", label: "Incidents" },
  { id: "environment", label: "Environment" },
  { id: "reports", label: "Reports" },
];

export default function Sidebar({ section, onSelect }) {
  const renderItem = (s) => {
    const active = section === s.id;
    return (
      <button
        key={s.id}
        onClick={() => onSelect(s.id)}
        className={`flex items-center gap-2.5 rounded-md px-3 py-2 text-xs font-medium tracking-wide transition-colors ${
          active
            ? "bg-cyan-500/10 text-cyan-300"
            : "text-slate-400 hover:bg-slate-800/50 hover:text-slate-200"
        }`}
      >
        <span
          className={`h-1.5 w-1.5 rounded-full ${active ? "bg-cyan-400" : "bg-slate-600"}`}
        />
        {s.label}
      </button>
    );
  };

  return (
    <>
      {/* desktop: fixed left rail */}
      <aside className="fixed inset-y-0 left-0 z-30 hidden w-48 flex-col border-r border-ops-border bg-ops-rail/80 md:flex">
        <div className="border-b border-ops-border px-4 py-4">
          <div className="font-mono text-sm font-bold tracking-widest text-cyan-300">
            MINEGUARD
          </div>
          <div className="mt-0.5 text-[9px] uppercase tracking-[0.3em] text-slate-500">
            Operations Center
          </div>
        </div>
        <nav className="flex flex-col gap-1 p-2">
          {SECTIONS.map(renderItem)}
        </nav>
        <div className="mt-auto border-t border-ops-border px-4 py-3">
          <div className="text-[9px] uppercase tracking-[0.3em] text-slate-600">
            ws /ws/alerts
          </div>
        </div>
      </aside>

      {/* mobile / tablet: horizontal section bar */}
      <nav className="border-b border-ops-border bg-ops-rail/60 md:hidden">
        <div className="mx-auto flex max-w-screen-2xl gap-1 px-2 py-1.5">
          {SECTIONS.map((s) => (
            <button
              key={s.id}
              onClick={() => onSelect(s.id)}
              className={`flex-1 rounded-md px-2 py-1.5 text-[11px] font-medium tracking-wide transition-colors ${
                section === s.id
                  ? "bg-cyan-500/10 text-cyan-300"
                  : "text-slate-400 hover:text-slate-200"
              }`}
            >
              {s.label}
            </button>
          ))}
        </div>
      </nav>
    </>
  );
}