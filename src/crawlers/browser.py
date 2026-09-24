from playwright.sync_api import sync_playwright


class BrowserFetcher:
    def __init__(
        self,
        user_agent="TaskCrawler/1.0",
        headless=True,
        timeout=30000
    ):
        self.user_agent = user_agent
        self.headless = headless
        self.timeout = timeout

        self.playwright = None
        self.browser = None
        self.context = None

    def start(self):
        self.playwright = sync_playwright().start()

        self.browser = self.playwright.chromium.launch(
            headless=self.headless
        )

        self.context = self.browser.new_context(
            user_agent=self.user_agent,
            locale="fa-IR"
        )

        self.context.set_default_timeout(self.timeout)
        self.context.set_default_navigation_timeout(self.timeout)

    def fetch(self, url):

        if self.context is None:
            raise RuntimeError(
                "BrowserFetcher has not been started."
            )

        # مهم: page باید از context ساخته شود
        page = self.context.new_page()

        try:
            response = page.goto(
                url,
                wait_until="domcontentloaded",
                timeout=self.timeout
            )

            if response is None:
                return None

            return {
                "url": page.url,
                "status": response.status,
                "content": page.content(),
                "headers": response.headers,
            }

        finally:
            page.close()

    def close(self):

        if self.context:
            self.context.close()

        if self.browser:
            self.browser.close()

        if self.playwright:
            self.playwright.stop()

        self.context = None
        self.browser = None
        self.playwright = None