import { existsSync, mkdirSync, readFileSync, writeFileSync } from "node:fs";
import { dirname, resolve } from "node:path";

const outputPath = resolve("assets/supabase-env.js");
const localEnvPath = resolve(".env.local");

function readLocalEnv() {
  if (!existsSync(localEnvPath)) return {};

  return Object.fromEntries(
    readFileSync(localEnvPath, "utf8")
      .split(/\r?\n/)
      .map((line) => line.trim())
      .filter((line) => line && !line.startsWith("#") && line.includes("="))
      .map((line) => {
        const index = line.indexOf("=");
        return [line.slice(0, index), line.slice(index + 1)];
      }),
  );
}

const localEnv = readLocalEnv();
const supabaseUrl = process.env.NEXT_PUBLIC_SUPABASE_URL || localEnv.NEXT_PUBLIC_SUPABASE_URL || "";
const supabasePublishableKey =
  process.env.NEXT_PUBLIC_SUPABASE_PUBLISHABLE_KEY || localEnv.NEXT_PUBLIC_SUPABASE_PUBLISHABLE_KEY || "";

mkdirSync(dirname(outputPath), { recursive: true });

writeFileSync(
  outputPath,
  `window.ICS_SUPABASE_CONFIG = ${JSON.stringify(
    {
      url: supabaseUrl,
      publishableKey: supabasePublishableKey,
    },
    null,
    2,
  )};\n`,
);

if (!supabaseUrl || !supabasePublishableKey) {
  console.warn("Supabase env not set. Static app will load without a configured Supabase client.");
} else {
  console.log("Supabase static env generated.");
}
