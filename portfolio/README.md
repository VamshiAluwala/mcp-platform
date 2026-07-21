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

## Notes

- Fonts: Sora (headings), Inter (body), JetBrains Mono (accents) via Google Fonts, with system fallbacks
- Fully responsive, no external JS libraries; a small vanilla-JS scroll-reveal animation with `prefers-reduced-motion` support
