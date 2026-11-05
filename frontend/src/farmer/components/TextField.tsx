import { useId, useState, type ComponentProps, type ReactNode, type Ref } from "react";
import { en } from "../i18n/en";
import { Icon } from "./Icon";

/** The box every field shares; the ring shows on the box, so a prefix and a button sit inside it. */
function boxClass(problem: string | null): string {
  return `flex min-h-16 items-center rounded-control border-2 bg-surface has-[:focus-visible]:outline-3 has-[:focus-visible]:outline-offset-2 has-[:focus-visible]:outline-undo ${
    problem === null ? "border-border" : "border-bad"
  }`;
}

interface FieldFrameProps {
  id: string;
  label: string;
  hint?: string;
  problem: string | null;
  children: (described: string | undefined) => ReactNode;
}

/** The label, the hint above the box and the problem under it, never said by colour alone. */
function FieldFrame({ id, label, hint, problem, children }: FieldFrameProps) {
  const problemId = `${id}-problem`;
  const hintId = `${id}-hint`;
  const described = [hint === undefined ? null : hintId, problem === null ? null : problemId]
    .filter((part) => part !== null)
    .join(" ");
  return (
    <div className="flex flex-col gap-2">
      <label htmlFor={id} className="px-0.5 text-body font-bold text-ink-2">
        {label}
      </label>
      {hint === undefined ? null : (
        <p id={hintId} className="-mt-1 px-0.5 text-caption leading-snug text-ink-3">
          {hint}
        </p>
      )}
      {children(described === "" ? undefined : described)}
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

interface TextFieldProps
  extends Omit<ComponentProps<"input">, "className" | "onChange" | "id" | "ref" | "prefix"> {
  label: string;
  onChange: (value: string) => void;
  /** What is wrong with the value, in words; null while it is fine. */
  problem: string | null;
  /** What the field wants, said before the farmer types. */
  hint?: string;
  /** Fixed text before the value, such as "+57". */
  prefix?: string;
  /** A button inside the box, after the value. */
  action?: ReactNode;
  ref?: Ref<HTMLInputElement>;
}

/** A labelled field with its problem said under it, never by colour alone. */
export function TextField({ label, onChange, problem, hint, prefix, action, ref, ...input }: TextFieldProps) {
  const id = useId();
  return (
    <FieldFrame id={id} label={label} hint={hint} problem={problem}>
      {(described) => (
        <div className={boxClass(problem)}>
          {prefix === undefined ? null : (
            <span aria-hidden="true" className="border-r-2 border-divider py-2 pr-3 pl-4 text-row font-bold text-ink-2">
              {prefix}
            </span>
          )}
          <input
            id={id}
            ref={ref}
            aria-invalid={problem !== null}
            aria-describedby={described}
            onChange={(event) => onChange(event.target.value)}
            className="min-h-15 min-w-0 flex-1 rounded-control border-0 bg-transparent px-4 text-row text-ink placeholder:text-ink-3 focus-visible:outline-none"
            {...input}
          />
          {action}
        </div>
      )}
    </FieldFrame>
  );
}

type PasswordFieldProps = Omit<TextFieldProps, "type" | "action" | "prefix">;

/** A password with Show and Hide, so the farmer can check what they typed. */
export function PasswordField(props: PasswordFieldProps) {
  const [shown, setShown] = useState(false);
  return (
    <TextField
      {...props}
      type={shown ? "text" : "password"}
      autoCapitalize="none"
      spellCheck={false}
      action={
        <button
          type="button"
          aria-pressed={shown}
          aria-label={shown ? en.auth.hidePasswordLabel : en.auth.showPasswordLabel}
          onClick={() => setShown((current) => !current)}
          className="press mr-1.5 flex min-h-12 min-w-12 shrink-0 items-center gap-1.5 rounded-chip border-0 bg-transparent px-2.5 text-small font-bold text-primary"
        >
          <Icon name={shown ? "eyeOff" : "eye"} size={22} />
          {shown ? en.auth.hidePassword : en.auth.showPassword}
        </button>
      }
    />
  );
}

interface SelectFieldProps extends Omit<ComponentProps<"select">, "className" | "onChange" | "id" | "ref"> {
  label: string;
  value: string;
  onChange: (value: string) => void;
  options: readonly string[];
  /** The first line, shown until something is chosen. */
  choose: string;
  problem: string | null;
  hint?: string;
  ref?: Ref<HTMLSelectElement>;
}

/** A choice from a list, in the phone's own picker: large, searchable by letter, and accessible. */
export function SelectField({ label, value, onChange, options, choose, problem, hint, ref, ...select }: SelectFieldProps) {
  const id = useId();
  return (
    <FieldFrame id={id} label={label} hint={hint} problem={problem}>
      {(described) => (
        <div className={`relative ${boxClass(problem)}`}>
          <select
            id={id}
            ref={ref}
            value={value}
            aria-invalid={problem !== null}
            aria-describedby={described}
            onChange={(event) => onChange(event.target.value)}
            className="min-h-15 w-full min-w-0 appearance-none rounded-control border-0 bg-transparent pr-12 pl-4 text-row text-ink focus-visible:outline-none disabled:text-ink-3"
            {...select}
          >
            <option value="">{choose}</option>
            {options.map((option) => (
              <option key={option} value={option}>
                {option}
              </option>
            ))}
          </select>
          <Icon
            name="chevronDown"
            size={22}
            strokeWidth={2.4}
            className="pointer-events-none absolute right-4 text-ink-2"
          />
        </div>
      )}
    </FieldFrame>
  );
}
