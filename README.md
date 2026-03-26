# MHC Atlas OS Website

This directory contains the polished GitHub Pages microsite for **MHC Atlas OS**. It is designed as a serious, architecture-driven technical project site with stronger SEO metadata, clearer problem framing, and premium static presentation.

## Files

- `index.html` - page structure, copy, metadata, structured data, navigation, and link targets
- `styles.css` - visual system, layout, responsiveness, and component styling
- `script.js` - sticky navigation, active section highlighting, mobile nav toggle, image fallback handling, and subtle reveal-on-scroll
- `.nojekyll` - disables Jekyll processing so GitHub Pages serves the site as plain static files

## SEO metadata

The page includes:

- title tag
- meta description
- meta keywords
- robots tag
- canonical URL
- author meta
- Open Graph metadata
- Twitter card metadata
- JSON-LD structured data

### Where to edit SEO fields

Open `index.html` and update these areas in the `<head>`:

- `<title>`
- `<meta name="description">`
- `<meta name="keywords">`
- `<link rel="canonical">`
- Open Graph tags:
  - `og:title`
  - `og:description`
  - `og:url`
  - `og:image`
  - `og:site_name`
- Twitter tags:
  - `twitter:title`
  - `twitter:description`
  - `twitter:image`

### Where to edit structured data / JSON-LD

Also in `index.html`, update the `<script type="application/ld+json">` block.

Useful fields to adjust there:

- `name`
- `description`
- `url`
- `codeRepository`
- `image`
- `keywords`
- `author`

## Problem and why-it-matters copy

The homepage now includes stronger narrative framing around:

- the project problem
- why the problem matters
- why raw structure outputs are not enough
- why runtime abstraction and policy-governed execution matter

### Where to edit this copy

In `index.html`, the main narrative sections are:

- `#problem`
- `#why-matters`
- `#platform`
- `#execution-why`
- `#architecture`

These are the main places to update the problem statement and explanation of why the platform matters.

## Hero metadata and CTA buttons

The hero content is defined in `index.html`.

Edit these blocks to update the top-of-page positioning:

- `<h1>` for the project name
- `<p class="hero-subtitle">` for the subtitle
- `<p class="hero-thesis">` for the one-line thesis
- `<dl class="meta-grid">` for the metadata row
- `<div class="hero-actions">` for button labels and URLs

## Asset placement

The site can use these asset paths:

```text
./assets/architecture.png
./assets/runtime-modes.png
./assets/scoring-flow.png
./assets/ui-preview.png
./assets/pdb-compare.png
./assets/favicon.png
```

### Current built-in asset behavior

This version uses shipped repo assets where available so the live site does not depend on missing files:

- architecture figure:
  `./docs/architecture.svg`
- UI preview:
  `./docs/ui.png`
- social preview:
  `./docs/social_preview.png`

The scoring section currently uses a built-in HTML/CSS diagram instead of an external image, so it remains stable even without `./assets/scoring-flow.png`.

## Update repository, docs, and demo links

Most public-facing links live directly in `index.html`.

Common links to update:

- repository:
  `https://github.com/manishklach/alphafold-mhc-atlas`
- docs:
  `./docs/SPEC.md`
- quickstart:
  `./QUICKSTART.md`
- contribution guide:
  `./CONTRIBUTING.md`
- pilot workflow:
  `./PILOT_WORKFLOW.md`
- demo script:
  `./scripts/demo_showcase.py`

If you rename section IDs, also update the corresponding header navigation links.

## Deploy on GitHub Pages

1. Commit these files to the repository root.
2. Push to the branch you want to publish, usually `main`.
3. In GitHub, open `Settings -> Pages`.
4. Set:
   - `Source: Deploy from a branch`
   - `Branch: main`
   - `Folder: / (root)`
5. Save and wait for the Pages deployment to complete.

Typical published URL:

```text
https://manishklach.github.io/alphafold-mhc-atlas/
```

## Why `.nojekyll` is included

GitHub Pages often processes sites through Jekyll by default. This site is a plain static HTML, CSS, and JavaScript site, so `.nojekyll` ensures GitHub serves it directly without unnecessary processing.

## Local preview

Any static file server works. Example:

```bash
python -m http.server 8000
```

Then open:

```text
http://localhost:8000/
```

## Notes

- The site remains framework-free.
- JavaScript is minimal and optional enhancement only.
- The main color and spacing tokens live in `:root` at the top of `styles.css`.
