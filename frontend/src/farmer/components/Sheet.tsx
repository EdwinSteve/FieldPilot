import { useEffect, useRef, type ReactNode } from "react";

interface SheetProps {
  label: string;
  onClose: () => void;
  children: ReactNode;
}

/**
 * A panel sliding up from the bottom. It is modal: focus stays inside, and
 * Escape or a tap on the dimmed page closes it.
 */
export function Sheet({ label, onClose, children }: SheetProps) {
  const dialog = useRef<HTMLDialogElement>(null);

  useEffect(() => {
    const element = dialog.current;
    if (element === null) return undefined;
    if (!element.open) element.showModal();
    return () => element.close();
  }, []);

  return (
    // The dialog itself is hit only outside its panel: that tap is the way out by touch.
    // oxlint-disable-next-line jsx-a11y/click-events-have-key-events, jsx-a11y/no-noninteractive-element-interactions
    <dialog
      ref={dialog}
      aria-label={label}
      onCancel={(event) => {
        event.preventDefault();
        onClose();
      }}
      onClick={(event) => {
        if (event.target === event.currentTarget) onClose();
      }}
      className="m-0 mx-auto mt-auto max-h-[90dvh] w-full max-w-[430px] animate-sheet-up rounded-t-sheet border-0 bg-surface p-0 text-ink backdrop:animate-fade-in backdrop:bg-overlay"
    >
      <div className="flex flex-col gap-3.5 px-5 pt-3.5 pb-[calc(1.75rem+env(safe-area-inset-bottom))]">
        <span className="h-1.25 w-12 self-center rounded-full bg-border" />
        {children}
      </div>
    </dialog>
  );
}
