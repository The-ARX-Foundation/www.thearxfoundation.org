# www.thearxfoundation.org (public monorepo)

Static site for **https://www.thearxfoundation.org/** — pitches, shells, and other **public** ARX Foundation material. Deploy with **GitHub Actions → FTP** to the **www** document root on your host.

**Canonical URL:** use **`www`** in links and `<link rel="canonical">`; point apex `thearxfoundation.org` with a **301** to `www` at the host/DNS layer when ready.

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

## Deploy (Actions → FTP)

On every push to **`main`**, [.github/workflows/deploy-ftp.yml](.github/workflows/deploy-ftp.yml) uploads the static tree (excluding `.git`, `.github`, root `README.md`, `.gitignore`).

**Repository secrets:** `FTP_SERVER`, `FTP_USERNAME`, `FTP_PASSWORD` (Settings → Secrets and variables → Actions).

If uploads land in the wrong directory, uncomment and set **`server-dir`** in the workflow to match SiteGround’s path for **www** (often under `public_html/` for that subdomain).
