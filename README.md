# www.thearxfoundation.org (public monorepo)

Static site for **https://www.thearxfoundation.org/** — pitches, shells, and other **public** ARX Foundation material. Deployed by a **Cloudflare Worker** (static assets) that builds on every push to `main`.

**Canonical URL:** `https://www.thearxfoundation.org/`. The apex 301-redirects to `www` (Cloudflare redirect rule); `lander.thearxfoundation.org` serves the same Worker.

## Layout (grow here instead of losing stubs in temp)

- `index.html` — apex shell for the www host (light nav into sections below).
- `pitches/` — public pitch deck / narrative stubs (`pitches/index.html`).
- `contributor-projects.json` — machine-readable list of contributor-facing projects (empty array until you fill it).

Subdomains that need **private** builds, separate cadence, or gated deploys should stay **separate repos** with their own workflows (per your split plan).

## Serve locally

From this folder:

```powershell
python -m http.server 8765
```

Open http://127.0.0.1:8765/ and http://127.0.0.1:8765/pitches/

## GitHub

Remote: [The-ARX-Foundation/thearxfoundation.org](https://github.com/The-ARX-Foundation/thearxfoundation.org.git) — default branch **`main`**.

## Deploy (Cloudflare Worker)

The Worker is connected to this repo through **Workers Builds** in the Cloudflare dashboard (Workers & Pages → the Worker → Settings → Build). Every push to **`main`** builds and deploys it; there is no GitHub Actions workflow.

- Custom domains on the Worker: `www.thearxfoundation.org`, `thearxfoundation.org`, `lander.thearxfoundation.org`.
- `.assetsignore` keeps `tools/`, `.github/`, `.git*` and `README.md` from being served.
- Email for the domain runs on Cloudflare Email Routing (MX/SPF/DKIM in DNS); leave those records alone.
