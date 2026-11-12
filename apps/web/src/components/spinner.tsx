/** The 28px ring spinner from the prototype (.spinner). Decorative: aria-hidden. */
export function Spinner() {
  return (
    <div
      aria-hidden="true"
      className="h-7 w-7 animate-spin rounded-full border-2 border-line border-t-ink"
    />
  );
}
