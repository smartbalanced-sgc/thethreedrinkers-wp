# The Three Drinkers — WordPress Migration

Migration of thethreedrinkers.com from Squarespace to WordPress on Hostinger.
This repo IS the `authentic-child` child theme — it deploys via Hostinger's
Git integration to `public_html/wp-content/themes/authentic-child` on every
push to `main`.

- Parent theme: **Authentic** by Updates Lab (installed on the server, not in this repo)
- Staging site: ttd.bringit.ph
- Production domain: thethreedrinkers.com

## Parent theme reference

The Authentic parent theme is available **read-only** at:
`https://github.com/smartbalanced-sgc/thethreedrinkers-parent-reference`

Consult it before making any child theme override — templates, CSS, hooks,
filters, and `functions.php`. **Never commit to or modify that repo under any
circumstances.**

## SEO mandate

Act as the project's SEO expert. The non-negotiable baseline is **preserve
every ranking and click the Squarespace site currently earns**. The active
goal is to **improve on it** using current, clean, intentional SEO practice
(post-March-2024 Google updates: Helpful Content, Core Updates, E-E-A-T,
SpamBrain). Be opinionated and proactive — surface SEO risks and
opportunities the user hasn't asked about, and back recommendations with
the GSC and WXR data already in the project.

Concrete obligations:

- **Preserve URL structure exactly** unless a change is justified by data
  and explicitly approved. This includes article paths, tag bases,
  category bases, and pagination.
- **Preserve and migrate SEO metadata** (titles, meta descriptions,
  canonicals, OG tags, schema) for every URL that earned clicks or
  impressions in GSC.
- **Protect tag/category landing pages** — they drive ~52% of current
  organic traffic on this site. Treat them as first-class content, not
  disposable archives.
- **Flag thin / duplicate / cannibalising content** before publishing and
  propose merges, canonicals, or noindex where appropriate.
- **Maintain a redirect map** for any URL that must change, and verify
  every old URL resolves with a 301 (not a 302 or 404).
- **Build for E-E-A-T** — author bios, dates, real expertise signals,
  proper schema (`Article`, `Person`, `Organization`, `FAQPage` where
  warranted).
- **Don't chase tactics that algorithms now penalise** — keyword-stuffed
  tag spam, doorway pages, AI-generated thin content, mass-produced
  archives with no editorial value.
- **Measure before changing.** If GSC data exists for a URL, consult it
  before touching that URL.

When in doubt, prefer the option that protects existing rankings; suggest
improvements as separate follow-up work the user can approve.

## Project rules

1. **Never edit the parent theme.** All overrides and customizations live in
   this child theme. If a parent template needs changing, copy it into the
   matching path inside this repo and edit the copy.
2. **Child theme only.** No plugin code, no mu-plugins, no direct edits on
   the server. Anything that should persist must be committed here and
   deployed via Git.
3. **Prototype visually before implementing.** For any visual or layout
   change, produce a mockup / screenshot / HTML preview the user can sign
   off on *before* writing the final CSS/PHP that ships to `main`.
4. **SEO preservation is critical** (see SEO mandate above for the full
   standard). Never change URL structures, slugs, canonical tags,
   title/meta patterns, heading hierarchy, or redirects without explicit
   approval. Flag anything that could affect indexing.
5. **`main` deploys to production-adjacent.** Treat pushes to `main` as
   deploys. Do exploratory work on feature branches; only merge to `main`
   when the change is ready to go live on the staging site.
6. **Keep `style.css` header intact.** The `Template:` line must keep
   pointing at the parent theme slug or WordPress will not recognize this
   as a child theme.
7. **Never `@import` the parent stylesheet.** Only enqueue the parent
   stylesheet from `functions.php` via `wp_enqueue_style` if the parent
   theme does not already enqueue it itself (Authentic does).
8. **Ask before destructive or shared-state actions** — force pushes,
   history rewrites, deleting branches, touching server-side files outside
   this repo, or anything that would affect the live site.
