import { createClient } from "https://esm.sh/@supabase/supabase-js@2";

const config = window.ICS_SUPABASE_CONFIG || {};

export function getSupabaseClient() {
  if (!config.url || !config.publishableKey) {
    throw new Error("Supabase belum dikonfigurasi. Set NEXT_PUBLIC_SUPABASE_URL dan NEXT_PUBLIC_SUPABASE_PUBLISHABLE_KEY.");
  }

  return createClient(config.url, config.publishableKey, {
    auth: {
      persistSession: true,
      autoRefreshToken: true,
      detectSessionInUrl: true,
    },
  });
}

window.ICS_SUPABASE = {
  getClient: getSupabaseClient,
};
