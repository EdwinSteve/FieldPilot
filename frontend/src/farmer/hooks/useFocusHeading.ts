import { useEffect, useRef, type RefObject } from "react";

/**
 * Moves focus to the first heading in `container` whenever `key` changes, so a
 * screen reader reads out the new screen. Never on the first render: a fresh
 * page starts at the top on its own.
 */
export function useFocusHeading(key: string, container: RefObject<HTMLElement | null>): void {
  const last = useRef(key);

  useEffect(() => {
    if (last.current === key) return;
    last.current = key;
    const heading = container.current?.querySelector("h1");
    if (!heading) return;
    heading.tabIndex = -1;
    heading.focus({ preventScroll: true });
  }, [key, container]);
}
