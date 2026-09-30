# Umutungo web application

This Next.js application is the browser interface for the Umutungo API. It owns presentation and Supabase sign-in; API access is centralized in `src/lib/api/client.ts`. The browser must not connect directly to the application database.

## Local development

From this directory:

```bash
npm ci
npm run dev
```

Next.js automatically loads `apps/web/.env.local` in development. Set the Supabase project URL and publishable key there, and set `NEXT_PUBLIC_API_BASE_URL=http://127.0.0.1:8000` to use the local API. Start that separately from `apps/api` with `uvicorn govasset_api.main:app --reload --host 127.0.0.1 --port 8000 --env-file .env.local`. Do not place a Supabase service-role key or database connection URL in frontend environment variables.

## Vercel

Create the Vercel project with the repository root directory set to `apps/web`. Add these environment variables for each environment that should be deployed:

| Variable | Value |
|---|---|
| `NEXT_PUBLIC_API_BASE_URL` | `https://umutungo.onrender.com` |
| `NEXT_PUBLIC_SUPABASE_URL` | Supabase project URL |
| `NEXT_PUBLIC_SUPABASE_PUBLISHABLE_KEY` | Supabase publishable key (safe for browser use) |

Configure the API's `CORS_ORIGINS` with the exact production and required preview origins. In Supabase Auth, enable email sign-up and configure the site's URL plus allowed redirect URLs for the selected Vercel domains. Users can register and confirm their email, but an administrator must set trusted `app_metadata.govasset_access=approved` before API access is granted. Configure the same allowed redirect URLs for password recovery.

Signed-in users can edit their name, organization, department, and phone from the profile panel. These personal details are stored in the user's Supabase Auth `user_metadata`; only that user's own metadata can be changed from the browser. Access approval remains in trusted `app_metadata` and cannot be changed through the profile form.

The frontend is currently available at `https://umutungo7.vercel.app`. The shorter `https://umutungo.vercel.app` alias is already in use by another Vercel deployment. Never paste access tokens into chat or commit them to this repository.
