import { useRef, useState, type FormEvent, type ReactNode, type RefObject } from "react";
import logo from "../assets/logo.webp";
import { BigButton } from "../components/BigButton";
import { Icon } from "../components/Icon";
import { TextField } from "../components/TextField";
import { en } from "../i18n/en";
import {
  nameProblem,
  phoneProblem,
  pinAgainProblem,
  pinProblem,
  type Account,
  type FieldProblem,
  type LogInResult,
} from "../lib/account";
import { hrefOf } from "../lib/route";

const PIN_LENGTH = 4;
const SWITCH_LINK =
  "flex min-h-15 items-center justify-center text-center text-lead font-bold text-ink-2 underline";
const PIN_FIELD = {
  type: "password",
  inputMode: "numeric",
  maxLength: PIN_LENGTH,
  enterKeyHint: "next",
} as const;

function words(problem: FieldProblem | null): string | null {
  return problem === null ? null : en.auth.problems[problem];
}

/** Focuses the first field with a problem; true when there was one. */
function focusFirstProblem(fields: [FieldProblem | null, RefObject<HTMLInputElement | null>][]) {
  const first = fields.find(([problem]) => problem !== null);
  first?.[1].current?.focus();
  return first !== undefined;
}

function AccountLayout({
  title,
  lead,
  children,
}: {
  title: string;
  lead: string;
  children: ReactNode;
}) {
  return (
    <main className="flex min-h-0 flex-1 flex-col gap-4.5 overflow-y-auto bg-ground-welcome px-4.5 pt-8 pb-6">
      <img src={logo} alt={en.welcome.logoAlt} className="h-auto w-28 self-center" />
      <div className="flex flex-col gap-1 px-0.5">
        <h1 className="text-title font-extrabold tracking-title">{title}</h1>
        <span className="text-lead leading-snug text-ink-2">{lead}</span>
      </div>
      {children}
      <span className="flex items-center gap-2 px-1 text-caption leading-snug text-ink-3">
        <Icon name="info" size={18} className="shrink-0" />
        {en.auth.demoNote}
      </span>
    </main>
  );
}

interface SignUpScreenProps {
  /** The account already on this phone, which a new one replaces. */
  existing: Account | null;
  onSignUp: (name: string, phone: string, pin: string) => void;
}

export function SignUpScreen({ existing, onSignUp }: SignUpScreenProps) {
  const [name, setName] = useState("");
  const [phone, setPhone] = useState("");
  const [pin, setPin] = useState("");
  const [again, setAgain] = useState("");
  // Problems show once the farmer tries to go on, then follow each change.
  const [tried, setTried] = useState(false);
  const nameRef = useRef<HTMLInputElement>(null);
  const phoneRef = useRef<HTMLInputElement>(null);
  const pinRef = useRef<HTMLInputElement>(null);
  const againRef = useRef<HTMLInputElement>(null);
  const problems = {
    name: nameProblem(name),
    phone: phoneProblem(phone),
    pin: pinProblem(pin),
    again: pinAgainProblem(pin, again),
  };
  const shown = (problem: FieldProblem | null) => (tried ? words(problem) : null);

  const submit = (event: FormEvent) => {
    event.preventDefault();
    setTried(true);
    const blocked = focusFirstProblem([
      [problems.name, nameRef],
      [problems.phone, phoneRef],
      [problems.pin, pinRef],
      [problems.again, againRef],
    ]);
    if (!blocked) onSignUp(name, phone, pin);
  };

  return (
    <AccountLayout title={en.auth.signUpTitle} lead={en.auth.signUpLead}>
      {existing === null ? null : (
        <p className="rounded-control bg-needs-tint px-4 py-3 text-small font-bold text-needs-text">
          {en.auth.replaces(existing.name)}
        </p>
      )}
      <form noValidate onSubmit={submit} className="flex flex-col gap-4">
        <TextField
          ref={nameRef}
          label={en.auth.name}
          value={name}
          onChange={setName}
          problem={shown(problems.name)}
          autoComplete="name"
          enterKeyHint="next"
        />
        <TextField
          ref={phoneRef}
          label={en.auth.phone}
          value={phone}
          onChange={setPhone}
          problem={shown(problems.phone)}
          type="tel"
          inputMode="tel"
          autoComplete="tel"
          enterKeyHint="next"
        />
        <TextField
          ref={pinRef}
          label={en.auth.pin}
          value={pin}
          onChange={setPin}
          problem={shown(problems.pin)}
          autoComplete="new-password"
          {...PIN_FIELD}
        />
        <TextField
          ref={againRef}
          label={en.auth.pinAgain}
          value={again}
          onChange={setAgain}
          problem={shown(problems.again)}
          autoComplete="new-password"
          {...PIN_FIELD}
          enterKeyHint="done"
        />
        <BigButton type="submit" variant="primary" size="large">
          {en.auth.create}
        </BigButton>
      </form>
      {existing === null ? null : (
        <a href={hrefOf({ screen: "login" })} className={SWITCH_LINK}>
          {en.auth.haveAccount}
        </a>
      )}
    </AccountLayout>
  );
}

interface LogInScreenProps {
  account: Account | null;
  onLogIn: (phone: string, pin: string) => LogInResult;
}

export function LogInScreen({ account, onLogIn }: LogInScreenProps) {
  // One account per phone: its number is already known, so it starts filled in.
  const [phone, setPhone] = useState(account?.phone ?? "");
  const [pin, setPin] = useState("");
  const [tried, setTried] = useState(false);
  const [failure, setFailure] = useState<Exclude<LogInResult, "ok"> | null>(null);
  const phoneRef = useRef<HTMLInputElement>(null);
  const pinRef = useRef<HTMLInputElement>(null);
  const problems = { phone: phoneProblem(phone), pin: pinProblem(pin) };
  const pinWords = failure === "wrong" ? en.auth.wrong : tried ? words(problems.pin) : null;

  const submit = (event: FormEvent) => {
    event.preventDefault();
    setTried(true);
    setFailure(null);
    const blocked = focusFirstProblem([
      [problems.phone, phoneRef],
      [problems.pin, pinRef],
    ]);
    if (blocked) return;
    const result = onLogIn(phone, pin);
    if (result === "ok") return;
    setFailure(result);
    setPin("");
    pinRef.current?.focus();
  };

  return (
    <AccountLayout
      title={en.auth.logInTitle}
      lead={account === null ? en.auth.logInLeadNew : en.auth.logInLead(account.name)}
    >
      {failure === "no_account" ? (
        <p
          role="alert"
          className="animate-notice-in rounded-control bg-needs-tint px-4 py-3 text-small font-bold text-needs-text"
        >
          {en.auth.noAccount}
        </p>
      ) : null}
      <form noValidate onSubmit={submit} className="flex flex-col gap-4">
        <TextField
          ref={phoneRef}
          label={en.auth.phone}
          value={phone}
          onChange={(value) => {
            setPhone(value);
            setFailure(null);
          }}
          problem={tried ? words(problems.phone) : null}
          type="tel"
          inputMode="tel"
          autoComplete="tel"
          enterKeyHint="next"
        />
        <TextField
          ref={pinRef}
          label={en.auth.pin}
          value={pin}
          onChange={(value) => {
            setPin(value);
            setFailure(null);
          }}
          problem={pinWords}
          autoComplete="current-password"
          {...PIN_FIELD}
          enterKeyHint="done"
        />
        <BigButton type="submit" variant="primary" size="large">
          {en.auth.logIn}
        </BigButton>
      </form>
      <a href={hrefOf({ screen: "signup" })} className={SWITCH_LINK}>
        {account === null ? en.auth.newHere : en.auth.forgotPin}
      </a>
    </AccountLayout>
  );
}
