import { requireUser } from "@/lib/auth";

import { SettingsForm } from "./SettingsForm";

export const metadata = { title: "Settings" };

export default async function SettingsPage() {
  const user = await requireUser();
  return (
    <div className="flex flex-col gap-8">
      <header className="flex flex-col gap-1">
        <h1 className="text-3xl font-semibold text-midnight">Settings</h1>
        <p className="text-sm text-slate">Manage how Beyond Borders shows up for you.</p>
      </header>
      <SettingsForm
        initial={{
          name: user.name,
          home_country: user.home_country ?? "",
          home_currency: user.home_currency,
          display_currency: user.display_currency,
        }}
      />
    </div>
  );
}