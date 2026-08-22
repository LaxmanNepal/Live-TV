# TV Data Architecture

The app uses three generated data files:

- `source-list.json` — exact upstream list fetched from the legacy TV database.
- `channels.json` — normalized records consumed by the web app.
- `categories.json` — generated category counts for navigation and analytics.

Do not manually edit generated files. The workflow in `.github/workflows/sync-tv-data.yml` refreshes them every 6 hours and can also be started manually.

## Normalized channel schema

```json
{
  "id": "unique-slug",
  "name": "Channel Name",
  "country": "India",
  "language": "Hindi",
  "category": "movies",
  "logo": "https://...",
  "stream": "https://...m3u8",
  "sourcePage": "https://...",
  "program": "Channel Name Live",
  "enabled": true
}
```

The upstream source remains the source of truth; classification and IDs are generated locally so the UI does not depend on the legacy Blogger structure.
