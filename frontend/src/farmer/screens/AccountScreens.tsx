import { useRef, useState, type FormEvent, type ReactNode, type RefObject } from "react";
import { useResource } from "../../hooks/useResource";
import { lifecycle } from "../api/lifecycle";
import logo from "../assets/logo.webp";
import { BigButton } from "../components/BigButton";
import { Icon } from "../components/Icon";
import { PasswordField, SelectField, TextField } from "../components/TextField";
import type { SessionControl } from "../hooks/useSession";
import { en } from "../i18n/en";
import {
  colombianMobile,
  consentProblem,
  homeProblems,
  nameProblem,
  passwordAgainProblem,
  passwordMissing,
  passwordProblem,
  phoneProblem,
  type FieldProblem,
} from "../lib/account";
import { authFailure, type AuthFailure } from "../lib/authFailure";
import { departments, townsOf } from "../lib/places";
import { hrefOf } from "../lib/route";
import { MAX_PASSWORD, mobileDisplay, typedMobile, typedName } from "../lib/typing";

const SWITCH_LINK =
  "flex min-h-15 items-center justify-center text-center text-lead font-bold text-ink-2 underline";
/** Digits only, on the number pad; the box already shows +57. */
const PHONE_FIELD = {
  type: "tel",
  inputMode: "numeric",
  autoComplete: "tel-national",
  prefix: "+57",
  placeholder: en.auth.phoneExample,
} as const;
const PASSWORD_FIELD = { maxLength: MAX_PASSWORD } as const;
const DEPARTMENTS = departments();
const loadPolicy = () => lifecycle.privacyPolicy();

function words(problem: FieldProblem | null): string | null {
  return problem === null ? null : en.auth.problems[problem];
}

/** Focuses the first field with a problem; true when there was one. */
function focusFirstProblem(fields: [FieldProblem | null, RefObject<HTMLElement | null>][]) {
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
    </main>
  );
}

function FailureNote({ failure }: { failure: AuthFailure | null }) {
  if (failure === null) return null;
  return (
    <p
      role="alert"
      className="animate-notice-in rounded-control bg-needs-tint px-4 py-3 text-small font-bold text-needs-text"
    >
      {en.auth.failures[failure]}
    </p>
  );
}

interface ConsentProps {
  checked: boolean;
  onChange: (checked: boolean) => void;
  version: string | null;
  problem: string | null;
  ref: RefObject<HTMLInputElement | null>;
}

/** The privacy consent the backend records with the account (Ley 1581 de 2012, D082). */
function Consent({ checked, onChange, version, problem, ref }: ConsentProps) {
  return (
    <div className="flex flex-col gap-2">
      <label className="flex min-h-16 cursor-pointer items-start gap-3.5 rounded-control border-2 border-border bg-surface px-4 py-3.5">
        <input
          ref={ref}
          type="checkbox"
          checked={checked}
          aria-invalid={problem !== null}
          onChange={(event) => onChange(event.target.checked)}
          className="mt-0.5 size-7 shrink-0 accent-primary"
        />
        <span className="flex flex-col gap-1">
          <span className="text-body leading-snug">{en.auth.consent}</span>
          {version === null ? null : (
            <span className="text-caption text-ink-3">{en.auth.consentVersion(version)}</span>
          )}
        </span>
      </label>
      {problem === null ? null : (
        <p className="flex animate-notice-in items-center gap-2 px-0.5 text-small font-bold text-bad-text">
          <Icon name="warning" size={18} strokeWidth={2.4} className="shrink-0" />
          {problem}
        </p>
      )}
    </div>
  );
}

interface SignUpScreenProps {
  session: SessionControl;
  online: boolean;
}

export function SignUpScreen({ session, online }: SignUpScreenProps) {
  const [name, setName] = useState("");
  const [phone, setPhone] = useState("");
  const [password, setPassword] = useState("");
  const [again, setAgain] = useState("");
  const [department, setDepartment] = useState("");
  const [town, setTown] = useState("");
  const [consent, setConsent] = useState(false);
  // Read again after the backend says the policy changed.
  const [policyVersion, setPolicyVersion] = useState(0);
  const policy = useResource(loadPolicy, policyVersion).data?.version ?? null;
  // Problems show once the farmer tries to go on, then follow each change.
  const [tried, setTried] = useState(false);
  const [busy, setBusy] = useState(false);
  const [failure, setFailure] = useState<AuthFailure | null>(null);
  const nameRef = useRef<HTMLInputElement>(null);
  const phoneRef = useRef<HTMLInputElement>(null);
  const passwordRef = useRef<HTMLInputElement>(null);
  const againRef = useRef<HTMLInputElement>(null);
  const departmentRef = useRef<HTMLSelectElement>(null);
  const townRef = useRef<HTMLSelectElement>(null);
  const consentRef = useRef<HTMLInputElement>(null);
  const home = homeProblems(department, town);
  const problems = {
    name: nameProblem(name),
    phone: phoneProblem(phone),
    password: passwordProblem(password, phone),
    again: passwordAgainProblem(password, again, phone),
    department: home.department,
    town: home.town,
    consent: consentProblem(consent),
  };
  const shown = (problem: FieldProblem | null) => (tried ? words(problem) : null);

  const submit = async (event: FormEvent) => {
    event.preventDefault();
    setTried(true);
    setFailure(null);
    const blocked = focusFirstProblem([
      [problems.name, nameRef],
      [problems.phone, phoneRef],
      [problems.password, passwordRef],
      [problems.again, againRef],
      [problems.department, departmentRef],
      [problems.town, townRef],
      [problems.consent, consentRef],
    ]);
    if (blocked) return;
    if (policy === null) {
      setFailure(online ? "unreachable" : "offline");
      setPolicyVersion((v) => v + 1);
      return;
    }
    setBusy(true);
    try {
      const form = {
        phone: colombianMobile(phone) ?? phone,
        full_name: name.trim(),
        password,
        privacy_policy_version: policy,
      };
      await session.register(form, { department, town });
    } catch (caught) {
      const reason = authFailure(caught, navigator.onLine);
      setFailure(reason);
      if (reason === "policy_changed") {
        setConsent(false);
        setPolicyVersion((v) => v + 1);
      }
    } finally {
      setBusy(false);
    }
  };

  return (
    <AccountLayout title={en.auth.signUpTitle} lead={en.auth.signUpLead}>
      <FailureNote failure={failure} />
      <form noValidate onSubmit={(event) => void submit(event)} className="flex flex-col gap-4">
        <TextField
          ref={nameRef}
          label={en.auth.name}
          value={name}
          onChange={(value) => setName(typedName(value))}
          problem={shown(problems.name)}
          placeholder={en.auth.nameExample}
          autoComplete="name"
          autoCapitalize="words"
          enterKeyHint="next"
        />
        <TextField
          ref={phoneRef}
          label={en.auth.phone}
          hint={en.auth.phoneHint}
          value={mobileDisplay(phone)}
          onChange={(value) => setPhone(typedMobile(value))}
          problem={shown(problems.phone)}
          enterKeyHint="next"
          {...PHONE_FIELD}
        />
        <PasswordField
          ref={passwordRef}
          label={en.auth.password}
          hint={en.auth.passwordHint}
          value={password}
          onChange={setPassword}
          problem={shown(problems.password)}
          autoComplete="new-password"
          enterKeyHint="next"
          {...PASSWORD_FIELD}
        />
        <PasswordField
          ref={againRef}
          label={en.auth.passwordAgain}
          value={again}
          onChange={setAgain}
          problem={shown(problems.again)}
          autoComplete="new-password"
          enterKeyHint="next"
          {...PASSWORD_FIELD}
        />
        <fieldset className="flex flex-col gap-3 border-0 p-0">
          <legend className="px-0.5 pb-1 text-lead font-bold">{en.auth.home}</legend>
          <p className="-mt-1 px-0.5 text-caption leading-snug text-ink-3">{en.auth.homeHint}</p>
          <SelectField
            ref={departmentRef}
            label={en.auth.department}
            value={department}
            onChange={(value) => {
              setDepartment(value);
              setTown("");
            }}
            options={DEPARTMENTS}
            choose={en.auth.chooseDepartment}
            problem={shown(problems.department)}
            autoComplete="address-level1"
          />
          <SelectField
            ref={townRef}
            label={en.auth.town}
            value={town}
            onChange={setTown}
            options={townsOf(department)}
            choose={department === "" ? en.auth.chooseDepartmentFirst : en.auth.chooseTown}
            problem={shown(problems.town)}
            disabled={department === ""}
            autoComplete="address-level2"
          />
        </fieldset>
        <Consent
          ref={consentRef}
          checked={consent}
          onChange={setConsent}
          version={policy}
          problem={shown(problems.consent)}
        />
        <BigButton type="submit" variant="primary" size="large" disabled={busy}>
          {busy ? en.auth.creating : en.auth.create}
        </BigButton>
      </form>
      <a href={hrefOf({ screen: "login" })} className={SWITCH_LINK}>
        {en.auth.haveAccount}
      </a>
    </AccountLayout>
  );
}

interface LogInScreenProps {
  session: SessionControl;
}

export function LogInScreen({ session }: LogInScreenProps) {
  // A phone may be shared: the log-in never names or fills in whoever used it last.
  const [phone, setPhone] = useState("");
  const [password, setPassword] = useState("");
  const [tried, setTried] = useState(false);
  const [busy, setBusy] = useState(false);
  const [failure, setFailure] = useState<AuthFailure | null>(null);
  const phoneRef = useRef<HTMLInputElement>(null);
  const passwordRef = useRef<HTMLInputElement>(null);
  const problems = {
    phone: phoneProblem(phone),
    password: passwordMissing(password),
  };
  const edit = (set: (value: string) => void) => (value: string) => {
    set(value);
    if (failure !== null) setFailure(null);
  };

  const submit = async (event: FormEvent) => {
    event.preventDefault();
    setTried(true);
    setFailure(null);
    const blocked = focusFirstProblem([
      [problems.phone, phoneRef],
      [problems.password, passwordRef],
    ]);
    if (blocked) return;
    setBusy(true);
    try {
      await session.logIn(colombianMobile(phone) ?? phone, password);
    } catch (caught) {
      setFailure(authFailure(caught, navigator.onLine));
      setPassword("");
      passwordRef.current?.focus();
    } finally {
      setBusy(false);
    }
  };

  return (
    <AccountLayout
      title={en.auth.logInTitle}
      lead={en.auth.logInLead}
    >
      <FailureNote failure={failure} />
      <form noValidate onSubmit={(event) => void submit(event)} className="flex flex-col gap-4">
        <TextField
          ref={phoneRef}
          label={en.auth.phone}
          value={mobileDisplay(phone)}
          onChange={edit((value) => setPhone(typedMobile(value)))}
          problem={tried ? words(problems.phone) : null}
          enterKeyHint="next"
          {...PHONE_FIELD}
        />
        <PasswordField
          ref={passwordRef}
          label={en.auth.password}
          value={password}
          onChange={edit(setPassword)}
          problem={tried && failure === null ? words(problems.password) : null}
          autoComplete="current-password"
          enterKeyHint="done"
          {...PASSWORD_FIELD}
        />
        {/* Locked: the backend refuses for 15 minutes, so the button waits for a change. */}
        <BigButton
          type="submit"
          variant="primary"
          size="large"
          disabled={busy || failure === "locked"}
        >
          {busy ? en.auth.loggingIn : en.auth.logIn}
        </BigButton>
      </form>
      <a href={hrefOf({ screen: "signup" })} className={SWITCH_LINK}>
        {en.auth.newHere}
      </a>
    </AccountLayout>
  );
}
