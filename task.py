import os
import logging

from dotenv import load_dotenv

from cleaning.cleaner import AudioCleaner

from crawlers.ir import IransedaCrawler
from crawlers.kh import KhameneiCrawler
from crawlers.va import VaezinCrawler

from database.connection import SessionLocal
from database.repository import AudioRepository
from database.crawl_run_repository import CrawlRunRepository


load_dotenv()


# ============================================================
# Environment helpers
# ============================================================

def get_bool_env(name, default=False):
    value = os.getenv(name)

    if value is None:
        return default

    return value.lower() in {
        "true",
        "1",
        "yes",
        "y",
        "on",
    }


# ============================================================
# Global crawler configuration
# ============================================================

USER_AGENT = os.getenv(
    "USER_AGENT",
    "TaskCrawler/1.0",
)

CRAWLER_DELAY = float(
    os.getenv(
        "CRAWLER_DELAY",
        "2",
    )
)

CRAWLER_MAX_RETRIES = int(
    os.getenv(
        "CRAWLER_MAX_RETRIES",
        "3",
    )
)

CRAWLER_USE_BROWSER_FALLBACK = get_bool_env(
    "CRAWLER_USE_BROWSER_FALLBACK",
    True,
)

RESET_STATE = get_bool_env(
    "RESET_STATE",
    False,
)


# ============================================================
# Khamenei configuration
# ============================================================

KHAMENEI_START_URL = os.getenv(
    "KHAMENEI_START_URL",
)

KHAMENEI_MAX_PAGE = int(
    os.getenv(
        "KHAMENEI_MAX_PAGE",
        "10",
    )
)

KHAMENEI_TIMEOUT = int(
    os.getenv(
        "KHAMENEI_TIMEOUT",
        "3",
    )
)

KHAMENEI_STATE_FILE = os.getenv(
    "KHAMENEI_STATE_FILE",
    "state/khamenei.json",
)

KHAMENEI_PATH_FLAG = get_bool_env(
    "KHAMENEI_PATH_FLAG",
    True,
)

KHAMENEI_INCLUDE_PATHS = os.getenv(
    "KHAMENEI_INCLUDE_PATHS",
    "/audio-content,/audio-index",
).split(",")

KHAMENEI_SOURCE = os.getenv(
    "KHAMENEI_SOURCE",
    "farsi.khamenei.ir",
)


# ============================================================
# Vaezin configuration
# ============================================================

VAEZIN_START_URL = os.getenv(
    "VAEZIN_START_URL",
)

VAEZIN_MAX_PAGE = int(
    os.getenv(
        "VAEZIN_MAX_PAGE",
        "10",
    )
)

VAEZIN_TIMEOUT = int(
    os.getenv(
        "VAEZIN_TIMEOUT",
        "10",
    )
)

VAEZIN_STATE_FILE = os.getenv(
    "VAEZIN_STATE_FILE",
    "state/vaezin.json",
)

VAEZIN_SOURCE = os.getenv(
    "VAEZIN_SOURCE",
    "vaezin.com",
)


# ============================================================
# IranSeda configuration
# ============================================================

IRANSEDA_START_URL = os.getenv(
    "IRANSEDA_START_URL",
)

IRANSEDA_MAX_PAGE = int(
    os.getenv(
        "IRANSEDA_MAX_PAGE",
        "10",
    )
)

IRANSEDA_TIMEOUT = int(
    os.getenv(
        "IRANSEDA_TIMEOUT",
        "30",
    )
)

IRANSEDA_STATE_FILE = os.getenv(
    "IRANSEDA_STATE_FILE",
    "state/iranseda.json",
)

IRANSEDA_SOURCE = os.getenv(
    "IRANSEDA_SOURCE",
    "iranseda.ir",
)


# ============================================================
# Output
# ============================================================

def print_item(item):

    print()

    print("SOURCE      :", item.source)
    print("CONTENT ID  :", item.content_id)
    print("TITLE       :", item.title)
    print("AUDIO TITLE :", item.audio_title)
    print("CONTENT URL :", item.content_url)
    print("AUDIO URL   :", item.audio_url)
    print("PUBLISHED AT:", item.published_at)
    print("IMAGE       :", item.image_url)
    print("SPEAKER     :", item.speaker)
    print("TAGS        :", item.tags)
    print("CRAWLED AT  :", item.crawled_at)


# ============================================================
# Common crawler runner
# ============================================================

def run_crawler(
    crawler,
    cleaner,
    source,
):

    with SessionLocal() as session:

        crawl_repository = CrawlRunRepository(
            session
        )

        crawl_run = crawl_repository.start(
            source
        )

        errors = 0
        items_found = 0
        inserted = 0
        updated = 0
        pages_crawled = 0

        try:

            # ------------------------------------------------
            # Crawl
            # ------------------------------------------------

            crawler.crawl()

            # ------------------------------------------------
            # Crawling statistics
            # ------------------------------------------------

            items_found = len(
                crawler.items
            )

            pages_crawled = len(
                crawler.visited_urls
            )

            # ------------------------------------------------
            # Clean + store
            # ------------------------------------------------

            repository = AudioRepository(
                session
            )

            for item in crawler.items:

                cleaned = cleaner.clean(
                    item
                )

                if cleaned is None:
                    continue

                print_item(
                    cleaned
                )

                _, is_inserted = (
                    repository.add_or_update(
                        cleaned
                    )
                )

                if is_inserted:
                    inserted += 1
                else:
                    updated += 1

        except Exception as e:

            errors = 1

            logger = logging.getLogger(
                crawler.__class__.__name__
            )

            logger.exception(
                "Crawler run failed: %s",
                e,
            )

            pages_crawled = len(
                crawler.visited_urls
            )

        # ----------------------------------------------------
        # Finish crawl run
        # ----------------------------------------------------

        crawl_repository.finish(
            crawl_run=crawl_run,
            pages_crawled=pages_crawled,
            items_found=items_found,
            items_inserted=inserted,
            items_updated=updated,
            errors=errors,
        )

        session.commit()


# ============================================================
# Main
# ============================================================

if __name__ == "__main__":

    cleaner = AudioCleaner()


    # ========================================================
    # Vaezin
    # ========================================================

    crawler_vaezin = VaezinCrawler(
        start_url=VAEZIN_START_URL,

        user_agent=USER_AGENT,

        delay=CRAWLER_DELAY,

        max_page=VAEZIN_MAX_PAGE,

        max_retries=CRAWLER_MAX_RETRIES,

        use_browser_fallback=(
            CRAWLER_USE_BROWSER_FALLBACK
        ),

        timeout=VAEZIN_TIMEOUT,

        state_file=VAEZIN_STATE_FILE,
    )

    if RESET_STATE:

        crawler_vaezin.reset_state()

    run_crawler(
        crawler_vaezin,
        cleaner,
        VAEZIN_SOURCE,
    )


    # ========================================================
    # Khamenei
    # ========================================================

    crawler_khamenei = KhameneiCrawler(
        start_url=KHAMENEI_START_URL,

        user_agent=USER_AGENT,

        delay=CRAWLER_DELAY,

        max_page=KHAMENEI_MAX_PAGE,

        max_retries=CRAWLER_MAX_RETRIES,

        timeout=KHAMENEI_TIMEOUT,

        use_browser_fallback=(
            CRAWLER_USE_BROWSER_FALLBACK
        ),

        include_paths=KHAMENEI_INCLUDE_PATHS,

        path_flag=KHAMENEI_PATH_FLAG,

        state_file=KHAMENEI_STATE_FILE,
    )

    if RESET_STATE:

        crawler_khamenei.reset_state()

    run_crawler(
        crawler_khamenei,
        cleaner,
        KHAMENEI_SOURCE,
    )


    # ========================================================
    # IranSeda
    # ========================================================

    crawler_iranseda = IransedaCrawler(
        start_url=IRANSEDA_START_URL,

        user_agent=USER_AGENT,

        delay=CRAWLER_DELAY,

        max_page=IRANSEDA_MAX_PAGE,

        max_retries=CRAWLER_MAX_RETRIES,

        use_browser_fallback=(
            CRAWLER_USE_BROWSER_FALLBACK
        ),
        include_paths=["/podcasthome/"],
        timeout=IRANSEDA_TIMEOUT,
        path_flag=True,

        state_file=IRANSEDA_STATE_FILE,
    )

    if RESET_STATE:

        crawler_iranseda.reset_state()

    run_crawler(
        crawler_iranseda,
        cleaner,
        IRANSEDA_SOURCE,
    )

