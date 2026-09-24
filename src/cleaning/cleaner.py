import re
from urllib.parse import urlparse, urlunparse

from crawlers.base_crawler import AudioItem


class AudioCleaner:

    def clean(self, item: AudioItem) -> AudioItem:
        """
        Normalize and clean a raw AudioItem.
        """

        item.title = self.clean_text(item.title)
        item.audio_title = self.clean_text(item.audio_title)
        item.speaker = self.clean_text(item.speaker)

        item.content_url = self.normalize_url(item.content_url)
        item.audio_url = self.normalize_url(item.audio_url)
        item.image_url = self.normalize_url(item.image_url)

        item.tags = self.clean_tags(item.tags)

        item.published_at = self.clean_date(item.published_at)

        return item

    # --------------------------------------------------
    # Text
    # --------------------------------------------------

    def clean_text(self, value: str | None) -> str | None:
        if value is None:
            return None

        value = str(value)

        # Normalize different kinds of whitespace
        value = re.sub(r"\s+", " ", value)

        # Remove leading/trailing whitespace
        value = value.strip()

        if not value:
            return None

        return value

    # --------------------------------------------------
    # Digits
    # --------------------------------------------------

    def normalize_digits(self, value: str | None) -> str | None:
        if value is None:
            return None

        translation_table = str.maketrans(
            "۰۱۲۳۴۵۶۷۸۹٠١٢٣٤٥٦٧٨٩",
            "01234567890123456789"
        )

        return value.translate(translation_table)

    # --------------------------------------------------
    # Date
    # --------------------------------------------------

    def clean_date(self, value: str | None) -> str | None:
        if value is None:
            return None

        value = self.normalize_digits(value)
        value = self.clean_text(value)

        if value is None:
            return None

        return value

    # --------------------------------------------------
    # Tags
    # --------------------------------------------------

    def clean_tags(self, tags: list[str] | None) -> list[str]:
        if not tags:
            return []

        cleaned_tags = []

        for tag in tags:
            tag = self.clean_text(tag)

            if tag is None:
                continue

            if tag not in cleaned_tags:
                cleaned_tags.append(tag)

        return cleaned_tags

    # --------------------------------------------------
    # URL
    # --------------------------------------------------

    def normalize_url(self, url: str | None) -> str | None:
        if not url:
            return None

        url = url.strip()

        if not url:
            return None

        parsed = urlparse(url)

        # If URL is relative, keep it as-is.
        # Crawler should normally already provide absolute URLs.
        if not parsed.scheme:
            return url

        scheme = parsed.scheme.lower()
        netloc = parsed.netloc.lower()

        path = parsed.path or "/"

        normalized = urlunparse(
            (
                scheme,
                netloc,
                path,
                parsed.params,
                parsed.query,
                ""
            )
        )

        return normalized