#!/usr/bin/env python3
"""Build the ARX project list pages from the catalog, triage board and code links.

Usage:
  build_projects.py --catalog CATALOG.json --board BOARD_DIR --links CODE_LINKS.json \
                    --public-out projects/index.html --private-out PRIVATE_DIR/index.html

- Public page: only projects whose board field visibility_set == "public". Money,
  paths, chat links, private markers and notes are removed, and links to non-public
  projects are dropped.
- Private page: every project, with all fields, plus --blurbs (plain-English blurb +
  suggested 90-day signal) and a relative link to each project's collected copy. Write it OUTSIDE this repo.
With --pages (projects/pages.json from build_project_pages.py), public cards get their
write-up link, stage and one-line pitch. Glyphkeeper links its own app at /glyphkeeper/.
Stdlib only. Missing board values fall back to catalog suggestions, and the page
marks them as suggested.
"""
import argparse, collections, datetime, glob, json, os, re, sys

HERE = os.path.dirname(os.path.abspath(__file__))
PLACEHOLDER = re.compile(r"\[(PORTFOLIO TITLE|CUSTOMIZE|Custom|PROJECT NAME)|\{title\}|项目")
DECISION_PRIORITY = {"forge": "P0", "next": "P2", "archive": "P3", "drop": "P4"}
DECISION_HORIZON = {"forge": "<3mo", "next": "3-12mo", "archive": "3y+"}
DECISION_STAGE = {"forge": "Active", "next": "Up next", "archive": "Shelved"}
EXTRA_PAGES = {"arx-094": {"url": "/glyphkeeper/", "stage": "Active", "label": "Open Glyphkeeper",
               "blurb": "Study pages, flashcards and spaced repetition for the world's writing systems."}}
PUBLIC_DROP = {"money", "private_markers", "note", "chat", "chat_links", "local", "path",
               "ip_flag_insightally", "visibility", "sug_visibility", "all_versions", "todos",
               "legal_ip", "links", "conversations", "kind", "blurb", "sug_signal",
               "local_href"}


def load_board(d):
    out = {}
    for f in glob.glob(os.path.join(d, "**", "*.json"), recursive=True):
        doc = json.load(open(f, encoding="utf-8"))
        doc = doc.get("data", doc) if isinstance(doc, dict) else {}
        out[os.path.splitext(os.path.basename(f))[0]] = doc
    return out


def split(v):
    if isinstance(v, list):
        return [str(x).strip() for x in v if str(x).strip()]
    return [s.strip() for s in str(v or "").split(",") if s.strip()]


def local_href(rel):
    """Link from _site-private/index.html to ARX Projects/<rel> (collected copy)."""
    if not rel:
        return None
    from urllib.parse import quote
    return "../" + "/".join(quote(seg) for seg in rel.split("/"))


def merge(c, b, links, blurbs=None):
    """One project row: board value if set, else suggestion (named in `suggested`)."""
    sug = []

    def pick(field, fallback=None):
        v = b.get(field)
        if v not in (None, "", []):
            return v
        if fallback not in (None, "", []):
            sug.append(field)
            return fallback
        return None

    decision = b.get("decision") or ""
    r = {
        "id": c["id"], "title": c.get("title", c["id"]), "category": c.get("category"),
        "tier": c.get("tier"), "decision": decision or None,
        "visibility": pick("visibility_set", c.get("sug_visibility") or c.get("visibility")),
        "entity": pick("entity", c.get("entity_suggested")),
        "status": pick("status", c.get("sug_status")),
        "priority": pick("priority", DECISION_PRIORITY.get(decision)),
        "horizon": pick("horizon", DECISION_HORIZON.get(decision)),
        "effort_remaining": pick("effort_remaining", c.get("sug_effort_remaining")),
        "feasibility": pick("feasibility"), "feasibility_why": b.get("feasibility_why") or None,
        "revenue": pick("revenue"), "money": b.get("money") or None,
        "legal_ip": pick("legal_ip", "IP review" if c.get("ip_flag_insightally") else None),
        "skills": split(b.get("skills")), "people": split(b.get("people")),
        "hardware": split(b.get("hardware")),
        "depends_on": split(b.get("depends_on")), "blocks": split(b.get("blocks")),
        "blockers": b.get("blockers") or None, "next_action": b.get("next_action") or None,
        "note": b.get("note") or None,
        "effort_invested": c.get("effort_invested") or {},
        "themes": c.get("themes") or [], "related": c.get("related") or [],
        "first": c.get("first"), "last_touched": c.get("last_touched") or c.get("latest"),
        "staleness_days": c.get("staleness_days"),
        "private_markers": c.get("private_markers") or [],
        "ip_flag_insightally": bool(c.get("ip_flag_insightally")),
        "chat": c.get("chat"), "local": c.get("collected"),
        "scope": c.get("scope") or "ARX", "kind": c.get("kind"),
        "summary": c.get("summary") or None, "links": c.get("links") or [],
        "conversations": c.get("conversations") or [],
        "placeholder": bool(PLACEHOLDER.search(c.get("title", ""))) or c.get("category") == "Template sources",
        "code": links.get(c["id"], []),
        "blurb": ((blurbs or {}).get(c["id"]) or {}).get("b") or None,
        "sug_signal": ((blurbs or {}).get(c["id"]) or {}).get("s") or None,
        "local_href": local_href(c.get("collected")),
    }
    r["confirmed_public"] = b.get("visibility_set") == "public"
    if r["scope"] != "ARX" and r["visibility"] == "public" and "visibility" in sug:
        r["visibility"] = "private"  # non-ARX items default private
    if c.get("category") == "Personal (not for public)" or r["scope"] == "personal":
        r["visibility"] = "personal"; r["confirmed_public"] = False
    r["suggested"] = sug
    return r


def public_view(rows):
    # Public = confirmed public AND ARX scope (non-ARX work/volunteering/personal never ships).
    keep = {r["id"] for r in rows if r["confirmed_public"] and not r["placeholder"] and r["scope"] == "ARX"
            and r["id"] not in HOLDS}
    out = []
    for r in rows:
        if r["id"] not in keep:
            continue
        p = {k: v for k, v in r.items() if k not in PUBLIC_DROP}
        for k in ("related", "depends_on", "blocks"):
            p[k] = [i for i in r[k] if i in keep]
        p["code"] = [c for c in r["code"] if c.get("kind") == "github" and "private" not in (c.get("note") or "")]
        p["effort_invested"] = {k: v for k, v in r["effort_invested"].items() if k != "bytes"}
        p["suggested"] = [k for k in r["suggested"] if k in p]
        out.append(p)
    return out


SITE = json.load(open(os.path.join(HERE, "site.json"), encoding="utf-8"))
HOLDS = {k for k in json.load(open(os.path.join(HERE, "holds.json"), encoding="utf-8")) if not k.startswith("_")}
CONTACT = {"email": SITE["contact_email"], "discussions": SITE["discussions_url"]}


def patch_home(repo):
    """Write the contact links into index.html between <!--contact--> markers."""
    import html
    p = os.path.join(repo, "index.html")
    s = open(p, encoding="utf-8").read()
    e = html.escape(CONTACT["email"]); d = html.escape(CONTACT["discussions"])
    block = (f'<!--contact--><a href="mailto:{e}">{e}</a> &middot; '
             f'<a href="{d}" rel="noopener noreferrer">Discussions</a><!--/contact-->')
    new = re.sub(r"<!--contact-->.*?<!--/contact-->", block, s, flags=re.S)
    if new != s:
        open(p, "w", encoding="utf-8").write(new)


def render(template, rows, view):
    themes = collections.Counter(t for r in rows for t in r["themes"])
    data = {"view": view, "generated": datetime.date.today().isoformat(),
            "projects": rows, "themes": themes.most_common(60), "contact": CONTACT}
    blob = json.dumps(data, ensure_ascii=False).replace("</", "<\\/")
    return template.replace("/*__DATA__*/null", blob)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--catalog", required=True); ap.add_argument("--board", required=True)
    ap.add_argument("--links", required=True)
    ap.add_argument("--blurbs", help="blurbs.json: {arx-id: {b: blurb, s: suggested 90-day signal}} (private only)")
    ap.add_argument("--pages", help="projects/pages.json from build_project_pages.py")
    ap.add_argument("--public-out", required=True); ap.add_argument("--private-out", required=True)
    a = ap.parse_args()
    repo = os.path.dirname(HERE)
    if os.path.abspath(a.private_out).startswith(repo + os.sep):
        sys.exit("refusing: --private-out must be outside the site repo")
    cat = json.load(open(a.catalog, encoding="utf-8"))
    cat = cat if isinstance(cat, list) else cat.get("projects", [])
    board = load_board(a.board)
    links = json.load(open(a.links, encoding="utf-8")).get("links", {})
    blurbs = json.load(open(a.blurbs, encoding="utf-8")) if a.blurbs else {}
    rows = [merge(c, board.get(c["id"], {}), links, blurbs) for c in cat]
    pages = dict(EXTRA_PAGES, **(json.load(open(a.pages, encoding="utf-8")) if a.pages else {}))
    for r in rows:
        pg = pages.get(r["id"]) or {}
        r["stage"] = pg.get("stage") or DECISION_STAGE.get(r["decision"] or "", "Idea")
        r["page"] = pg.get("url") or None
        r["page_label"] = pg.get("label") or None
        r["pitch"] = pg.get("blurb") or None
    titles = {r["id"]: r["title"] for r in rows}
    for r in rows:
        r["titles"] = {i: titles.get(i, i) for i in set(r["related"] + r["depends_on"] + r["blocks"])}
    tpl = open(os.path.join(HERE, "projects_template.html"), encoding="utf-8").read()
    pub = public_view(rows)
    for p in pub:
        p["titles"] = {i: titles[i] for i in set(p["related"] + p["depends_on"] + p["blocks"])}
    patch_home(repo)
    for path, rs, view in ((a.public_out, pub, "public"), (a.private_out, rows, "private")):
        os.makedirs(os.path.dirname(os.path.abspath(path)), exist_ok=True)
        open(path, "w", encoding="utf-8").write(render(tpl, rs, view))
        print(f"{view}: {len(rs)} projects -> {path}")


if __name__ == "__main__":
    main()
