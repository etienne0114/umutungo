"use client";

import { Dashboard } from "@/features/dashboard/dashboard";
import { AuthGate } from "@/features/auth/auth-gate";

export default function Home() {
  return (
    <AuthGate>
      {(user, signOut) => <Dashboard user={user} onSignOut={signOut} />}
    </AuthGate>
  );
}
