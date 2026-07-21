# Personal Portfolio — Vamshi Krishna Aluwala

A single-page, self-contained portfolio website. No build step, no dependencies — just open `index.html` in a browser.

## Preview locally

```bash
# Option 1: open directly
open portfolio/index.html

# Option 2: serve it
python3 -m http.server 8080 --directory portfolio
# then visit http://localhost:8080
```

## Deploy

Works out of the box on any static host:

- **GitHub Pages** — enable Pages on this repo and point it at the `portfolio/` folder
- **Netlify / Vercel** — drag-and-drop the `portfolio/` folder
- Any web server — copy `index.html` to the document root

## Add your photo

Drop a square-ish photo named `profile.jpg` into this folder (next to `index.html`) and it will appear automatically in the hero section. Until then, a styled "VK" initials placeholder is shown.

## Theme

The site supports both dark and light themes. It follows the visitor's system preference by default, and the sun/moon button in the navbar toggles it manually (the choice is remembered in `localStorage`).

## Notes

- Fonts: Sora (headings), Inter (body), JetBrains Mono (accents) via Google Fonts, with system fallbacks
- Fully responsive, no external JS libraries; a small vanilla-JS scroll-reveal animation with `prefers-reduced-motion` support
