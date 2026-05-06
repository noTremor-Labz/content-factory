import { z } from "zod";

const webEnvSchema = z.object({
  VITE_API_BASE_URL: z.string().url().default("http://localhost:8000"),
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
