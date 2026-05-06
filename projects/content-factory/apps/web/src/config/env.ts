import { z } from "zod";

const apiBaseUrlSchema = z.string().min(1).refine(
  (value) => value.startsWith("/") || /^https?:\/\//.test(value),
  {
    message: "VITE_API_BASE_URL must be an absolute URL or a root-relative path",
  },
);

const webEnvSchema = z.object({
  VITE_API_BASE_URL: apiBaseUrlSchema.default("/"),
  VITE_APP_NAME: z.string().min(1).default("Content Factory Control Plane"),
});

export type WebEnv = z.infer<typeof webEnvSchema>;

export function parseWebEnv(rawEnv: Record<string, string | undefined>): WebEnv {
  return webEnvSchema.parse(rawEnv);
}

export const webEnv = parseWebEnv({
  VITE_API_BASE_URL: import.meta.env.VITE_API_BASE_URL,
  VITE_APP_NAME: import.meta.env.VITE_APP_NAME,
});
