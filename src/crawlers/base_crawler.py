
from collections import deque
from dataclasses import dataclass
from typing import Optional
from urllib.parse import urljoin, urlparse, urlunparse
from urllib import robotparser
from datetime import datetime

import json
import os
import time
import random
import logging
import requests
from bs4 import BeautifulSoup

from crawlers.browser import BrowserFetcher


logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)s | %(name)s | %(message)s"
)


def normalize_url(url):
    parsed_url = urlparse(url)

    return urlunparse((
        parsed_url.scheme.lower(),
        parsed_url.netloc.lower(),
        parsed_url.path or "/",
        parsed_url.params,
        parsed_url.query,
        ""
    ))


def sleep_backoff(attempt):
    delay = 2 ** (attempt - 1)
    jitter = random.uniform(0, 0.5)

    time.sleep(delay + jitter)

@dataclass
class AudioItem:

    source: str

    content_id: Optional[int]

    title: Optional[str]

    content_url: str

    audio_url: str

    published_at: Optional[str]

    tags: Optional[list[str]]

    crawled_at: datetime

    image_url: Optional[str]

    speaker: Optional[str]

    audio_title: Optional[str]

class BaseCrawler:

    def __init__(
        self,
        start_url,
        user_agent="TaskCrawler/1.0",
        delay=2,
        max_page=100,
        max_retries=3,
        use_browser_fallback=True,
        timeout=3,
        include_paths = None,
        state_file = "crawler_state.json",
        path_flag = False
    ):

        self.start_url = normalize_url(start_url)

        self.user_agent = user_agent
        self.delay = delay
        self.max_page = max_page
        self.max_retries = max_retries
        self.use_browser_fallback = use_browser_fallback
        self.timeout = timeout
        self.include_paths = include_paths
        self.state_file = state_file
        self.path_flag = path_flag

        self.queue = deque()
        self.queued_urls = set()
        self.visited_urls = set()

        # -------------------------
        # HTTP session
        # -------------------------

        self.session = requests.Session()

        self.session.headers.update({
            "User-Agent": self.user_agent,
            "Accept-Language": "fa-IR,fa;q=0.9,en-US;q=0.8",
            "Accept": (
                "text/html,application/xhtml+xml,"
                "application/xml;q=0.9,*/*;q=0.8"
            ),
        })

        # -------------------------
        # robots.txt cache
        # -------------------------

        self.robots = {}

        # -------------------------
        # Browser fallback
        # -------------------------

        self.browser = None

        if self.use_browser_fallback:
            self.browser = BrowserFetcher(
                user_agent=self.user_agent
            )

        # -------------------------
        # Logger
        # -------------------------

        self.logger = logging.getLogger(
            self.__class__.__name__
        )

        # -------------------------
        # Initial URL
        # -------------------------

        self.load_state()

        if not self.queue:
            self.queue.append(self.start_url)


    def save_state(self):
        state = {
            "queue": list(self.queue),
            "queued_urls": list(self.queued_urls),
            "visited_urls": list(self.visited_urls),
        }

        temp_file = self.state_file + ".tmp"

        with open(temp_file, "w", encoding="utf-8") as f:
            json.dump(
                state,
                f,
                ensure_ascii=False,
                indent=2
            )

        os.replace(temp_file, self.state_file)

        self.logger.info(
            "Crawler state saved | queue=%s | visited=%s",
            len(self.queue),
            len(self.visited_urls)
        )

    def load_state(self):
        if not os.path.exists(self.state_file):
            self.logger.info(
                "No crawler state found: %s",
                self.state_file
            )
            return

        try:
            with open(self.state_file, "r", encoding="utf-8") as f:
                state = json.load(f)

            self.queue = deque(state.get("queue", []))
            self.queued_urls = set(
                state.get("queued_urls", [])
            )
            self.visited_urls = set(
                state.get("visited_urls", [])
            )

            self.logger.info(
                "Crawler state loaded | queue=%s | visited=%s",
                len(self.queue),
                len(self.visited_urls)
            )

        except (OSError, json.JSONDecodeError) as e:
            self.logger.error(
                "Could not load crawler state: %s",
                e
            )

    def reset_state(self):
        if os.path.exists(self.state_file):
            os.remove(self.state_file)

            self.logger.info(
                "Crawler state reset: %s",
                self.state_file
            )
        else:
            self.logger.info(
                "No crawler state to reset: %s",
                self.state_file
            )

        self.queue.clear()
        self.queued_urls.clear()
        self.visited_urls.clear()

        self.queue.append(self.start_url)

    def is_same_domain(self, url):

        start_domain = urlparse(self.start_url).netloc

        current_domain = urlparse(url).netloc

        return current_domain == start_domain

    def is_target_path(self, url):

        if not self.include_paths:
            return True

        current = urlparse(url)

        current_path = current.path.rstrip("/")

        for target_path in self.include_paths:

            target_path = target_path.rstrip("/")

            if (
                    current.netloc == urlparse(self.start_url).netloc
                    and (
                    current_path == target_path
                    or current_path.startswith(target_path + "/")
            )
            ):
                return True

        return False

    def add_url(self, url):

        url = normalize_url(url)

        # Only HTTP/HTTPS
        parsed_url = urlparse(url)

        if parsed_url.scheme not in ("http", "https"):
            return

        # Same domain only
        if not self.is_same_domain(url):
            return

        if not self.is_target_path(url) and self.path_flag:
            return
        # Already processed
        if url in self.visited_urls:
            return

        # Already waiting in queue
        if url in self.queued_urls:
            return

        self.queue.append(url)
        self.queued_urls.add(url)

    # =========================================================
    # robots.txt
    # =========================================================

    def get_robots(self, url):

        parsed_url = urlparse(url)

        base_url = (
            f"{parsed_url.scheme}://"
            f"{parsed_url.netloc}"
        )

        robots_url = f"{base_url}/robots.txt"

        if base_url not in self.robots:

            rp = robotparser.RobotFileParser()
            rp.set_url(robots_url)

            try:

                rp.read()

                self.robots[base_url] = rp

                self.logger.info(
                    "Loaded robots.txt: %s",
                    robots_url
                )

            except Exception as e:

                self.logger.warning(
                    "Could not read robots.txt %s: %s",
                    robots_url,
                    e
                )

                self.robots[base_url] = None

        return self.robots[base_url]

    def can_fetch(self, url):

        rp = self.get_robots(url)

        if rp is None:

            self.logger.warning(
                "robots.txt unavailable. Blocking URL: %s",
                url
            )

            return False
        return True
        # return rp.can_fetch(
        #     self.user_agent,
        #     url
        # )

    # =========================================================
    # HTTP
    # =========================================================

    def fetch_http(self, url):

        last_exception = None

        for attempt in range(
            1,
            self.max_retries + 1
        ):

            self.logger.info(
                "HTTP attempt %s/%s: %s",
                attempt,
                self.max_retries,
                url
            )

            try:

                response = self.session.get(
                    url,
                    timeout=self.timeout
                )

                status = response.status_code

                # -------------------------
                # Success
                # -------------------------

                if status == 200:

                    return {
                        "url": response.url,
                        "status": status,
                        "content": response.content,
                        "headers": response.headers,
                        "method": "request"
                    }

                # -------------------------
                # Retryable status codes
                # -------------------------

                if status in {
                    408,
                    429,
                    500,
                    502,
                    503,
                    504
                }:

                    self.logger.warning(
                        "HTTP %s for %s "
                        "(attempt %s/%s)",
                        status,
                        url,
                        attempt,
                        self.max_retries
                    )

                    if attempt < self.max_retries:
                        sleep_backoff(attempt)

                    continue

                # -------------------------
                # Non-retryable status
                # -------------------------

                self.logger.warning(
                    "HTTP %s for %s. "
                    "Not retrying.",
                    status,
                    url
                )

                return {
                    "url": response.url,
                    "status": status,
                    "content": response.content,
                    "headers": response.headers,
                    "method": "request"
                }

            except requests.RequestException as e:

                last_exception = e

                self.logger.warning(
                    "Request failed for %s "
                    "(attempt %s/%s): %s",
                    url,
                    attempt,
                    self.max_retries,
                    e
                )

                if attempt < self.max_retries:
                    sleep_backoff(attempt)

        # -------------------------
        # All retries failed
        # -------------------------

        self.logger.error(
            "HTTP fetch failed permanently: %s",
            last_exception
        )

        return None

    # =========================================================
    # Browser
    # =========================================================

    def fetch_browser(self, url):

        if self.browser is None:
            return None

        try:

            self.logger.info(
                "Browser fetch started: %s",
                url
            )

            result = self.browser.fetch(url)

            if result is None:
                return None

            self.logger.info(
                "Browser returned status=%s url=%s",
                result["status"],
                result["url"]
            )

            return {
                "url": result["url"],
                "status": result["status"],
                "content": result["content"],
                "headers": result["headers"],
                "method": "playwright"
            }

        except Exception as e:

            self.logger.error(
                "Browser fetch failed for %s: %s",
                url,
                e
            )

            return None

    # =========================================================
    # Fetch strategy
    # =========================================================

    def fetch(self, url):

        result = self.fetch_http(url)

        # -----------------------------------------------------
        # HTTP completely failed
        # -----------------------------------------------------

        if result is None:

            if self.use_browser_fallback:

                self.logger.info(
                    "HTTP fetch failed. "
                    "Trying browser: %s",
                    url
                )

                return self.fetch_browser(url)

            return None

        status = result["status"]

        # -----------------------------------------------------
        # HTTP client blocked
        # -----------------------------------------------------

        if (
            self.use_browser_fallback
            and status in {401, 403}
        ):

            self.logger.info(
                "HTTP client blocked for %s "
                "(status=%s). Trying browser.",
                url,
                status
            )

            browser_result = self.fetch_browser(url)

            if browser_result is not None:
                return browser_result

        # -----------------------------------------------------
        # Return HTTP result
        # -----------------------------------------------------

        return result

    # =========================================================
    # Link extraction
    # =========================================================

    def extract_links(
        self,
        soup,
        current_url
    ):

        links = soup.select("a[href]")

        for link in links:

            href = link.get("href")

            if not href:
                continue

            full_url = urljoin(
                current_url,
                href
            )

            parsed_url = urlparse(
                full_url
            )

            if parsed_url.scheme not in (
                "http",
                "https"
            ):
                continue

            self.add_url(full_url)

    # =========================================================
    # Parser
    # =========================================================

    def parse(
        self,
        response,
        soup
    ):

        raise NotImplementedError

    # =========================================================
    # Crawl
    # =========================================================

    def crawl(self):

        pages = 0

        if self.browser:
            self.browser.start()

        try:

            while self.queue:

                # -------------------------
                # Max pages
                # -------------------------

                if pages >= self.max_page:

                    self.logger.info(
                        "Max pages reached: %s",
                        self.max_page
                    )

                    break

                # -------------------------
                # Get next URL
                # -------------------------

                current_url = self.queue.popleft()

                if current_url in self.visited_urls:
                    continue

                self.logger.info(
                    "Crawling: %s",
                    current_url
                )

                # -------------------------
                # robots.txt
                # -------------------------

                if not self.can_fetch(
                    current_url
                ):

                    self.logger.warning(
                        "Blocked by robots.txt: %s",
                        current_url
                    )

                    self.visited_urls.add(
                        current_url
                    )

                    continue

                # -------------------------
                # Fetch
                # -------------------------

                result = self.fetch(
                    current_url
                )

                if result is None:

                    self.logger.error(
                        "Could not fetch: %s",
                        current_url
                    )

                    continue

                # -------------------------
                # Mark visited
                # -------------------------

                self.visited_urls.add(
                    current_url
                )

                # -------------------------
                # Parse
                # -------------------------

                soup = BeautifulSoup(
                    result["content"],
                    "html.parser"
                )

                if self.is_target_path(result["url"]):
                    self.parse(
                        result,
                        soup
                    )
                    pages += 1

                self.extract_links(
                    soup,
                    result["url"]
                )

                self.save_state()

                self.logger.info(
                    "Page completed: %s | "
                    "method=%s | pages=%s | queue=%s",
                    current_url,
                    result["method"],
                    pages,
                    len(self.queue)
                )

                # -------------------------
                # Rate limiting
                # -------------------------

                if self.delay > 0:
                    time.sleep(
                        self.delay
                    )

        finally:

            if self.browser:
                self.browser.close()