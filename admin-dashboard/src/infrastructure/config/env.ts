import { z } from "zod";

const envSchema = z.object({
  NEXT_PUBLIC_API_BASE_URL: z.string().url(),
  NEXT_PUBLIC_STRIPE_PUBLIC_KEY: z.string().min(1),
});

export const env = envSchema.parse({
  NEXT_PUBLIC_API_BASE_URL: process.env.NEXT_PUBLIC_API_BASE_URL,
  NEXT_PUBLIC_STRIPE_PUBLIC_KEY: process.env.NEXT_PUBLIC_STRIPE_PUBLIC_KEY,
});
