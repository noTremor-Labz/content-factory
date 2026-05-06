import "./App.css";

import { webEnv } from "../config/env";

const services = [
  {
    label: "Web cockpit",
    status: "Ready for UI phases",
    detail: "React 19 + Vite baseline is wired with validation, tests, and linting.",
  },
  {
    label: "Control-plane API",
    status: "Health endpoints online",
    detail: "FastAPI now exports OpenAPI, validates env, and exposes readiness metadata.",
  },
  {
    label: "Worker runtime",
    status: "Bootstrap complete",
    detail: "Dramatiq broker wiring is present for later render and workflow jobs.",
  },
];

export function App() {
  return (
    <main className="shell">
      <section className="hero">
        <p className="eyebrow">Phase 1 bootstrap</p>
        <h1>{webEnv.VITE_APP_NAME}</h1>
        <p className="lede">
          Foundation and control-plane tooling are in place. The next slices can add auth,
          domain models, and review workflows without reworking the bootstrap.
        </p>
      </section>

      <section className="meta">
        <div>
          <span>API base URL</span>
          <strong>{webEnv.VITE_API_BASE_URL}</strong>
        </div>
        <div>
          <span>Current slice</span>
          <strong>Workspace Bootstrap And Shared Tooling</strong>
        </div>
      </section>

      <section className="grid" aria-label="Bootstrap services">
        {services.map((service) => (
          <article className="card" key={service.label}>
            <p className="card-label">{service.label}</p>
            <h2>{service.status}</h2>
            <p>{service.detail}</p>
          </article>
        ))}
      </section>
    </main>
  );
}
