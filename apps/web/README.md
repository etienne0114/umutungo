# Umutungo web application

This Next.js application is the browser interface for the Umutungo API. It owns presentation and Supabase sign-in; API access is centralized in `src/lib/api/client.ts`. The browser must not connect directly to the application database.

## Local development

From this directory:

```bash
npm ci
cp .env.example .env.local
npm run dev
```

Set the Supabase project URL and publishable key in `.env.local`, then configure the API's `CORS_ORIGINS` to allow the exact local frontend origin. Set `NEXT_PUBLIC_API_BASE_URL` to the API origin. Do not place a Supabase service-role key or database connection URL in frontend environment variables.

## Vercel

Create the Vercel project with the repository root directory set to `apps/web`. Add these environment variables for each environment that should be deployed:

| Variable | Value |
|---|---|
| `NEXT_PUBLIC_API_BASE_URL` | `https://umutungo.onrender.com` |
| `NEXT_PUBLIC_SUPABASE_URL` | Supabase project URL |
| `NEXT_PUBLIC_SUPABASE_PUBLISHABLE_KEY` | Supabase publishable key (safe for browser use) |

Configure the API's `CORS_ORIGINS` with the exact production and required preview origins. Configure Supabase Auth's allowed redirect URLs for the selected Vercel domains. Public self-registration should remain disabled; accounts are provisioned by an administrator and must have trusted `app_metadata.govasset_access=approved` to use the API.

The frontend is currently available at `https://umutungo7.vercel.app`. The shorter `https://umutungo.vercel.app` alias is already in use by another Vercel deployment. Never paste access tokens into chat or commit them to this repository.
