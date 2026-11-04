import icon from "../assets/icon-180.png";
import { Icon } from "../components/Icon";
import { IconCircle } from "../components/IconCircle";
import { Wordmark } from "../components/Wordmark";
import { en } from "../i18n/en";

/**
 * `startHref` is where Start leads: the farm, the log-in or a first account.
 * The logo comes first, then the words, then Start, so the eye follows one thing at a time.
 */
export function WelcomeScreen({ startHref }: { startHref: string }) {
  return (
    <main className="flex h-full flex-col items-center gap-6 bg-ground-welcome px-6 pt-14 pb-10">
      {/* The app's picture and its lettering, which follows dark mode: no light box around the logo. */}
      <div className="flex animate-logo-in flex-col items-center gap-4">
        <img src={icon} alt="" width={180} height={180} className="size-45 rounded-[40px] shadow-[0_12px_30px_rgb(21_39_40/0.18)]" />
        <Wordmark size="welcome" />
      </div>
      <p className="animate-rise text-center text-key leading-normal font-semibold text-ink-2 [animation-delay:450ms]">
        {en.welcome.tagline[0]}
        <br />
        {en.welcome.tagline[1]}
      </p>
      <div className="flex animate-rise justify-center gap-4.5 [animation-delay:650ms]" aria-hidden="true">
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
        className="press mt-auto flex min-h-19 animate-rise items-center justify-center gap-2.5 self-stretch rounded-start bg-primary text-key-lg font-extrabold text-surface no-underline transition-colors hover:bg-primary-hover [animation-delay:900ms]"
      >
        {en.welcome.start}
        <Icon name="forward" strokeWidth={2.8} />
      </a>
    </main>
  );
}
