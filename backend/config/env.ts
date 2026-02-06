import dotenv from "dotenv";
import path from "path";

dotenv.config({ path: path.resolve(__dirname, "..", ".env") });

export interface AppConfig {
  /** Azure Maps subscription key for route/matrix API calls */
  azureMapsSubscriptionKey: string;
  /** Base URL for Azure Maps REST API (v1) */
  azureMapsBaseUrl: string;
  /** Port the Express server listens on */
  port: number;
  /** Allowed CORS origins (comma-separated) */
  corsOrigins: string[];
}

function requireEnv(name: string, fallback?: string): string {
  const value = process.env[name] ?? fallback;
  if (!value) {
    throw new Error(
      `Missing required environment variable: ${name}. ` +
        `Set it in your .env file or as a system environment variable.`
    );
  }
  return value;
}

export const config: AppConfig = {
  azureMapsSubscriptionKey: requireEnv("AZURE_MAPS_SUBSCRIPTION_KEY", ""),
  azureMapsBaseUrl: requireEnv(
    "AZURE_MAPS_BASE_URL",
    "https://atlas.microsoft.com"
  ),
  port: parseInt(requireEnv("PORT", "4000"), 10),
  corsOrigins: requireEnv("CORS_ORIGINS", "http://localhost:3000")
    .split(",")
    .map((o) => o.trim()),
};
