import { describe, expect, test } from "vitest";
import { ZodError } from "zod";

import { parseWebEnv } from "./env";


describe("parseWebEnv", () => {
  test("uses bootstrap defaults when env is missing", () => {
    expect(parseWebEnv({})).toEqual({
      VITE_API_BASE_URL: "http://localhost:8000",
      VITE_APP_NAME: "Content Factory Control Plane",
    });
  });

  test("rejects malformed URLs", () => {
    expect(() => {
      parseWebEnv({
        VITE_API_BASE_URL: "not-a-url",
        VITE_APP_NAME: "Content Factory Control Plane",
      });
    }).toThrow(ZodError);
  });
});
