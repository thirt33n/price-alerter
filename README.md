# Amazon Price Tracker

Fully free, fully cloud. GitHub Actions does the scraping on a schedule,
GitHub Pages hosts the frontend, ntfy.sh sends push notifications.

## Setup (10 minutes)

### 1. Create the repo
- Create a new **public** GitHub repo (private also works, but Pages is easier on public + free tier).
- Upload all files from this folder, preserving structure:
  ```
  your-repo/
    .github/workflows/check.yml
    tracker.py
    tracked.json
    index.html
    README.md
  ```

### 2. Enable GitHub Pages
- Repo → Settings → Pages → Source: "Deploy from branch" → Branch: `main`, folder `/ (root)`.
- Your frontend will be live at `https://yourusername.github.io/your-repo/`.

### 3. Create a Personal Access Token
- GitHub → Settings → Developer settings → Personal access tokens → Fine-grained tokens (or classic).
- Scope: `repo` (or for fine-grained: Contents = Read and write, scoped to this repo).
- Copy the token — you'll paste it into the frontend once, it's saved in your browser's localStorage only.

### 4. Open the frontend
- Visit your GitHub Pages URL.
- Click "⚙️ GitHub settings", enter your username, repo name, and token. Save.
- Add a product: paste the Amazon URL, set a target price, and pick an ntfy topic name
  (make it random/unguessable, e.g. `mytracker-8f2k1`, since ntfy topics are public by default).

### 5. Subscribe to notifications
- Install the ntfy app (iOS/Android) or visit `https://ntfy.sh/<your-topic>` in browser.
- Subscribe to the same topic name you used in the form.

### 6. Verify it runs
- Repo → Actions tab → "Check Amazon Prices" → Run workflow (manual trigger) to test immediately.
- Otherwise it runs automatically every 30 minutes via cron.

## How it works
- `tracked.json` is your database — a simple list of `{name, url, target_price, ntfy_topic}`.
- The frontend commits new entries directly to `tracked.json` via the GitHub API.
- `.github/workflows/check.yml` runs `tracker.py` on a schedule, which:
  1. Loads `tracked.json`
  2. Scrapes each Amazon URL for current price
  3. If price ≤ target, POSTs a notification to `ntfy.sh/<topic>`
  4. Commits updated prices back to `tracked.json`

## Known limitations
- **Amazon blocks scrapers.** This uses plain requests + rotating User-Agents, which works
  intermittently. If it starts failing consistently, options:
  - Increase delay between requests
  - Route through a scraping API (e.g., ScraperAPI free tier: ~1000 req/month)
  - Reduce check frequency (edit the cron in `check.yml`)
- **ntfy topics are public.** Anyone who knows/guesses your topic name can subscribe. Use a
  long random string as the topic, not something guessable like "prices".
- GitHub Actions free tier: 2,000 minutes/month on private repos (unlimited on public repos).
  A 30-min cron checking a handful of products uses well under this.

## Customizing check frequency
Edit the cron line in `.github/workflows/check.yml`:
```yaml
schedule:
  - cron: '*/30 * * * *'   # every 30 min
  # - cron: '0 * * * *'    # every hour
  # - cron: '0 */6 * * *'  # every 6 hours
```
