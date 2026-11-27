#!/usr/bin/env python3
"""Publish each public project's original write-up at projects/<slug>/index.html.

Usage:
  build_project_pages.py --manifest PUBLIC/manifest.json --pages PUBLIC/pages --out projects

- The source pages stay untouched. Each copy only gets a slim ARX bar inserted right after
  <body> (back to all projects, stage, contact) plus the site favicon if the page has none.
- A page with needs_wrap (a bare React .jsx component) is compiled once with esbuild
  (npx, pinned) and wrapped in a full document that loads pinned React UMD builds, so
  visitors never download a JSX compiler.
- Writes projects/pages.json ({id: {slug, url, stage, blurb}}) for build_projects.py.
- Removes projects/<slug>/ folders this script made earlier (marked by .generated) that
  are no longer in the manifest, so unpublishing on the board unpublishes here too.
Stdlib only, plus npx esbuild for .jsx pages.
"""
import argparse, html, json, os, re, shutil, subprocess, sys

SITE = json.load(open(os.path.join(os.path.dirname(os.path.abspath(__file__)), "site.json"), encoding="utf-8"))
EMAIL = SITE["contact_email"]
STAGES = ("Active", "Up next", "Shelved", "Idea")
SLUG = re.compile(r"^[a-z0-9][a-z0-9-]{0,80}$")
RESERVED = {"index.html", "pages.json"}
HOLDS = {k for k in json.load(open(os.path.join(os.path.dirname(os.path.abspath(__file__)), "holds.json"), encoding="utf-8")) if not k.startswith("_")}

BAR = """<div id="arx-bar" style="all:initial;display:flex;flex-wrap:wrap;align-items:center;gap:6px 18px;box-sizing:border-box;width:100%;padding:9px max(16px,env(safe-area-inset-left,0px));background:#0A0A0A;color:#F2F2EF;border-bottom:1px solid rgba(242,242,239,.18);font:500 11px/1.4 'IBM Plex Mono',ui-monospace,Menlo,monospace;letter-spacing:.12em;text-transform:uppercase;position:relative;z-index:2147483000">
<a href="/projects/" style="color:#F2F2EF;text-decoration:none">&larr; All projects</a>
<span style="color:#8C8C88">The ARX Foundation</span>
<span style="border:1px solid rgba(242,242,239,.35);padding:2px 7px">{stage}</span>
<span style="color:#8C8C88;text-transform:none;letter-spacing:.02em;font-size:12px">{note}</span>
<a href="mailto:{email}?subject={subject}" style="color:#F2F2EF;margin-left:auto">Get in touch</a>
</div>
"""
NOTES = {"Shelved": "Paused, not dead. Open to collaborators or funding.",
         "Idea": "An early idea. Open to collaborators.",
         "Up next": "Queued to build next.", "Active": "In active development."}
ICON = ('<link rel="icon" href="/favicon.svg" type="image/svg+xml">'
        '<link rel="icon" href="/favicon.ico" sizes="48x48">')

JSX_DOC = """<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>{title}</title>
<style>html,body{{margin:0;background:#0b0d10}}</style>
</head>
<body>
<div id="root"></div>
<script src="https://cdnjs.cloudflare.com/ajax/libs/react/18.3.1/umd/react.production.min.js" crossorigin="anonymous"></script>
<script src="https://cdnjs.cloudflare.com/ajax/libs/react-dom/18.3.1/umd/react-dom.production.min.js" crossorigin="anonymous"></script>
<script>
{code}
ReactDOM.createRoot(document.getElementById("root")).render(React.createElement(App));
</script>
</body>
</html>
"""


ESBUILD = ["npx", "-y", "esbuild@0.24.0", "--loader=jsx", "--jsx-factory=React.createElement",
           "--jsx-fragment=React.Fragment", "--minify", "--target=es2019"]


def compile_jsx(src, slug):
    """Bare component -> plain script defining App (React globals from the UMD builds)."""
    react_import = re.compile(r'^import\s*\{([^}]*)\}\s*from\s*["\']react["\'];?\s*$', re.M)
    hooks = sorted({h.strip() for m in react_import.finditer(src) for h in m.group(1).split(",") if h.strip()})
    src = react_import.sub("", src)
    if re.search(r'^import\s', src, re.M):
        sys.exit(f"{slug}: imports other than named react hooks are not supported")
    m = re.search(r'^export\s+default\s+function\s+(\w+)', src, re.M)
    if not m:
        sys.exit(f"{slug}: expected `export default function Name`")
    src = src[:m.start()] + src[m.start():].replace("export default ", "", 1)
    prelude = f"const {{ {', '.join(hooks)} }} = React;\n" if hooks else ""
    src = prelude + src + f"\nconst App = {m.group(1)};\n"
    r = subprocess.run(ESBUILD, input=src, capture_output=True, text=True)
    if r.returncode:
        sys.exit(f"{slug}: esbuild failed\n{r.stderr}")
    return r.stdout


def bar(entry):
    stage = entry["status"]
    return BAR.format(stage=html.escape(stage), note=html.escape(NOTES.get(stage, "")),
                      email=html.escape(EMAIL), subject=html.escape(entry["title"]).replace(" ", "%20"))


def inject(doc, entry):
    # <body> is optional in HTML; fall back to just after </head>.
    m = re.search(r"<body\b[^>]*>", doc, re.I) or re.search(r"</head\s*>", doc, re.I)
    if not m:
        return None  # truncated or malformed page
    doc = doc[:m.end()] + "\n" + bar(entry) + doc[m.end():]
    if not re.search(r'<link[^>]+rel=["\'](shortcut )?icon', doc, re.I):
        doc = re.sub(r"(<meta[^>]*charset[^>]*>)", r"\1" + ICON, doc, count=1, flags=re.I)
    return doc


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--manifest", required=True); ap.add_argument("--pages", required=True)
    ap.add_argument("--out", required=True)
    a = ap.parse_args()
    man = json.load(open(a.manifest, encoding="utf-8"))
    os.makedirs(a.out, exist_ok=True)
    index, made = {}, set()
    for e in man["pages"]:
        slug = e["slug"]
        if e["id"] in HOLDS:
            print(f"HELD {slug} ({e['id']}): see tools/holds.json")
            continue
        if not SLUG.match(slug) or slug in RESERVED:
            sys.exit(f"bad slug: {slug!r}")
        if e["status"] not in STAGES:
            sys.exit(f"{slug}: unknown status {e['status']!r}")
        src = os.path.join(a.pages, e["file"])
        if e.get("needs_wrap"):
            doc = JSX_DOC.format(title=html.escape(e["title"]), code=compile_jsx(open(src, encoding="utf-8").read(), slug))
        else:
            doc = open(src, encoding="utf-8").read()
            if not re.match(r"\s*<!doctype html", doc, re.I):
                sys.exit(f"{e['file']}: no doctype")
        out_doc = inject(doc, e)
        if out_doc is None or not re.search(r"</html\s*>\s*$", out_doc, re.I):
            print(f"SKIPPED {slug}: page is truncated or malformed (no </head>/<body>, or no closing </html>)")
            continue
        d = os.path.join(a.out, slug)
        os.makedirs(d, exist_ok=True)
        open(os.path.join(d, "index.html"), "w", encoding="utf-8").write(out_doc)
        open(os.path.join(d, ".generated"), "w").write(e["id"] + "\n")
        made.add(slug)
        index[e["id"]] = {"slug": slug, "url": f"/projects/{slug}/", "stage": e["status"], "blurb": e.get("blurb") or ""}
    for name in sorted(os.listdir(a.out)):
        d = os.path.join(a.out, name)
        if name not in made and os.path.isfile(os.path.join(d, ".generated")):
            shutil.rmtree(d); print("removed", name)
    json.dump(index, open(os.path.join(a.out, "pages.json"), "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    print(f"{len(made)} project pages -> {a.out}/<slug>/")


if __name__ == "__main__":
    main()
