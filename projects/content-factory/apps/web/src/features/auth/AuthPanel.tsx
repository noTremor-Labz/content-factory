import { useState } from "react";

import type { InviteAcceptRequest, LoginRequest, BootstrapOwnerRequest } from "../../shared/api/types";

type AuthMode = "login" | "bootstrap" | "invite";

interface AuthPanelProps {
  appName: string;
  apiBaseLabel: string;
  busy: boolean;
  error: string | null;
  onLogin: (payload: LoginRequest) => Promise<void>;
  onBootstrapOwner: (payload: BootstrapOwnerRequest) => Promise<void>;
  onAcceptInvite: (payload: InviteAcceptRequest) => Promise<void>;
}

const authModes: Array<{ id: AuthMode; label: string; description: string }> = [
  {
    id: "login",
    label: "Login",
    description: "Use an existing owner, operator, reviewer, or viewer account.",
  },
  {
    id: "bootstrap",
    label: "Bootstrap owner",
    description: "Create the first owner once and start the initial control-plane session.",
  },
  {
    id: "invite",
    label: "Accept invite",
    description: "Turn an invite token into a working reviewer or operator account.",
  },
];

export function AuthPanel({
  appName,
  apiBaseLabel,
  busy,
  error,
  onLogin,
  onBootstrapOwner,
  onAcceptInvite,
}: AuthPanelProps) {
  const [mode, setMode] = useState<AuthMode>("login");
  const [loginForm, setLoginForm] = useState<LoginRequest>({
    email: "owner@inflave.test",
    password: "very-secure-password",
  });
  const [bootstrapForm, setBootstrapForm] = useState<BootstrapOwnerRequest>({
    email: "owner@inflave.test",
    display_name: "Owner",
    password: "very-secure-password",
  });
  const [inviteForm, setInviteForm] = useState<InviteAcceptRequest>({
    token: "",
    email: "",
    display_name: "",
    password: "",
  });

  return (
    <section className="auth-layout">
      <div className="auth-hero surface">
        <p className="eyebrow">Pilot cockpit</p>
        <h1>{appName}</h1>
        <p className="lede">
          Protected operator workspace for bootstrap, intake, planning, review, and audit.
          The current frontend slice talks directly to the control-plane API and keeps the
          workflow human-approved end to end.
        </p>

        <dl className="meta-list">
          <div>
            <dt>API target</dt>
            <dd>{apiBaseLabel}</dd>
          </div>
          <div>
            <dt>Current slice</dt>
            <dd>Phase 1 / Cockpit Shell And Review Queue</dd>
          </div>
        </dl>
      </div>

      <div className="auth-card surface">
        <div className="tab-row" role="tablist" aria-label="Authentication modes">
          {authModes.map((item) => (
            <button
              key={item.id}
              className={item.id === mode ? "tab active" : "tab"}
              onClick={() => setMode(item.id)}
              role="tab"
              type="button"
              aria-selected={item.id === mode}
            >
              {item.label}
            </button>
          ))}
        </div>

        <p className="panel-copy">{authModes.find((item) => item.id === mode)?.description}</p>

        {error ? (
          <p className="banner error" role="alert">
            {error}
          </p>
        ) : null}

        {mode === "login" ? (
          <form
            className="stack-form"
            onSubmit={async (event) => {
              event.preventDefault();
              await onLogin(loginForm);
            }}
          >
            <label>
              <span>Email</span>
              <input
                autoComplete="email"
                name="login-email"
                type="email"
                value={loginForm.email}
                onChange={(event) =>
                  setLoginForm((current) => ({ ...current, email: event.target.value }))
                }
              />
            </label>
            <label>
              <span>Password</span>
              <input
                autoComplete="current-password"
                name="login-password"
                type="password"
                value={loginForm.password}
                onChange={(event) =>
                  setLoginForm((current) => ({ ...current, password: event.target.value }))
                }
              />
            </label>
            <button className="primary-button" disabled={busy} type="submit">
              {busy ? "Signing in..." : "Sign in"}
            </button>
          </form>
        ) : null}

        {mode === "bootstrap" ? (
          <form
            className="stack-form"
            onSubmit={async (event) => {
              event.preventDefault();
              await onBootstrapOwner(bootstrapForm);
            }}
          >
            <label>
              <span>Owner email</span>
              <input
                autoComplete="email"
                type="email"
                value={bootstrapForm.email}
                onChange={(event) =>
                  setBootstrapForm((current) => ({ ...current, email: event.target.value }))
                }
              />
            </label>
            <label>
              <span>Display name</span>
              <input
                autoComplete="name"
                value={bootstrapForm.display_name}
                onChange={(event) =>
                  setBootstrapForm((current) => ({ ...current, display_name: event.target.value }))
                }
              />
            </label>
            <label>
              <span>Password</span>
              <input
                autoComplete="new-password"
                type="password"
                value={bootstrapForm.password}
                onChange={(event) =>
                  setBootstrapForm((current) => ({ ...current, password: event.target.value }))
                }
              />
            </label>
            <button className="primary-button" disabled={busy} type="submit">
              {busy ? "Bootstrapping..." : "Create first owner"}
            </button>
          </form>
        ) : null}

        {mode === "invite" ? (
          <form
            className="stack-form"
            onSubmit={async (event) => {
              event.preventDefault();
              await onAcceptInvite(inviteForm);
            }}
          >
            <label>
              <span>Invite token</span>
              <input
                value={inviteForm.token}
                onChange={(event) =>
                  setInviteForm((current) => ({ ...current, token: event.target.value }))
                }
              />
            </label>
            <label>
              <span>Email</span>
              <input
                autoComplete="email"
                type="email"
                value={inviteForm.email}
                onChange={(event) =>
                  setInviteForm((current) => ({ ...current, email: event.target.value }))
                }
              />
            </label>
            <label>
              <span>Display name</span>
              <input
                autoComplete="name"
                value={inviteForm.display_name}
                onChange={(event) =>
                  setInviteForm((current) => ({ ...current, display_name: event.target.value }))
                }
              />
            </label>
            <label>
              <span>Password</span>
              <input
                autoComplete="new-password"
                type="password"
                value={inviteForm.password}
                onChange={(event) =>
                  setInviteForm((current) => ({ ...current, password: event.target.value }))
                }
              />
            </label>
            <button className="primary-button" disabled={busy} type="submit">
              {busy ? "Accepting..." : "Accept invite"}
            </button>
          </form>
        ) : null}
      </div>
    </section>
  );
}
