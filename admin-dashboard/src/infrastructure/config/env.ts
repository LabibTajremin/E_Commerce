import { z } from "zod";

const envSchema = z.object({
  NEXT_PUBLIC_API_BASE_URL: z.string().url(),
  // Set when deployed without a wildcarded custom domain (e.g. bare Vercel
  // *.vercel.app domains) — there's no tenant subdomain to splice onto the
  // API host in that topology, so talk to the configured API origin
  // directly instead. See docs/DEPLOYMENT.md's no-custom-domain section.
  NEXT_PUBLIC_SINGLE_TENANT_MODE: z
    .string()
    .optional()
    .transform((v) => v === "true"),
});

export const env = envSchema.parse({
  NEXT_PUBLIC_API_BASE_URL: process.env.NEXT_PUBLIC_API_BASE_URL,
  NEXT_PUBLIC_SINGLE_TENANT_MODE: process.env.NEXT_PUBLIC_SINGLE_TENANT_MODE,
});
