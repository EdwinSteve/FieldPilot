import type { ComponentProps, ReactNode } from "react";

type Variant = "primary" | "outline" | "needs" | "undo" | "stop";
type Size = "compact" | "main" | "large" | "extraLarge";

const VARIANTS: Record<Variant, string> = {
  primary: "border-0 bg-primary text-surface hover:bg-primary-hover",
  outline: "border-2 border-border bg-surface text-ink",
  needs: "border-0 bg-needs text-surface",
  undo: "border-0 bg-undo text-surface",
  stop: "border-0 bg-stop text-surface",
};

const SIZES: Record<Size, string> = {
  compact: "min-h-16 rounded-control text-row",
  main: "min-h-16 rounded-control text-key",
  large: "min-h-18 rounded-button text-key",
  extraLarge: "min-h-19 rounded-button text-key-lg",
};

function actionClass(variant: Variant, size: Size): string {
  return `flex items-center justify-center gap-2.5 font-extrabold no-underline disabled:cursor-not-allowed disabled:border-0 disabled:bg-divider disabled:text-ink-3 ${VARIANTS[variant]} ${SIZES[size]}`;
}

interface StyleProps {
  variant: Variant;
  size?: Size;
  children: ReactNode;
}

/** A main action. Never under 64 px tall. */
export function BigButton({
  variant,
  size = "main",
  children,
  ...button
}: StyleProps & Omit<ComponentProps<"button">, "className">) {
  return (
    <button type="button" className={actionClass(variant, size)} {...button}>
      {children}
    </button>
  );
}

/** A main action that opens a screen. */
export function BigLink({
  variant,
  size = "main",
  children,
  ...link
}: StyleProps & Omit<ComponentProps<"a">, "className">) {
  return (
    <a className={actionClass(variant, size)} {...link}>
      {children}
    </a>
  );
}
