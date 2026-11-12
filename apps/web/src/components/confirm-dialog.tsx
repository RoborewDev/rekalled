import { useEffect, useRef } from "react";
import type { ReactNode } from "react";
import { X } from "lucide-react";

type ConfirmDialogProps = {
  title: string;
  children: ReactNode;
  confirmLabel: string;
  onConfirm: () => void;
  onDismiss: () => void;
  pending?: boolean;
};

/**
 * Modal confirmation, in the prototype's sheet language: dimmed scrim, card
 * surface, display-font heading. Escape, scrim click and the X all dismiss.
 */
export function ConfirmDialog({
  title,
  children,
  confirmLabel,
  onConfirm,
  onDismiss,
  pending = false,
}: ConfirmDialogProps) {
  const cancelRef = useRef<HTMLButtonElement>(null);
  const dialogRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    // Focus the safe choice, not the destructive one.
    cancelRef.current?.focus();
    const onKeyDown = (e: KeyboardEvent) => {
      if (e.key === "Escape") onDismiss();
      if (e.key === "Tab") {
        // Keep focus inside the dialog while it is modal.
        const focusable = dialogRef.current?.querySelectorAll<HTMLElement>(
          "button:not([disabled]), [href], input, select, textarea",
        );
        if (!focusable?.length) return;
        const first = focusable[0]!;
        const last = focusable[focusable.length - 1]!;
        if (e.shiftKey && document.activeElement === first) {
          e.preventDefault();
          last.focus();
        } else if (!e.shiftKey && document.activeElement === last) {
          e.preventDefault();
          first.focus();
        }
      }
    };
    window.addEventListener("keydown", onKeyDown);
    return () => window.removeEventListener("keydown", onKeyDown);
  }, [onDismiss]);

  return (
    <div
      className="fixed inset-0 z-50 flex items-center justify-center bg-ink/35 p-4"
      onClick={(e) => {
        if (e.target === e.currentTarget) onDismiss();
      }}
    >
      <div
        ref={dialogRef}
        role="dialog"
        aria-modal="true"
        aria-labelledby="confirm-dialog-title"
        className="panel w-full max-w-md space-y-4"
      >
        <div className="flex items-start justify-between gap-4">
          <h2 id="confirm-dialog-title" className="text-xl">
            {title}
          </h2>
          <button type="button" className="btn-icon" aria-label="Close" onClick={onDismiss}>
            <X aria-hidden="true" size={16} />
          </button>
        </div>
        <div className="space-y-2 text-sm text-ink-soft">{children}</div>
        <div className="flex justify-end gap-2">
          <button ref={cancelRef} type="button" className="btn-outline" onClick={onDismiss}>
            Cancel
          </button>
          <button type="button" className="btn-danger" disabled={pending} onClick={onConfirm}>
            {pending ? "Working…" : confirmLabel}
          </button>
        </div>
      </div>
    </div>
  );
}
