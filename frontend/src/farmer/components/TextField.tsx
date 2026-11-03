import { useId, type ComponentProps, type Ref } from "react";
import { Icon } from "./Icon";

interface TextFieldProps
  extends Omit<ComponentProps<"input">, "className" | "onChange" | "id" | "ref"> {
  label: string;
  onChange: (value: string) => void;
  /** What is wrong with the value, in words; null while it is fine. */
  problem: string | null;
  ref?: Ref<HTMLInputElement>;
}

/** A labelled field with its problem said under it, never by colour alone. */
export function TextField({ label, onChange, problem, ref, ...input }: TextFieldProps) {
  const id = useId();
  const problemId = `${id}-problem`;
  return (
    <div className="flex flex-col gap-2">
      <label htmlFor={id} className="px-0.5 text-body font-bold text-ink-2">
        {label}
      </label>
      <input
        id={id}
        ref={ref}
        aria-invalid={problem !== null}
        aria-describedby={problem === null ? undefined : problemId}
        onChange={(event) => onChange(event.target.value)}
        className={`min-h-16 rounded-control border-2 bg-surface px-4 text-row text-ink ${
          problem === null ? "border-border" : "border-bad"
        }`}
        {...input}
      />
      {problem === null ? null : (
        <p
          id={problemId}
          className="flex animate-notice-in items-center gap-2 px-0.5 text-small font-bold text-bad-text"
        >
          <Icon name="warning" size={18} strokeWidth={2.4} className="shrink-0" />
          {problem}
        </p>
      )}
    </div>
  );
}
