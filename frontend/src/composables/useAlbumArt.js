// Shared neutral album-art placeholder + error fallback.
// Used wherever album art may be missing so the browser never receives an
// empty `src` (which would otherwise re-request the current page URL and
// render a broken image).

export const ALBUM_ART_PLACEHOLDER =
  'data:image/svg+xml;charset=utf-8,' +
  encodeURIComponent(
    '<svg xmlns="http://www.w3.org/2000/svg" width="64" height="64" viewBox="0 0 64 64">' +
      '<rect width="64" height="64" rx="6" fill="%23333"/>' +
      '<path d="M40 18v18.6a8 8 0 1 1-4-6.9V22l-12 2.4v14.2a8 8 0 1 1-4-6.9V20l20-4z" fill="%23888"/>' +
      '</svg>',
  );

export function onArtError(event) {
  if (event?.target && event.target.src !== ALBUM_ART_PLACEHOLDER) {
    event.target.src = ALBUM_ART_PLACEHOLDER;
  }
}
