# Dashboard User Flow Improvements (2025-11-12)

## Requirements

- Dashboards must be usable on desktop, tablet, and mobile.
- Critical KPIs (camera availability, alerts, log anomalies) should be visible
  without scrolling on common resolutions (1920×1080, 1280×800, iPad).
- Provide quick navigation between camera, sensor, and logging views.

## Planned Enhancements

1. **Responsive Layout**
   - Use Grafana panel grid widths (6 / 12) to allow stacking on smaller viewports.
   - Collapse secondary panels into rows with `repeat` option for easy filtering.
   - Add "Compact" text panels summarizing status when real estate is constrained.

2. **Navigation**
   - Add dashboard links between `camera-overview`, `sensor-overview`, and
     `logging-overview`.
   - Create landing dashboard with key stats + shortcuts (to be built when
     `user-flows` graduates to implementation).

3. **Mobile Testing Checklist**
   - Validate on iPad (Safari) and Android tablet (Chrome).
   - Confirm panels adapt when width < 768px.
   - Ensure alert banners are legible and accessible.

4. **Accessibility**
   - Favor high-contrast palette (Grafana dark theme with accessible colors).
   - Include descriptive panel titles and units for screen readers.

## Next Steps

- Implement navigation links (Grafana dashboard links) once dashboards are
  imported.
- Document mobile-specific screenshots for QA.
- Gather feedback from pilot mobile users and iterate.
