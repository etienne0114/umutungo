# Umutungo web application

This Next.js application is the browser interface for the Umutungo API. It owns presentation and Supabase sign-in; API access is centralized in `src/lib/api/client.ts`. The browser must not connect directly to the application database.

## Local development

From this directory:

```bash
npm ci
npm run dev
```

`npm run dev` starts the API if needed, checks its health, and starts the frontend unless Umutungo is already serving on port 3000. It shuts down only the API process it started when Next.js exits. Next.js loads `apps/web/.env.local`; the API loads `apps/api/.env.local`. Set the Supabase project URL and publishable key in the web env file and `NEXT_PUBLIC_API_BASE_URL=http://127.0.0.1:8000`. Keep `NEXT_PUBLIC_AUTH_REQUIRED=true` so local approval checks match the API's Supabase token checks. If you prefer separate terminals, start the API from `apps/api` with `uvicorn govasset_api.main:app --reload --host 127.0.0.1 --port 8000` and run `npm run dev:web` from `apps/web`. Restart both dev servers after changing environment variables. Do not place a Supabase service-role key or database connection URL in frontend environment variables.

Email confirmation and password recovery redirect to `/auth/callback` on the same origin where the user started the flow. In Supabase Dashboard → Authentication → URL Configuration, keep the production site URL and add these redirect URLs to the allow list:

```text
http://localhost:*/**
http://127.0.0.1:*/**
https://umutungo7.vercel.app/**
https://umutungo-five.vercel.app/**
https://umutungo-etienne0114s-projects.vercel.app/**
https://umutungo-*-etienne0114s-projects.vercel.app/**
```

If Next.js selects another local port, add that exact localhost origin too. The callback exchanges Supabase's PKCE code, then returns the user to the same local or hosted app. Supabase will reject a confirmation redirect whose origin is not in the allow list.

If the email confirmation template builds a custom link from `{{ .SiteURL }}`, change it to use `{{ .RedirectTo }}` so it honors the local callback requested during registration. Keep the action URL secure by retaining Supabase's `{{ .ConfirmationURL }}` flow.

## Vercel

Create the Vercel project with the repository root directory set to `apps/web`. Add these environment variables for each environment that should be deployed:

| Variable | Value |
|---|---|
| `NEXT_PUBLIC_API_BASE_URL` | `https://umutungo.onrender.com` |
| `NEXT_PUBLIC_SUPABASE_URL` | Supabase project URL |
| `NEXT_PUBLIC_SUPABASE_PUBLISHABLE_KEY` | Supabase publishable key (safe for browser use) |

Configure the API's `CORS_ORIGINS` with the exact production and required preview origins. In Supabase Auth, enable email sign-up and configure the site's URL plus allowed redirect URLs listed above. Users can register and confirm their email, but an administrator must set trusted `app_metadata.govasset_access=approved` before API access is granted. Password recovery uses the same callback allow list.

Registration requires email confirmation in the current Supabase project. New and unapproved users can sign in, but the app shows an approval-pending screen until trusted `app_metadata.govasset_access=approved` is present in their session. After an administrator changes that claim, the user should sign out and sign back in to refresh their access token.

Signed-in users can edit their name, organization, department, and phone from the profile panel. These personal details are stored in the user's Supabase Auth `user_metadata`; only that user's own metadata can be changed from the browser. Access approval remains in trusted `app_metadata` and cannot be changed through the profile form.

Users with the trusted `app_metadata.govasset_role=admin` claim see a **User access** view. Administrators can search and filter registered accounts, load all account pages, approve confirmed users, and revoke access from other accounts. New accounts remain pending until an administrator approves them after email confirmation. After approval, users must sign out and back in to refresh their token claims before the API will grant access. The Supabase service-role key is server-only and must never be added to this frontend or any `NEXT_PUBLIC_*` setting.

The **Data quality** view summarizes asset-field coverage, service due counts, saved inspection/maintenance history, rule-based triage counts and recorded downtime. It also identifies roadmap data not captured by the application; it does not infer asset health or claim predictive performance. Approved users can export the existing asset, inspection and maintenance rows as CSV (up to 10,000 rows per export).

The frontend is currently available at `https://umutungo7.vercel.app`. The shorter `https://umutungo.vercel.app` alias is already in use by another Vercel deployment. Never paste access tokens into chat or commit them to this repository.
