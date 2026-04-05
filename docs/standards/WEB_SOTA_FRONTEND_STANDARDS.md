# Web SOTA Frontend Standards

**Status:** Mandatory for all web-sota dashboards and UIs in this project.

## Required stack

| Layer      | Technology   | Notes |
|-----------|--------------|--------|
| Framework | **React**    | Functional components, hooks; TypeScript preferred. |
| Build     | **Vite**     | Default bundler for React. |
| Styling   | **Tailwind CSS** | Utility-first; no ad‑hoc custom CSS for layout/theme. |
| Components| **shadcn/ui** | Use shadcn components; install via CLI, not a single dependency. |

## Rationale

- **Consistency** with other project dashboards (e.g. robofang `/dashboard`: React/Vite/Tailwind).
- **Maintainability**: One stack across MCP web UIs; shared patterns and accessibility.
- **Quality**: shadcn/ui gives accessible, themable, copy‑paste components on Tailwind.

## Out of scope (legacy)

- Jinja2 server‑side rendering for primary UI.
- Vanilla JS + custom CSS as the main frontend.
- Other CSS frameworks (Bootstrap, custom-only) for new pages.

## Migration

Existing Jinja2/custom CSS UIs (e.g. `web-sota/backend` with FastAPI + Jinja2) are **legacy**. New features and replacements must follow this standard. Full migration of existing pages is tracked separately.
