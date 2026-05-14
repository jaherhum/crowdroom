import json

from backend.adapters.base import StreamingPlatformAdapter
from backend.core.config import settings
from backend.schemas.song_metadata import ReadSongMetadata


class MusicBrainzAdapter(StreamingPlatformAdapter):
    BASE_URL = settings.MUSICBRAINZ_API_URL
    _default_headers = {"User-Agent": "crowdroom/0.5 (https://github.com/jaherhum/crowdroom)"}

    def __init__(self, session=None, rate_limit_delay=1.0):
        super().__init__(session=session, rate_limit_delay=rate_limit_delay)

    # -- public interface (abstract contract) ----------------------------------

    async def search(
        self, isrc: str | None = None, query: str = ""
    ) -> list[ReadSongMetadata]:
        # MusicBrainz returns XML by default — must ask for JSON
        params: dict[str, str | int] = {"fmt": "json"}
        if isrc:
            params["isrc"] = isrc
        elif query:
            params["query"] = query
            params["limit"] = 20

        data = await self._cached_request(
            f"search:{isrc or query}",
            f"{self.BASE_URL}/recording",
            params=params,
        )
        raw = json.loads(data)
        return [self._parse_recording(r) for r in raw.get("recordings", [])]

    async def get_metadata(self, external_id: str) -> ReadSongMetadata | None:
        # Build URL with inc= using + as separator (literal, not URL-encoded).
        # Valid includes for the recording resource: aliases, artist-credits,
        # genres, isrcs, labels, url-schemes. Note: "release-group" is NOT valid
        # for recordings — use search endpoint or rely on release-list in base response.
        inc_parts = "artist-credits isrcs releases"
        url = (
            f"{self.BASE_URL}/recording/{external_id}"
            f"?fmt=json&inc={inc_parts}"
        )
        data = await self._cached_request(f"mbid:{external_id}", url)
        result = json.loads(data)
        return self._parse_recording(result) if result.get("id") else None

    def get_track_uri(self, external_id: str) -> str | None:
        # MusicBrainz uses MBIDs directly rather than URIs
        return f"musicbrainz:recording:{external_id}"

    # -- internal helpers ------------------------------------------------------

    @staticmethod
    def _parse_recording(raw: dict) -> ReadSongMetadata:
        # Extract artist names from both search-style and lookup-style
        # artist-credit structures
        credits = raw.get("artist-credit") or raw.get("artist-credits") or []
        artists = []
        for entry in credits:
            if not isinstance(entry, dict):
                continue
            # Search style: {"name": "Queen", "artist": {...}}
            name = entry.get("name")
            # Lookup style: {"name-credit": {"name": "Queen"}, ...}
            if not name:
                nc = entry.get("name-credit") or {}
                name = nc.get("name") if isinstance(nc, dict) else None
            if name:
                artists.append(name)

        # ISRCs come in different field names depending on endpoint
        isrc_key = "isrc-list" if raw.get("isrc-list") else "isrcs"
        isrcs = []
        for item in (raw.get(isrc_key) or []):
            isrc_str = item.get("isrc") if isinstance(item, dict) else str(item)
            if isrc_str:
                isrcs.append(isrc_str)

        album = MusicBrainzAdapter._pick_album(raw.get("release-list"))

        cover_art_url = None
        relations = raw.get("relation-list") or []
        for relation in relations:
            if not isinstance(relation, dict):
                continue
            if relation.get("target-type") != "image":
                continue
            attrs = relation.get("attribute", {})
            if not isinstance(attrs, dict):
                continue
            if not attrs.get("source_image"):
                continue
            url_data = relation.get("url") or {}
            cover_art_url = url_data.get("$text")
            break

        return ReadSongMetadata(
            title=raw.get("title", ""),
            artist=artists[0] if artists else "",
            artists=artists,
            album=album,
            duration_ms=int(raw["length"]) if raw.get("length") else None,
            isrc=isrcs[0] if isrcs else None,
            platform=None,
            album_art_url=cover_art_url,
            external_id=raw.get("id"),
        )

    @staticmethod
    def _pick_album(release_list: list | None) -> str:
        """Pick the most meaningful album title from available releases.

        Prefers original studio albums over compilations or reissues.
        """
        if not release_list:
            return ""

        for release in release_list:
            title = (release.get("title") or "").strip()
            if not title:
                continue

            # Prefer non-compilation releases
            release_group = release.get("release-group", {}) or {}
            type_value = release_group.get("type") or ""
            if type_value not in ("Compilation", "Side", "Split"):
                return title

        # Fallback: return first available
        for release in release_list:
            title = (release.get("title") or "").strip()
            if title:
                return title

        return ""
