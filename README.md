# Deploy and Host Aurelio Finance on Railway

Aurelio Finance is an open-source wealth dashboard and financial-planning app with an optional AI advisor. Track banks, brokers, investments, real assets, debts, income, expenses and financial goals from one private workspace. This Railway Pro Stack adds a generated password, protected UI and API, and persistent SQLite storage to the original Aurelio application.

## About Hosting Aurelio Finance

The template builds the native React interface and FastAPI backend from a fixed upstream revision. One service runs them behind a private HTTPS gateway. SQLite, application records and settings are stored on an attached Railway volume. You can open and use the core application without creating an OpenRouter account or providing a model API key.

Aurelio is a single-user app. The deployment password protects the whole instance; it does not add separate users or roles. This is an independent Railway template, not an official hosted Aurelio product.

### What this Pro Stack adds

| Feature | Included behavior |
| --- | --- |
| Private access | Generated owner password for the web app and every API route |
| Secure browser session | HTTPS-only, HTTP-only session cookie and origin checks |
| Persistent records | SQLite database and saved settings on `/data` |
| Low-friction first launch | Core features start without an AI key |
| Optional AI advisor | Add your own OpenRouter key in Railway Variables |
| Reproducible deployment | Pinned source revision, verified source archive and frozen dependency locks |
| Real readiness check | `/healthz` checks the running application backend |

## Quick start

1. Deploy the template and wait for Railway to mark the service healthy.
2. Open the generated domain. Reveal `APP_PASSWORD` in the service's Railway Variables and use it on the login page.
3. Add an institution, then your own records. A new installation starts with an empty database; no invented portfolio is included.
4. To enable Ask Aurelio, optionally add `OPENROUTER_API_KEY` in Railway Variables and apply the deployment. Pick an available model in the app's chat.

No external PostgreSQL or Redis service is required. This template keeps the native SQLite backend, including Aurelio's database migrations and its pre-migration safety copies.

## Common Use Cases

- Follow personal net worth across financial accounts, property and liabilities.
- See portfolio allocation, instrument exposure and investment history.
- Record recurring income and expenses and review cash flow.
- Track savings goals and recurring investment plans.
- Ask the optional AI advisor questions about your records and review its proposed changes before confirming them.

## Configuration

| Variable | Purpose |
| --- | --- |
| `APP_PASSWORD` | Generated password; also works with HTTP Basic username `admin` |
| `SESSION_SECRET` | Generated signing secret for private browser sessions |
| `OPENROUTER_API_KEY` | Optional provider key for the AI chat and analysis |
| `PUBLIC_URL` | Automatic Railway HTTPS domain; update if you add a custom domain |
| `PORT` | Public ingress port, defaults to `8080` |

Keep provider keys and passwords in Railway Variables. Never put them into a public repository or this template's description. Setting a provider key enables requests to that provider, which can incur its normal charges. The AI features can send relevant records and prompts to OpenRouter and the selected model provider.

## Persistence, restarts and updates

The database is `/data/aurelio.db`. Authentication fallback state and configuration are under `/data/railway`, and the application's writable home is `/data/home`. All three are on the Railway volume mounted at `/data`.

Keep the volume attached during restarts and redeployments. Run one replica, since this is a single-node SQLite deployment. The launcher initializes volume permissions and then runs the application as an unprivileged user. Aurelio creates a safety copy before database migrations; those copies are separate from regular disaster-recovery backups. Configure Railway volume backups in your own project and keep an independent copy for important records.

The application is pinned to upstream revision `2be2ddb2b95dad0947314c818f952c3412e8e861`. Updates should be deliberate and tested against a backup. Deleting the Railway project or its volume deletes the stored records.

## FAQ

**Can I self-host Aurelio Finance on Railway?** Yes. This template includes the compiled frontend, native API, protected login and persistent database in one deployable service.

**Do I need OpenAI or Claude to launch it?** No. The core dashboard and record management work without an AI key. The optional advisor uses OpenRouter; supported models depend on OpenRouter availability and your account.

**Is Aurelio usable without an AI subscription?** Yes. Entering records and viewing the financial dashboard do not require an LLM subscription. Railway hosting still has its usual resource charges.

**Is my dashboard publicly readable?** No. The UI and APIs require authentication. The public `/healthz` route returns only a minimal readiness status. Anyone with your instance password has owner access to its records.

**Will records survive a Railway redeploy?** They are stored on the attached `/data` volume. Keep that volume when replacing the container. A volume is persistence, not an independent backup.

**Why choose this Aurelio Railway template?** It adapts a locally designed finance app for remote hosting with private access, automatic credentials, a persistent database and an optional AI setup. It avoids exposing the native unauthenticated API directly to the Internet.

## Dependencies for Aurelio Finance Hosting

### Deployment Dependencies

- A Railway service and persistent volume mounted at `/data`.
- [Aurelio Finance upstream source](https://github.com/LosaLosSantos/aurelio-finance).
- [Aurelio documentation](https://github.com/LosaLosSantos/aurelio-finance/wiki).
- [Railway template source](https://github.com/XavTo/Aurelio-Finance-Railway).
- Optional: your own [OpenRouter account](https://openrouter.ai/) for AI features.

## Why Deploy Aurelio Finance on Railway?

Railway manages the container, HTTPS domain, variables and persistent volume. The template supplies the built application, private ingress and database path configuration. Actual compute and storage costs depend on usage. External market-data coverage and model availability depend on their respective providers.
