import type { Bands } from "@rekalled/api-client";

/** Memory score 0–1 shown as a percentage; "new" when nothing has been reviewed yet. */
export function Score({ value, size = "md" }: { value: number | null; size?: "md" | "lg" }) {
  const text = value === null ? "new" : `${Math.round(value * 100)}%`;
  const tone =
    value === null
      ? "text-ink-soft"
      : value >= 0.9
        ? "text-strong"
        : value >= 0.75
          ? "text-fading"
          : "text-red";
  return (
    <span
      className={`font-display font-semibold ${tone} ${size === "lg" ? "text-4xl" : "text-lg"}`}
    >
      {text}
    </span>
  );
}

export function BandsBar({ bands }: { bands: Bands }) {
  const total = bands.strong + bands.fading + bands.weak + bands.new || 1;
  const parts = [
    ["bg-strong", bands.strong, "strong"],
    ["bg-fading", bands.fading, "fading"],
    ["bg-red", bands.weak, "weak"],
    ["bg-line", bands.new, "new"],
  ] as const;
  return (
    <div>
      <div className="flex h-2 overflow-hidden rounded-full bg-line">
        {parts.map(([cls, n, label]) => (
          <div key={label} className={cls} style={{ width: `${(n / total) * 100}%` }} />
        ))}
      </div>
      <p className="mt-2 text-xs text-ink-soft">
        {parts.map(([, n, label]) => `${n} ${label}`).join(" · ")}
      </p>
    </div>
  );
}
