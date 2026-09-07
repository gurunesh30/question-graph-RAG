export interface Env {
  NEXT_PUBLIC_API_BASE?: string;
}

export const env: Env = {
  NEXT_PUBLIC_API_BASE: process.env.NEXT_PUBLIC_API_BASE,
};