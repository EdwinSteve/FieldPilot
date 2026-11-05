import { Icon, type IconName } from "./Icon";

/** A row of big choices, one pressed: the same look as the setup questions. */
export function Choices<T extends string | number>({
  options,
  chosen,
  label,
  icon,
  labelClass,
  onChoose,
}: {
  options: readonly T[];
  chosen: T | null;
  label: (option: T) => string;
  /** A picture before each label, so the choices are told apart at a glance. */
  icon?: (option: T) => IconName;
  /** The label's own text style, such as a bigger size for "Large". */
  labelClass?: (option: T) => string;
  onChoose: (option: T) => void;
}) {
  return (
    <div className="flex flex-wrap gap-2">
      {options.map((option) => (
        <button
          key={option}
          type="button"
          aria-pressed={option === chosen}
          onClick={() => onChoose(option)}
          className={`press flex min-h-12 min-w-20 items-center justify-center gap-1.5 rounded-control border-2 px-4 text-body font-bold ${
            option === chosen ? "border-primary bg-tint text-primary-hover" : "border-border bg-surface text-ink"
          }`}
        >
          {/* The tick: colour is never the only sign of the choice. */}
          {option === chosen ? (
            <Icon name="check" size={18} strokeWidth={3} className="animate-pop-in" />
          ) : null}
          {icon === undefined ? null : <Icon name={icon(option)} size={20} />}
          <span className={labelClass?.(option)}>{label(option)}</span>
        </button>
      ))}
    </div>
  );
}
