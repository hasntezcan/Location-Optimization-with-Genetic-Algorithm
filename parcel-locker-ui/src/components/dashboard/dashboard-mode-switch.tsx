"use client";

export type DashboardMode = "user" | "dev";

export type DashboardModeSwitchProps = {
  mode: DashboardMode;
  onModeChange: (mode: DashboardMode) => void;
};

const modes: Array<{ value: DashboardMode; label: string }> = [
  { value: "user", label: "Kullanıcı Modu" },
  { value: "dev", label: "Geliştirici Modu" },
];

export function DashboardModeSwitch({ mode, onModeChange }: DashboardModeSwitchProps) {
  return (
    <div className="inline-flex rounded-xl border border-slate-200 bg-slate-50 p-1 shadow-sm">
      {modes.map((item) => {
        const isActive = item.value === mode;

        return (
          <button
            key={item.value}
            type="button"
            onClick={() => onModeChange(item.value)}
            className={`rounded-lg px-4 py-2 text-xs font-bold transition ${
              isActive
                ? "bg-slate-950 text-white shadow-sm"
                : "text-slate-500 hover:bg-white hover:text-slate-900"
            }`}
            aria-pressed={isActive}
          >
            {item.label}
          </button>
        );
      })}
    </div>
  );
}
