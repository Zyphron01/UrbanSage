import { createClient } from "@supabase/supabase-js";

const supabaseUrl = process.env.NEXT_PUBLIC_SUPABASE_URL || "https://lrkjcavnvabqbrpjgpbq.supabase.co";
const supabaseAnonKey =
  process.env.NEXT_PUBLIC_SUPABASE_ANON_KEY ||
  "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6Imxya2pjYXZudmFicWJycGpncGJxIiwicm9sZSI6ImFub24iLCJpYXQiOjE3OTI3MzM1MzcsImV4cCI6MjEwODMwOTUzN30.xV-WajuX9FhVrjU-EhpqeDYLi2IzZr4J3gM-7qDly3s";

export const supabase = createClient(supabaseUrl, supabaseAnonKey, {
  auth: {
    persistSession: true,
    autoRefreshToken: true,
    detectSessionInUrl: true,
  },
});
