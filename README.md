# MHC Atlas OS Website

This directory contains the static GitHub Pages microsite for **MHC Atlas OS**. It is intended to present the project as a serious architecture-driven technical platform, not as a startup landing page and not as a README pasted onto the web.

## Files

- `index.html` - homepage structure, section content, and link targets
- `styles.css` - visual system, layout, responsiveness, and component styling
- `script.js` - sticky navigation, active section highlighting, mobile nav toggle, image fallback behavior, and subtle reveal-on-scroll
- `.nojekyll` - disables Jekyll processing so GitHub Pages serves the site as plain static files

## Deploy on GitHub Pages

1. Commit these files to the repository root.
2. Push the changes to the branch you want to publish, usually `main`.
3. In GitHub, open `Settings -> Pages`.
4. Choose:
   - `Source: Deploy from a branch`
   - `Branch: main`
   - `Folder: / (root)`
5. Save and wait for the Pages deployment to complete.

For a repository named `alphafold-mhc-atlas`, the published URL is typically:

```text
https://manishklach.github.io/alphafold-mhc-atlas/
```

## Asset placement

Place static visuals in:

```text
./assets/architecture.png
./assets/runtime-modes.png
./assets/scoring-flow.png
./assets/ui-preview.png
./assets/pdb-compare.png
./assets/favicon.png
```

The homepage already points to those paths.

### Current asset behavior

- `./assets/architecture.png` falls back to `./docs/architecture.svg` if the PNG is missing.
- `./assets/scoring-flow.png` shows a styled placeholder if the image does not exist.
- `./assets/favicon.png` is optional but recommended.

## Edit hero metadata

The hero is defined in `index.html`.

Update these blocks to change the top-of-page positioning:

- `<h1>` for the project name
- `<p class="hero-subtitle">` for the subtitle
- `<p class="hero-thesis">` for the one-line thesis
- `<dl class="meta-grid">` for the metadata row
- `<div class="hero-actions">` for CTA button labels and links

## Customize repository, docs, and demo links

Most public-facing links live directly in `index.html`.

Common links you may want to change:

- repository:
  `https://github.com/manishklach/alphafold-mhc-atlas`
- docs:
  `./docs/SPEC.md`
- quickstart:
  `./QUICKSTART.md`
- contribution guide:
  `./CONTRIBUTING.md`
- issues:
  `https://github.com/manishklach/alphafold-mhc-atlas/issues`
- demo script:
  `./scripts/demo_showcase.py`
- UI notes:
  `./apps/ui/README.md`

If you rename sections or IDs, also update the matching navigation links in the header.

## Swap in real architecture and UI screenshots later

The site is already prepared for production visuals.

Recommended replacements:

- `architecture.png`
  Use this for the primary system architecture figure.
- `runtime-modes.png`
  Reserved for a future runtime comparison image if you want one.
- `scoring-flow.png`
  Use this for a dedicated scoring or signal-composition diagram.
- `ui-preview.png`
  Use this for Open Graph preview and future UI section visuals.
- `pdb-compare.png`
  Use this for a WT vs mutant comparison image if you add one later.

Keep all new images under `./assets/` and link them with relative paths.

## .nojekyll

Keep `.nojekyll` in the published root. This ensures GitHub Pages serves the site as plain static files and does not try to process the site through Jekyll.

## Local preview

Any static file server will work. For example:

```bash
python -m http.server 8000
```

Then open:

```text
http://localhost:8000/
```

## Notes

- The site is intentionally framework-free: plain HTML, CSS, and vanilla JavaScript only.
- It is responsive and keyboard-friendly.
- JavaScript is optional enhancement; navigation and content remain accessible without it.
- The color system and major spacing tokens live in `:root` at the top of `styles.css`.
