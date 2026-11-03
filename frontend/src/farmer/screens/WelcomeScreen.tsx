import logo from "../assets/logo.webp";
import { Icon } from "../components/Icon";
import { IconCircle } from "../components/IconCircle";
import { en } from "../i18n/en";

/** `startHref` is where Start leads: the farm, the log-in or a first account. */
export function WelcomeScreen({ startHref }: { startHref: string }) {
  return (
    <main className="flex h-full flex-col items-center gap-6 bg-ground-welcome px-6 pt-14 pb-10">
      <img src={logo} alt={en.welcome.logoAlt} className="h-auto w-75" />
      <p className="text-center text-key leading-normal font-semibold text-ink-2">
        {en.welcome.tagline[0]}
        <br />
        {en.welcome.tagline[1]}
      </p>
      <div className="flex justify-center gap-4.5" aria-hidden="true">
        <IconCircle tone="undo" size="welcome">
          <Icon name="drop" size={28} />
        </IconCircle>
        <IconCircle tone="good" size="welcome">
          <Icon name="satellite" size={28} />
        </IconCircle>
        <IconCircle tone="needs" size="welcome">
          <Icon name="mic" size={28} />
        </IconCircle>
      </div>
      <a
        href={startHref}
        className="mt-auto flex min-h-19 items-center justify-center gap-2.5 self-stretch rounded-start bg-primary text-key-lg font-extrabold text-surface no-underline hover:bg-primary-hover"
      >
        {en.welcome.start}
        <Icon name="forward" strokeWidth={2.8} />
      </a>
    </main>
  );
}
