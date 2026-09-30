import json
import re
from datetime import datetime
from urllib.parse import parse_qs, urljoin, urlparse

import jdatetime
from bs4 import BeautifulSoup

from crawlers.base_crawler import BaseCrawler, AudioItem


class IransedaCrawler(BaseCrawler):

    API_BASE_URL = "http://api.iranseda.ir"
    WEB_BASE_URL = "http://podcast.iranseda.ir"

    def __init__(self, start_url, **kwargs):
        super().__init__(
            start_url=start_url,
            **kwargs
        )

        self.items: list[AudioItem] = []

    # =========================================================
    # BROWSER FETCH
    # =========================================================

    def fetch(self, url):
        if self.browser is None:
            self.logger.error(
                "Browser is required for IranSeda crawler."
            )
            return None

        # -----------------------------------------------------
        # The homepage's HTML is an almost-empty SPA shell
        # (<div id="app"></div> + <script src="assets/js/app.js">).
        # BrowserFetcher.fetch() reads page.content() right after
        # "domcontentloaded", which fires before app.js has made
        # or resolved any request - so that shell, not the grid,
        # is what we'd get here every time, retried or not.
        #
        # app.js itself builds the grid from a JSON endpoint:
        # http://api.iranseda.ir/podcast/vitrin/ (confirmed by
        # capturing the page's own XHR/fetch calls). Its
        # Containers[].boxes[] shape is identical to
        # podcastepisodes, right down to the WebUrl/URL fields -
        # so for listing pages (is_target_path() False - in this
        # crawler's config, just the homepage), we discover
        # programs straight from that endpoint instead of the
        # DOM. extract_links() still runs afterwards (base_crawler
        # calls it unconditionally) but finds nothing new in the
        # shell below, which is fine - discovery already happened.
        # -----------------------------------------------------

        if not self.is_target_path(url):
            self.discover_from_vitrin()

        try:
            self.logger.info(
                "IranSeda browser fetch: %s",
                url
            )

            result = self.browser.fetch(url)

            if result is None:
                return None

            return {
                "url": result["url"],
                "status": result["status"],
                "content": result["content"],
                "headers": result["headers"],
                "method": "playwright",
            }

        except Exception as exc:
            self.logger.error(
                "IranSeda browser fetch failed | "
                "url=%s | error=%s",
                url,
                exc,
            )
            return None

    # =========================================================
    # VITRIN DISCOVERY (homepage grid, via its JSON endpoint)
    # =========================================================

    def discover_from_vitrin(self):

        url = f"{self.API_BASE_URL}/podcast/vitrin/"

        data = self.fetch_json(url)

        if data is None:
            self.logger.error(
                "Failed to fetch IranSeda vitrin listing | "
                "url=%s",
                url,
            )
            return

        # vitrin's Containers[].boxes[] shape - and the
        # WebUrl/URL fields on each box - are identical to
        # podcastepisodes, so the same helpers apply here.

        boxes = self.extract_episode_boxes(data)

        discovered = 0

        for box in boxes:

            program_url = self.extract_content_url(box)

            if not program_url:
                continue

            before = len(self.queued_urls)

            self.add_url(program_url)

            if len(self.queued_urls) > before:
                discovered += 1

        self.logger.info(
            "IranSeda vitrin discovery completed | "
            "url=%s | discovered=%s",
            url,
            discovered,
        )

    # =========================================================
    # LINK DISCOVERY
    # =========================================================

    def extract_links(self, soup, current_url):
        discovered = 0

        # -----------------------------------------------------
        # 1. Normal podcasthome links
        # -----------------------------------------------------

        for link in soup.select("a[href]"):

            href = link.get("href")

            if not href:
                continue

            full_url = urljoin(
                current_url,
                href
            )

            parsed = urlparse(full_url)

            if parsed.scheme not in ("http", "https"):
                continue

            if not self.is_same_domain(full_url):
                continue

            path = parsed.path.rstrip("/")

            if path != "/podcasthome":
                continue

            before = len(self.queued_urls)

            self.add_url(full_url)

            if len(self.queued_urls) > before:
                discovered += 1

        # -----------------------------------------------------
        # 2. SIDPlayer(serial_id, item_id)
        # -----------------------------------------------------

        for element in soup.select(
            "[onclick*='SIDPlayer']"
        ):

            onclick = element.get(
                "onclick",
                ""
            )

            match = re.search(
                r"SIDPlayer\(\s*(\d+)\s*,\s*(\d+)\s*\)",
                onclick
            )

            if match is None:
                continue

            serial_id = match.group(1)

            program_url = (
                f"{self.WEB_BASE_URL}"
                f"/podcasthome/"
                f"?p={serial_id}"
            )

            before = len(self.queued_urls)

            self.add_url(program_url)

            if len(self.queued_urls) > before:
                discovered += 1

        # -----------------------------------------------------
        # 3. data-id + podcasthome context
        # -----------------------------------------------------

        for element in soup.select(
            "[data-id]"
        ):

            data_id = element.get("data-id")

            if not data_id:
                continue

            parent = element.find_parent(
                "article"
            )

            if parent is None:
                continue

            if "podcasthome" not in (
                parent.get("class") or []
            ):
                continue

            # The program/serial id is normally available
            # from SIDPlayer in the same article.
            onclick_elements = parent.select(
                "[onclick*='SIDPlayer']"
            )

            for player in onclick_elements:

                onclick = player.get(
                    "onclick",
                    ""
                )

                match = re.search(
                    r"SIDPlayer\(\s*(\d+)\s*,\s*(\d+)\s*\)",
                    onclick
                )

                if match is None:
                    continue

                serial_id = match.group(1)

                program_url = (
                    f"{self.WEB_BASE_URL}"
                    f"/podcasthome/"
                    f"?p={serial_id}"
                )

                before = len(
                    self.queued_urls
                )

                self.add_url(
                    program_url
                )

                if len(
                    self.queued_urls
                ) > before:
                    discovered += 1

                break

        self.logger.info(
            "IranSeda link discovery completed | "
            "url=%s | discovered=%s",
            current_url,
            discovered,
        )

    # =========================================================
    # PARSE
    # =========================================================

    def parse(
        self,
        response,
        soup: BeautifulSoup
    ):

        program_id = self.extract_program_id(
            response["url"]
        )

        if program_id is None:
            self.logger.debug(
                "No IranSeda program id found | url=%s",
                response["url"]
            )
            return

        self.logger.info(
            "IranSeda program found | program_id=%s",
            program_id
        )

        program = self.fetch_program(
            program_id
        )

        if program is None:
            return

        speaker = self.extract_speaker(
            program
        )

        page_number = 1

        while page_number <= self.max_page:

            self.logger.info(
                "Fetching IranSeda episodes | "
                "program_id=%s | page=%s",
                program_id,
                page_number,
            )

            episodes = self.fetch_episodes(
                program_id,
                page_number
            )

            if episodes is None:
                break

            boxes = self.extract_episode_boxes(
                episodes
            )

            if not boxes:
                self.logger.debug(
                    "No IranSeda episodes found | "
                    "program_id=%s | page=%s",
                    program_id,
                    page_number,
                )
                break

            for episode in boxes:

                item = self.parse_episode(
                    episode=episode,
                    program=program,
                    speaker=speaker,
                )

                if item is None:
                    continue

                self.items.append(item)

                self.logger.info(
                    "IranSeda audio extracted | "
                    "content_id=%s | audio_title=%s",
                    item.content_id,
                    item.audio_title,
                )

            if not self.has_next_page(
                episodes,
                page_number
            ):
                break

            page_number += 1

    # =========================================================
    # PROGRAM
    # =========================================================

    @staticmethod
    def extract_program_id(url):

        query = parse_qs(
            urlparse(url).query
        )

        values = query.get("p")

        if not values:
            return None

        try:
            return int(values[0])

        except (TypeError, ValueError):
            return None

    def fetch_program(self, program_id):

        url = (
            f"{self.API_BASE_URL}"
            f"/podcast/podcasthome/"
            f"?p={program_id}"
        )

        program = self.fetch_json(url)

        if program is None:
            self.logger.error(
                "Failed to fetch IranSeda program via "
                "API and browser fallback | url=%s",
                url,
            )

        return program

    # =========================================================
    # EPISODES
    # =========================================================

    def fetch_episodes(
        self,
        program_id,
        page_number
    ):

        url = (
            f"{self.API_BASE_URL}"
            f"/podcast/podcastepisodes/"
            f"?p={program_id}"
            f"&pn={page_number}"
            f"&sf=0"
        )

        episodes = self.fetch_json(url)

        if episodes is None:
            self.logger.error(
                "Failed to fetch IranSeda episodes via "
                "API and browser fallback | url=%s",
                url,
            )

        return episodes

    # =========================================================
    # JSON FETCH: API first, browser fetch as a fallback
    # =========================================================
    #
    # fetch_program()/fetch_episodes() both need the same JSON
    # the api.iranseda.ir endpoints return. Calling that API
    # directly (fetch_json_via_api) is cheap and is tried first;
    # if it fails - a block on this host/IP, a timeout, a bad
    # response - the exact same URL is retried through the real
    # browser (fetch_json_via_browser), which presents as a
    # normal browser session and can succeed where a plain
    # request doesn't. This mirrors the HTTP-then-browser
    # fallback BaseCrawler.fetch() already uses for pages.
    # =========================================================

    def fetch_json(self, url):

        data = self.fetch_json_via_api(url)

        if data is not None:
            return data

        if self.browser is None:
            return None

        self.logger.info(
            "IranSeda API call failed, retrying "
            "via browser: %s",
            url,
        )

        return self.fetch_json_via_browser(url)

    def fetch_json_via_api(self, url):

        try:

            response = self.session.get(
                url,
                timeout=self.timeout,
            )

            response.raise_for_status()

            return response.json()

        except Exception as exc:

            self.logger.warning(
                "IranSeda API request failed | "
                "url=%s | error=%s",
                url,
                exc,
            )

            return None

    def fetch_json_via_browser(self, url):

        try:

            result = self.browser.fetch(url)

        except Exception as exc:

            self.logger.error(
                "IranSeda browser fetch (API fallback) "
                "failed | url=%s | error=%s",
                url,
                exc,
            )

            return None

        if result is None or not result.get("content"):
            return None

        return self.parse_json_content(
            result["content"],
            url,
        )

    def parse_json_content(self, content, url):

        if isinstance(content, bytes):
            text = content.decode(
                "utf-8",
                errors="replace",
            )
        else:
            text = content

        try:
            return json.loads(text)

        except (TypeError, ValueError):
            pass

        # A browser will sometimes wrap a raw JSON response in
        # a minimal HTML document (e.g. inside a <pre> tag).
        # Pull the text back out before giving up on it.

        try:

            soup = BeautifulSoup(
                text,
                "html.parser"
            )

            pre = soup.find("pre")

            raw = pre.get_text() if pre else soup.get_text()

            return json.loads(raw)

        except (TypeError, ValueError, AttributeError):

            self.logger.error(
                "Could not parse JSON from browser "
                "content | url=%s",
                url,
            )

            return None

    @staticmethod
    def extract_episode_boxes(episodes):

        containers = episodes.get(
            "Containers",
            []
        )

        boxes = []

        for container in containers:

            boxes.extend(
                container.get(
                    "boxes",
                    []
                )
            )

        return boxes

    # =========================================================
    # EPISODE PARSING
    # =========================================================

    def parse_episode(
        self,
        episode,
        program,
        speaker
    ):

        audio_url = self.extract_audio_url(
            episode
        )

        if audio_url is None:

            self.logger.debug(
                "No audio URL found in IranSeda episode."
            )

            return None

        content_id = self.extract_content_id(
            episode
        )

        title = self.extract_title(
            program
        )

        audio_title = self.extract_audio_title(
            episode
        )

        content_url = self.extract_content_url(
            episode
        )

        published_at = self.extract_date(
            episode
        )

        image_url = self.extract_image_url(
            episode
        )

        if content_url:
            self.add_url(
                content_url
            )

        return AudioItem(
            source="iranseda.ir",
            content_id=content_id,
            title=title,
            content_url=content_url,
            audio_url=audio_url,
            published_at=published_at,
            tags=None,
            crawled_at=datetime.now(),
            image_url=image_url,
            speaker=speaker,
            audio_title=audio_title,
        )

    # =========================================================
    # CONTENT ID
    # =========================================================

    @staticmethod
    def extract_content_id(episode):

        value = episode.get(
            "ItemID"
        )

        if value is None:
            return None

        try:
            return int(value)

        except (TypeError, ValueError):
            return None

    # =========================================================
    # TITLE
    # =========================================================

    @staticmethod
    def extract_title(program):

        value = program.get(
            "serialName"
        )

        if not value:
            return None

        return value.strip()

    # =========================================================
    # AUDIO TITLE
    # =========================================================

    @staticmethod
    def extract_audio_title(episode):

        title = episode.get(
            "title"
        )

        description = episode.get(
            "webdesc"
        )

        if isinstance(title, str):
            title = title.strip()

        if isinstance(description, str):
            description = description.strip()

        if title and description:
            return f"{title} | {description}"

        if title:
            return title

        if description:
            return description

        return None

    # =========================================================
    # CONTENT URL
    # =========================================================

    @classmethod
    def extract_content_url(cls, episode):

        web_url = episode.get(
            "WebUrl"
        )

        if web_url:

            return urljoin(
                cls.WEB_BASE_URL,
                web_url
            )

        return episode.get(
            "URL"
        )

    # =========================================================
    # AUDIO URL
    # =========================================================

    @staticmethod
    def extract_audio_url(episode):

        audio_url = episode.get(
            "playurl"
        )

        if audio_url:
            return audio_url

        items = episode.get(
            "items",
            []
        )

        for item in items:

            audio_url = item.get(
                "playUrl"
            )

            if audio_url:
                return audio_url

        return None

    # =========================================================
    # SPEAKER
    # =========================================================

    @staticmethod
    def extract_speaker(program):

        main_tags = program.get(
            "mainTags",
            []
        )

        for tag in main_tags:

            if tag.get(
                "tagname"
            ) == "میزبان/مجری":

                value = tag.get(
                    "tagvalue"
                )

                if value:
                    return value.strip()

        return None

    # =========================================================
    # DATE
    # =========================================================

    @staticmethod
    def extract_date(episode):

        tags = episode.get(
            "tags",
            []
        )

        for tag in tags:

            value = tag.get(
                "tagvalue"
            )

            if value:

                return IransedaCrawler.normalize_date(
                    value
                )

        return None

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

        match = re.fullmatch(
            r"(\d{4})/(\d{1,2})/(\d{1,2})",
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

            return date.togregorian().isoformat()

        except ValueError:
            return None

    # =========================================================
    # IMAGE
    # =========================================================

    @staticmethod
    def extract_image_url(episode):

        image_url = episode.get(
            "image"
        )

        if image_url:
            return image_url

        return episode.get(
            "image-cover"
        )

    # =========================================================
    # PAGINATION
    # =========================================================

    @staticmethod
    def has_next_page(
        episodes,
        current_page
    ):

        if str(
            episodes.get("Infinity")
        ).lower() != "true":

            return False

        try:

            page_number = int(
                episodes.get(
                    "PageNo",
                    current_page
                )
            )

        except (TypeError, ValueError):

            return False

        if page_number != current_page:
            return False

        containers = episodes.get(
            "Containers",
            []
        )

        count = sum(
            len(
                container.get(
                    "boxes",
                    []
                )
            )
            for container in containers
        )

        return count > 0