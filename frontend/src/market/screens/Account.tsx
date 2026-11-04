import { useEffect, useState } from "react";
import { BigButton, BigLink } from "../../farmer/components/BigButton";
import { Icon } from "../../farmer/components/Icon";
import { PasswordField, TextField } from "../../farmer/components/TextField";
import { en as farmerEn } from "../../farmer/i18n/en";
import {
  colombianMobile,
  consentProblem,
  nameProblem,
  passwordAgainProblem,
  passwordMissing,
  passwordProblem,
  phoneProblem,
  type FieldProblem,
} from "../../farmer/lib/account";
import { authFailure, type AuthFailure } from "../../farmer/lib/authFailure";
import { mobileDisplay, typedMobile, typedName } from "../../farmer/lib/typing";
import { getJson } from "../../api/client";
import { session } from "../api/session";
import { store } from "../api/store";
import { Notice } from "../components";
import { en } from "../i18n/en";
import { hrefOf } from "../lib/route";
import { canRunWarehouse } from "../lib/storedUser";
import { showToast, useUser } from "../state";

const words = (problem: FieldProblem | null) => (problem === null ? null : farmerEn.auth.problems[problem]);

function LogIn({ onCreate }: { onCreate: () => void }) {
  const [phone, setPhone] = useState("");
  const [password, setPassword] = useState("");
  const [tried, setTried] = useState(false);
  const [busy, setBusy] = useState(false);
  const [failure, setFailure] = useState<AuthFailure | null>(null);
  const problems = { phone: phoneProblem(phone), password: passwordMissing(password) };
  const submit = async () => {
    setTried(true);
    setFailure(null);
    const mobile = colombianMobile(phone);
    if (mobile === null || problems.password !== null) return;
    setBusy(true);
    try {
      const user = await session.logIn(mobile, password);
      showToast({ tone: "good", text: en.toast.loggedIn(user.name) });
      window.location.hash = canRunWarehouse(user.role) ? hrefOf({ screen: "warehouse" }) : hrefOf({ screen: "shop" });
    } catch (caught) {
      setFailure(authFailure(caught, navigator.onLine));
    } finally {
      setBusy(false);
    }
  };
  return (
    <form
      className="flex flex-col gap-4"
      onSubmit={(event) => {
        event.preventDefault();
        void submit();
      }}
    >
      <h1 className="text-title font-extrabold tracking-title">{en.account.logIn}</h1>
      <TextField
        label={en.account.phone}
        prefix="+57"
        value={mobileDisplay(phone)}
        onChange={(value) => setPhone(typedMobile(value))}
        problem={tried ? words(problems.phone) : null}
        inputMode="tel"
        autoComplete="tel-national"
      />
      <PasswordField
        label={en.account.password}
        value={password}
        onChange={setPassword}
        problem={tried ? words(problems.password) : null}
        autoComplete="current-password"
      />
      {failure === null ? null : <Notice text={farmerEn.auth.failures[failure]} />}
      <BigButton variant="primary" disabled={busy} onClick={() => void submit()}>
        {busy ? en.account.loggingIn : en.account.logIn}
      </BigButton>
      <button type="button" onClick={onCreate} className="press min-h-12 border-0 bg-transparent text-body font-bold text-primary">
        {en.account.newHere}
      </button>
    </form>
  );
}

const loadPolicy = () => getJson<{ version: string }>("/auth/privacy-policy");

function CreateAccount({ onLogIn }: { onLogIn: () => void }) {
  const [name, setName] = useState("");
  const [phone, setPhone] = useState("");
  const [password, setPassword] = useState("");
  const [again, setAgain] = useState("");
  const [consent, setConsent] = useState(false);
  const [tried, setTried] = useState(false);
  const [busy, setBusy] = useState(false);
  const [failure, setFailure] = useState<AuthFailure | null>(null);
  const problems = {
    name: nameProblem(name),
    phone: phoneProblem(phone),
    password: passwordProblem(password, phone),
    again: passwordAgainProblem(password, again, phone),
    consent: consentProblem(consent),
  };
  const submit = async () => {
    setTried(true);
    setFailure(null);
    const mobile = colombianMobile(phone);
    if (mobile === null || Object.values(problems).some((p) => p !== null)) return;
    setBusy(true);
    try {
      const { version } = await loadPolicy();
      await session.register({ phone: mobile, full_name: name.trim(), password, privacy_policy_version: version });
      showToast({ tone: "good", text: en.toast.created(name.trim()) });
      window.location.hash = hrefOf({ screen: "shop" });
    } catch (caught) {
      setFailure(authFailure(caught, navigator.onLine));
    } finally {
      setBusy(false);
    }
  };
  return (
    <form
      className="flex flex-col gap-4"
      onSubmit={(event) => {
        event.preventDefault();
        void submit();
      }}
    >
      <h1 className="text-title font-extrabold tracking-title">{en.account.create}</h1>
      <TextField label={en.account.name} value={name} onChange={(v) => setName(typedName(v))} problem={tried ? words(problems.name) : null} autoComplete="name" />
      <TextField
        label={en.account.phone}
        prefix="+57"
        value={mobileDisplay(phone)}
        onChange={(value) => setPhone(typedMobile(value))}
        problem={tried ? words(problems.phone) : null}
        inputMode="tel"
        autoComplete="tel-national"
      />
      <PasswordField
        label={en.account.password}
        hint={farmerEn.auth.passwordHint}
        value={password}
        onChange={setPassword}
        problem={tried ? words(problems.password) : null}
        autoComplete="new-password"
      />
      <PasswordField label={en.account.passwordAgain} value={again} onChange={setAgain} problem={tried ? words(problems.again) : null} autoComplete="new-password" />
      <label className="flex min-h-12 items-start gap-3 rounded-control bg-surface p-4">
        <input type="checkbox" checked={consent} onChange={(event) => setConsent(event.target.checked)} className="mt-1 size-6 shrink-0 accent-[var(--color-primary)]" />
        <span className="text-body">{en.account.consent}</span>
      </label>
      {tried && problems.consent !== null ? <Notice text={words(problems.consent) ?? ""} /> : null}
      {failure === null ? null : <Notice text={farmerEn.auth.failures[failure]} />}
      <BigButton variant="primary" disabled={busy} onClick={() => void submit()}>
        {busy ? en.account.creating : en.account.create}
      </BigButton>
      <button type="button" onClick={onLogIn} className="press min-h-12 border-0 bg-transparent text-body font-bold text-primary">
        {en.account.haveAccount}
      </button>
    </form>
  );
}

function Profile() {
  const [address, setAddress] = useState<string | null>(null);
  const [picks, setPicks] = useState(false);
  const [saving, setSaving] = useState<"idle" | "busy" | "saved" | "failed">("idle");
  /** An edit after a save: "Saved" no longer tells the truth. */
  const edit = <T,>(set: (value: T) => void) => (value: T) => {
    set(value);
    setSaving((current) => (current === "busy" ? current : "idle"));
  };
  useEffect(() => {
    void store
      .profile()
      .then((profile) => {
        setAddress(profile.delivery_address ?? "");
        setPicks(profile.consent_profiling);
      })
      .catch(() => setAddress(""));
  }, []);
  const save = async () => {
    setSaving("busy");
    try {
      await store.saveProfile({ delivery_address: (address ?? "").trim() || null, consent_profiling: picks });
      setSaving("saved");
    } catch {
      setSaving("failed");
    }
  };
  return (
    <section className="flex flex-col gap-4 rounded-card bg-surface p-5">
      <TextField label={en.account.address} hint={en.cart.addressHint} value={address ?? ""} onChange={edit(setAddress)} problem={null} autoComplete="street-address" />
      <label className="flex min-h-12 items-start gap-3" aria-label={en.account.picks}>
        <input type="checkbox" checked={picks} onChange={(event) => edit(setPicks)(event.target.checked)} className="mt-1 size-6 shrink-0 accent-[var(--color-primary)]" />
        <span className="flex flex-col">
          <span className="text-body font-bold">{en.account.picks}</span>
          <span className="text-small text-ink-2">{en.account.picksDetail}</span>
        </span>
      </label>
      {saving === "saved" ? <Notice tone="good" text={en.account.saved} /> : null}
      {saving === "failed" ? <Notice text={en.account.saveFailed} /> : null}
      <BigButton variant="primary" size="compact" disabled={saving === "busy"} onClick={() => void save()}>
        {saving === "busy" ? en.account.saving : en.account.save}
      </BigButton>
    </section>
  );
}

export function AccountPage() {
  const user = useUser();
  const [creating, setCreating] = useState(false);
  if (user === null) {
    return (
      <div className="mx-auto w-full max-w-md">
        {creating ? <CreateAccount onLogIn={() => setCreating(false)} /> : <LogIn onCreate={() => setCreating(true)} />}
      </div>
    );
  }
  return (
    <div className="mx-auto flex w-full max-w-xl flex-col gap-5">
      <header className="flex items-center gap-4">
        <span className="flex size-16 items-center justify-center rounded-full bg-tint text-head font-extrabold text-primary-hover">
          {user.name.trim().charAt(0).toUpperCase()}
        </span>
        <div className="flex flex-col">
          <h1 className="text-title-sm font-extrabold">{en.account.hello(user.name)}</h1>
          <span className="flex items-center gap-1.5 text-body text-ink-2">
            <Icon name="call" size={18} />
            {user.phone} · {en.account.role[user.role]}
          </span>
        </div>
      </header>
      {user.role === "customer" ? <Profile /> : null}
      {user.role === "farmer" ? (
        <section className="flex flex-col gap-3 rounded-card bg-surface p-5">
          <p className="text-body">{en.account.farmerHere}</p>
          <BigLink variant="primary" size="compact" href="/farmer">
            {en.account.openFarmerApp}
          </BigLink>
        </section>
      ) : null}
      <BigButton
        variant="outline"
        size="compact"
        onClick={() => void session.logOut().then(() => showToast({ tone: "good", text: en.toast.loggedOut }))}
      >
        <Icon name="logOut" size={22} />
        {en.account.signOut}
      </BigButton>
    </div>
  );
}
