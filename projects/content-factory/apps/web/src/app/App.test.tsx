import { render, screen } from "@testing-library/react";
import { describe, expect, test } from "vitest";

import { App } from "./App";

describe("App", () => {
  test("renders the phase bootstrap heading", () => {
    render(<App />);

    expect(screen.getByRole("heading", { name: /content factory control plane/i })).toBeVisible();
    expect(screen.getByText(/workspace bootstrap and shared tooling/i)).toBeVisible();
  });
});
