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
4. **SEO preservation is critical.** Do not change URL structures, slugs,
   canonical tags, title/meta patterns, heading hierarchy, or redirects
   without explicit approval. Flag anything that could affect indexing.
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
