# Live TV

Mobile-first live television web app for Nepali and Hindi channels.

## Structure

```text
Live-TV/
├── index.html
├── data/
│   └── channels.json      # All channel metadata + stream URLs
├── assets/
│   ├── css/style.css      # Responsive UI
│   └── js/app.js          # Search, player, favorites, theme
└── README.md
```

## Add or edit a channel

Edit `data/channels.json` and add an object:

```json
{
  "id": "unique-id",
  "name": "Channel Name",
  "country": "Nepal",
  "language": "Nepali",
  "category": "news",
  "logo": "https://example.com/logo.png",
  "stream": "https://example.com/live/index.m3u8",
  "program": "Live"
}
```

Supported categories are not hard-coded; any category in the JSON automatically becomes a filter chip.

## Stream notes

- HLS `.m3u8` streams are handled with HLS.js where required.
- Safari/iOS native HLS playback is supported through the browser's video element.
- A blank `stream` intentionally shows a clear unavailable state instead of pretending a channel is playable.
- Only use stream URLs you are authorized to redistribute and stream.

## Features

- Mobile-first responsive layout
- Desktop responsive layout
- HLS playback
- Search with autocomplete
- Category filtering
- Favorites stored locally
- Dark/light theme
- Fullscreen player
- Organized JSON channel database
- No build step required; suitable for GitHub Pages
