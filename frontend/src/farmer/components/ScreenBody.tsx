import type { ReactNode } from "react";

interface ScreenBodyProps {
  children: ReactNode;
  /** A screen with a back header starts closer to the top. */
  underHeader?: boolean;
}

/** The scrolling area above the tab bar. */
export function ScreenBody({ children, underHeader = false }: ScreenBodyProps) {
  const top = underHeader ? "pt-2.5" : "pt-7";
  return (
    <main className={`flex min-h-0 flex-1 flex-col gap-3.5 overflow-y-auto px-4.5 pb-5 ${top}`}>
      {children}
    </main>
  );
}
