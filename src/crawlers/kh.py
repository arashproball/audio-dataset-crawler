import re
from datetime import datetime
from typing import Optional
from urllib.parse import urljoin, urlparse, parse_qs

import jdatetime

from crawlers.base_crawler import BaseCrawler, AudioItem


class KhameneiCrawler(BaseCrawler):

    BASE_URL = "https://farsi.khamenei.ir/"

    def __init__(
        self,
        start_url=BASE_URL,
        **kwargs
    ):
        super().__init__(
            start_url=start_url,
            **kwargs
        )

        self.items: list[AudioItem] = []
        self.audio_ids: set[int] = set()

    def parse(self, response, soup):

        players = self.find_audio_players(soup)

        if not players:
            return

        page_title = self.extract_page_title(soup)
        published_at = self.extract_date(soup)
        tags = self.extract_tags(soup)
        image_url = self.extract_image_url(soup)

        for player in players:

            audio_id = self.extract_audio_id(player)

            if (
                audio_id is not None
                and audio_id in self.audio_ids
            ):
                continue

            audio_url = self.extract_audio_url(player)

            if audio_url is None:
                continue

            content_id = self.extract_content_id(
                player,
                response["url"]
            )

            content_url = self.extract_content_url(
                player,
                response["url"]
            )

            audio_title = self.extract_audio_title(
                soup,
                audio_id
            )

            speaker = self.extract_speaker(
                audio_title
            )

            item = AudioItem(
                source="farsi.khamenei.ir",
                content_id=content_id,
                title=page_title,
                content_url=content_url,
                audio_url=audio_url,
                published_at=published_at,
                tags=tags,
                crawled_at=datetime.now(),
                image_url=image_url,
                speaker=speaker,
                audio_title=audio_title,
            )

            self.items.append(item)

            if audio_id is not None:
                self.audio_ids.add(audio_id)

            self.logger.info(
                "Khamenei audio extracted | "
                f"content_id={content_id} | "
                f"audio_title={audio_title}"
            )

    @staticmethod
    def find_audio_players(soup):

        return soup.select(
            "div.khamenei_ir-ajs[data-rss], "
            "div.khamenei_ir-ajs-small[data-rss]"
        )

    @staticmethod
    def extract_audio_id(
            player
    ) -> Optional[int]:

        rss_url = player.get("data-rss")

        if not rss_url:
            return None

        try:

            query = parse_qs(
                urlparse(rss_url).query
            )

            audio_id = query.get(
                "id",
                [None]
            )[0]

            if audio_id is None:
                return None

            return int(audio_id)

        except (ValueError, TypeError):

            return None

    @staticmethod
    def extract_content_id(
            player,
        response_url: Optional[str] = None
    ) -> Optional[int]:

        player_id = player.get("data-id")

        if player_id:

            match = re.search(
                r"player_target_(\d+)",
                player_id
            )

            if match:
                return int(
                    match.group(1)
                )

        element = player.select_one(
            "[data-link]"
        )

        if element:

            data_link = element.get(
                "data-link"
            )

            if data_link:

                match = re.search(
                    r"[?&]id=(\d+)",
                    data_link
                )

                if match:
                    return int(
                        match.group(1)
                    )

        if response_url:

            match = re.search(
                r"[?&]id=(\d+)",
                response_url
            )

            if match:
                return int(
                    match.group(1)
                )

        return None

    @staticmethod
    def extract_page_title(
            soup
    ) -> Optional[str]:

        title = soup.select_one(
            "div[style*='width:100%'][style*='float:right'] > h3"
        )

        if title:

            value = title.get_text(
                " ",
                strip=True
            )

            if value:
                return value

        title = soup.select_one(
            ".audio-content h3"
        )

        if title:

            value = title.get_text(
                " ",
                strip=True
            )

            if value:
                return value

        title = soup.select_one(
            "h1, h2, h3"
        )

        if title:

            value = title.get_text(
                " ",
                strip=True
            )

            if value:
                return value

        return None

    @staticmethod
    def extract_audio_title(
            soup,
        audio_id: Optional[int]
    ) -> Optional[str]:

        if audio_id is None:
            return None

        span = soup.select_one(
            f"#sit_q{audio_id} .text-wrapper span"
        )

        if not span:
            return None

        title = span.get_text(
            " ",
            strip=True
        )

        return title

    def extract_audio_url(
        self,
        player
    ) -> Optional[str]:

        url = player.get("data-hq")

        if url:
            return urljoin(
                self.BASE_URL,
                url
            )

        url = player.get("data-mq")

        if url:
            return urljoin(
                self.BASE_URL,
                url
            )

        url = player.get("data-lq")

        if url:
            return urljoin(
                self.BASE_URL,
                url
            )

        links = player.select(
            ".audio-player-small-download-list a[href]"
        )

        for link in links:

            href = link.get("href")

            if (
                href
                and ".mp3" in href.lower()
            ):
                return urljoin(
                    self.BASE_URL,
                    href
                )

        source = player.select_one(
            "audio source[src]"
        )

        if source:

            src = source.get("src")

            if src:
                return urljoin(
                    self.BASE_URL,
                    src
                )

        audio = player.select_one(
            "audio[src]"
        )

        if audio:

            src = audio.get("src")

            if src:
                return urljoin(
                    self.BASE_URL,
                    src
                )

        return None

    def extract_content_url(
        self,
        player,
        fallback_url: str
    ) -> str:

        button = player.select_one(
            ".audio-player-small-play-pause-button"
        )

        if button:

            url = button.get(
                "data-link"
            )

            if url:
                return urljoin(
                    self.BASE_URL,
                    url
                )

        element = player.select_one(
            "[data-link]"
        )

        if element:

            url = element.get(
                "data-link"
            )

            if url:
                return urljoin(
                    self.BASE_URL,
                    url
                )

        return urljoin(
            self.BASE_URL,
            fallback_url
        )

    def extract_date(
        self,
        soup
    ) -> Optional[str]:

        date_element = soup.select_one(
            "span.oliveDate"
        )

        if date_element is None:

            date_element = soup.select_one(
                "time"
            )

        if date_element is None:
            return None

        value = date_element.get_text(
            " ",
            strip=True
        )

        if not value:
            return None

        value = self.normalize_persian_digits(
            value
        )

        return self.jalali_to_gregorian(
            value
        )

    @staticmethod
    def jalali_to_gregorian(
        value: Optional[str]
    ) -> Optional[str]:

        if not value:
            return None

        match = re.search(
            r"(\d{4})[/-](\d{1,2})[/-](\d{1,2})",
            value
        )

        if not match:
            return None

        year, month, day = map(
            int,
            match.groups()
        )

        try:

            gregorian_date = jdatetime.date(
                year,
                month,
                day
            ).togregorian()

            return gregorian_date.isoformat()

        except ValueError:

            return None

    @staticmethod
    def extract_tags(
            soup
    ) -> list[str]:

        tags = []

        for link in soup.select(
            "a[href*='tag-content']"
        ):

            text = link.get_text(
                " ",
                strip=True
            )

            if text:
                tags.append(text)

        return tags

    def extract_image_url(
        self,
        soup
    ) -> Optional[str]:

        image = soup.select_one(
            "meta[property='og:image']"
        )

        if image:

            url = image.get(
                "content"
            )

            if url:
                return urljoin(
                    self.BASE_URL,
                    url
                )

        image = soup.select_one(
            "img[src*='smps']"
        )

        if image:

            url = image.get(
                "src"
            )

            if url:
                return urljoin(
                    self.BASE_URL,
                    url
                )

        return None

    @staticmethod
    def extract_speaker(
            audio_title: Optional[str]
    ) -> Optional[str]:

        if not audio_title:
            return None

        if "|" not in audio_title:
            return None

        speaker = audio_title.split(
            "|",
            1
        )[1]

        return speaker

    @staticmethod
    def normalize_persian_digits(
        value: Optional[str]
    ) -> Optional[str]:

        if not value:
            return None

        translation = str.maketrans(
            "۰۱۲۳۴۵۶۷۸۹٠١٢٣٤٥٦٧٨٩",
            "01234567890123456789"
        )

        return value.translate(
            translation
        )