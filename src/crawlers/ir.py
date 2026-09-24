import re
from datetime import datetime
from urllib.parse import urljoin, urlparse

import jdatetime

from crawlers.base_crawler import (
    BaseCrawler,
    AudioItem,
)


class IransedaCrawler(BaseCrawler):

    WEB_BASE_URL = "http://podcast.iranseda.ir"

    def __init__(
        self,
        start_url,
        **kwargs
    ):
        super().__init__(
            start_url=start_url,
            **kwargs
        )

        self.items: list[AudioItem] = []
        self.audio_urls = {}

    # ---------------------------------------------------------
    # Browser-only fetch
    # ---------------------------------------------------------

    def fetch(self, url):
        if self.browser is None:
            return None

        page = self.browser.context.new_page()

        audio_requests = []

        def handle_request(request):
            request_url = request.url.lower()

            if (
                    ".m3u8" in request_url
                    or ".aac" in request_url
                    or ".mp3" in request_url
                    or (
                    ".mp4" in request_url
                    and (
                            request.resource_type == "media"
                            or "audio" in request_url
                    )
            )
            ):
                audio_requests.append(request.url)

                self.logger.info(
                    "IranSeda media request detected | "
                    "type=%s | url=%s",
                    request.resource_type,
                    request.url
                )

        try:
            self.logger.info(
                "IranSeda browser fetch: %s",
                url
            )

            # مهم:
            # listener قبل از navigation نصب می‌شود
            page.on("request", handle_request)

            response = page.goto(
                url,
                wait_until="domcontentloaded",
                timeout=self.browser.timeout
            )

            if response is None:
                return None

            try:
                page.wait_for_selector(
                    "article.podcasthome",
                    timeout=10_000
                )

                self.logger.info(
                    "IranSeda episode DOM detected"
                )

            except Exception:
                self.logger.warning(
                    "IranSeda episode DOM was not detected"
                )

            articles = page.locator(
                "article.podcasthome"
            )

            article_count = articles.count()

            self.logger.info(
                "IranSeda episodes discovered: %s",
                article_count
            )

            for index in range(article_count):

                article = articles.nth(index)

                content_id = article.get_attribute(
                    "data-id"
                )

                if not content_id:

                    article_id = article.get_attribute(
                        "id"
                    )

                    if article_id:

                        match = re.search(
                            r"\d+",
                            article_id
                        )

                        if match:
                            content_id = match.group()

                if not content_id:
                    continue

                content_id = int(content_id)

                players = article.locator(
                    '[onclick*="SIDPlayer"]'
                )

                if players.count() == 0:
                    self.logger.warning(
                        "No SIDPlayer found | content_id=%s",
                        content_id
                    )
                    continue

                self.logger.info(
                    "Activating IranSeda player | content_id=%s",
                    content_id
                )

                player = players.first

                before_count = len(audio_requests)

                try:

                    player.scroll_into_view_if_needed()

                    player.click(
                        force=True,
                        timeout=5_000
                    )

                    # player ممکن است async باشد
                    page.wait_for_timeout(4_000)

                except Exception as e:

                    self.logger.warning(
                        "Could not activate player | "
                        "content_id=%s | error=%s",
                        content_id,
                        e
                    )

                    continue

                new_requests = audio_requests[
                    before_count:
                ]

                if not new_requests:
                    self.logger.warning(
                        "No media request captured | "
                        "content_id=%s",
                        content_id
                    )

                    continue

                audio_url = self.select_audio_url(
                    new_requests
                )

                if audio_url:
                    self.audio_urls[
                        content_id
                    ] = audio_url

                    self.logger.info(
                        "IranSeda audio captured | "
                        "content_id=%s | audio_url=%s",
                        content_id,
                        audio_url
                    )

            return {
                "url": page.url,
                "status": response.status,
                "content": page.content(),
                "headers": response.headers,
                "method": "playwright"
            }

        except Exception as e:

            self.logger.error(
                "IranSeda browser fetch failed | "
                "url=%s | error=%s",
                url,
                e
            )

            return None

        finally:

            page.remove_listener(
                "request",
                handle_request
            )

            page.close()
    # ---------------------------------------------------------
    @staticmethod
    def select_audio_url(urls):
        if not urls:
            return None

        # Prefer the playlist because it is the stable
        # media entry point rather than an individual segment.
        for url in urls:
            if ".m3u8" in url.lower():
                return url

        for extension in (".mp3", ".mp4", ".aac"):
            for url in urls:
                if extension in url.lower():
                    return url

        return urls[0]


    def parse(
        self,
        response,
        soup
    ):

        self.logger.info(
            "Parsing rendered IranSeda DOM: %s",
            response["url"]
        )

        articles = self.find_episode_articles(
            soup
        )

        if not articles:

            self.logger.warning(
                "No IranSeda episode articles found: %s",
                response["url"]
            )

            return

        self.logger.info(
            "IranSeda episodes discovered: %s",
            len(articles)
        )

        program_title = self.extract_program_title(
            soup
        )

        speaker = self.extract_speaker(
            soup
        )

        for article in articles:

            item = self.parse_episode(
                article=article,
                page_url=response["url"],
                program_title=program_title,
                speaker=speaker
            )

            if item is None:
                continue

            self.items.append(
                item
            )

            self.logger.info(
                "IranSeda audio extracted | "
                f"content_id={item.content_id} | "
                f"audio_title={item.audio_title}"
            )

    # ---------------------------------------------------------
    # Episode discovery
    # ---------------------------------------------------------

    @staticmethod
    def find_episode_articles(soup):

        selectors = [
            "article.podcasthome",
            "article[id^='item']",
        ]

        for selector in selectors:

            articles = soup.select(
                selector
            )

            if articles:
                return articles

        return []

    # ---------------------------------------------------------
    # Parse one episode
    # ---------------------------------------------------------

    def parse_episode(
        self,
        article,
        page_url,
        program_title,
        speaker
    ):

        content_id = self.extract_content_id(
            article
        )

        if content_id is None:

            self.logger.debug(
                "Episode without content id"
            )

            return None

        content_url = self.extract_content_url(
            article
        )

        if content_url is None:

            self.logger.debug(
                "Episode without content URL | "
                f"content_id={content_id}"
            )

            return None

        audio_url = self.audio_urls.get(content_id)

        if audio_url is None:
            self.logger.warning(
                "IranSeda audio URL not captured | "
                "content_id=%s",
                content_id
            )
            return None

        audio_title = self.extract_audio_title(
            article
        )

        published_at = self.extract_date(
            article
        )

        image_url = self.extract_image_url(
            article
        )

        self.add_url(
            content_url
        )

        return AudioItem(
            source="iranseda.ir",
            content_id=content_id,
            title=program_title,
            content_url=content_url,
            audio_url=audio_url,
            published_at=published_at,
            tags=None,
            crawled_at=datetime.now(),
            image_url=image_url,
            speaker=speaker,
            audio_title=audio_title,
        )

    # ---------------------------------------------------------
    # Content ID
    # ---------------------------------------------------------

    @staticmethod
    def extract_content_id(article):

        element = article.select_one(
            "[data-id]"
        )

        if element is not None:

            value = element.get(
                "data-id"
            )

            try:

                return int(value)

            except (
                TypeError,
                ValueError
            ):
                pass

        article_id = article.get(
            "id"
        )

        if article_id:

            match = re.search(
                r"(\d+)",
                article_id
            )

            if match:

                return int(
                    match.group(1)
                )

        link = article.select_one(
            "a.modallink[href]"
        )

        if link is not None:

            href = link.get(
                "href"
            )

            if href:

                parsed = urlparse(
                    href
                )

                query = dict(
                    [
                        part.split("=", 1)
                        for part in parsed.query.split("&")
                        if "=" in part
                    ]
                )

                value = query.get(
                    "g"
                )

                if value:

                    try:

                        return int(value)

                    except (
                        TypeError,
                        ValueError
                    ):
                        pass

        return None

    # ---------------------------------------------------------
    # Content URL
    # ---------------------------------------------------------

    @staticmethod
    def extract_content_url(article):

        link = article.select_one(
            "a.modallink[href]"
        )

        if link is None:
            return None

        href = link.get(
            "href"
        )

        if not href:
            return None

        return urljoin(
            IransedaCrawler.WEB_BASE_URL,
            href
        )

    # ---------------------------------------------------------
    # Audio URL
    # ---------------------------------------------------------

    @staticmethod
    def extract_audio_url(article):

        # 1. Direct audio element
        audio = article.select_one(
            "audio[src]"
        )

        if audio is not None:

            src = audio.get(
                "src"
            )

            if src:
                return urljoin(
                    IransedaCrawler.WEB_BASE_URL,
                    src
                )

        # 2. Source element
        source = article.select_one(
            "audio source[src]"
        )

        if source is not None:

            src = source.get(
                "src"
            )

            if src:
                return urljoin(
                    IransedaCrawler.WEB_BASE_URL,
                    src
                )

        # 3. MP3 / MP4 / M3U8 links
        for link in article.select(
            "a[href]"
        ):

            href = link.get(
                "href"
            )

            if not href:
                continue

            lowered = href.lower()

            if (
                ".mp3" in lowered
                or ".mp4" in lowered
                or ".m3u8" in lowered
                or "playurl" in lowered
                or "playlist" in lowered
            ):

                return urljoin(
                    IransedaCrawler.WEB_BASE_URL,
                    href
                )

        # 4. Data attributes
        attributes = [
            "data-src",
            "data-url",
            "data-playurl",
            "data-audio",
            "data-audio-url",
        ]

        for attribute in attributes:

            element = article.select_one(
                f"[{attribute}]"
            )

            if element is None:
                continue

            value = element.get(
                attribute
            )

            if not value:
                continue

            lowered = value.lower()

            if (
                ".mp3" in lowered
                or ".mp4" in lowered
                or ".m3u8" in lowered
                or "playlist" in lowered
            ):

                return value

        # 5. onclick / SIDPlayer fallback
        for element in article.select(
            "[onclick]"
        ):

            onclick = element.get(
                "onclick"
            )

            if not onclick:
                continue

            if "SIDPlayer" not in onclick:
                continue

            # SIDPlayer itself does not contain the
            # audio URL, so do not invent one.
            # The URL must be obtained from rendered DOM.
            continue

        return None

    # ---------------------------------------------------------
    # Audio title
    # ---------------------------------------------------------

    @staticmethod
    def extract_audio_title(article):

        title_element = article.select_one(
            ".card-title"
        )

        description_element = article.select_one(
            ".text-content"
        )

        title = None
        description = None

        if title_element is not None:

            title = title_element.get_text(
                " ",
                strip=True
            )

        if description_element is not None:

            description = description_element.get_text(
                " ",
                strip=True
            )

        if title and description:

            return (
                f"{title} | {description}"
            )

        if title:
            return title

        if description:
            return description

        return None

    # ---------------------------------------------------------
    # Program title
    # ---------------------------------------------------------

    @staticmethod
    def extract_program_title(soup):

        json_ld = soup.select_one(
            'script[type="application/ld+json"]'
        )

        if json_ld is not None:

            text = json_ld.string

            if text:

                match = re.search(
                    r'"name"\s*:\s*"([^"]+)"',
                    text
                )

                if match:

                    value = match.group(
                        1
                    ).strip()

                    if value:
                        return value

        heading = soup.select_one(
            "h1"
        )

        if heading is not None:

            value = heading.get_text(
                " ",
                strip=True
            )

            if value:
                return value

        return None

    # ---------------------------------------------------------
    # Speaker
    # ---------------------------------------------------------

    @staticmethod
    def extract_speaker(soup):

        selectors = [
            "[class*='host']",
            "[class*='speaker']",
            "[class*='mojri']",
        ]

        for selector in selectors:

            element = soup.select_one(
                selector
            )

            if element is None:
                continue

            value = element.get_text(
                " ",
                strip=True
            )

            if value:
                return value

        return None

    # ---------------------------------------------------------
    # Published date
    # ---------------------------------------------------------

    @staticmethod
    def extract_date(article):

        selectors = [
            "time",
            "[class*='date']",
            "[class*='tarikh']",
        ]

        for selector in selectors:

            element = article.select_one(
                selector
            )

            if element is None:
                continue

            value = element.get_text(
                " ",
                strip=True
            )

            if not value:
                continue

            normalized = (
                IransedaCrawler.normalize_date(
                    value
                )
            )

            if normalized:
                return normalized

        # Search all visible text for Jalali date
        text = article.get_text(
            " ",
            strip=True
        )

        match = re.search(
            r"((?:13|14)\d{2}/\d{1,2}/\d{1,2})",
            text
        )

        if match:

            return (
                IransedaCrawler.normalize_date(
                    match.group(1)
                )
            )

        return None

    # ---------------------------------------------------------
    # Jalali -> Gregorian
    # ---------------------------------------------------------

    @staticmethod
    def normalize_date(value):

        if not value:
            return None

        value = value.strip()

        value = value.translate(
            str.maketrans(
                "۰۱۲۳۴۵۶۷۸۹",
                "0123456789"
            )
        )

        match = re.search(
            r"((?:13|14)\d{2})/(\d{1,2})/(\d{1,2})",
            value
        )

        if match is None:
            return None

        year = int(
            match.group(1)
        )

        month = int(
            match.group(2)
        )

        day = int(
            match.group(3)
        )

        try:

            date = jdatetime.date(
                year,
                month,
                day
            )

            return (
                date
                .togregorian()
                .isoformat()
            )

        except ValueError:

            return None

    # ---------------------------------------------------------
    # Image
    # ---------------------------------------------------------

    @staticmethod
    def extract_image_url(article):

        image = article.select_one(
            "img[src]"
        )

        if image is None:
            return None

        src = image.get(
            "src"
        )

        if not src:
            return None

        return urljoin(
            IransedaCrawler.WEB_BASE_URL,
            src
        )