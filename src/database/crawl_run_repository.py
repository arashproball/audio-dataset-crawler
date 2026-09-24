from datetime import datetime, timezone

from sqlalchemy.orm import Session

from src.database.models import CrawlRun


class CrawlRunRepository:

    def __init__(self, session: Session):
        self.session = session

    def start(self, source: str) -> CrawlRun:
        crawl_run = CrawlRun(
            source=source,
            started_at=datetime.now(timezone.utc),
            pages_crawled=0,
            items_found=0,
            items_inserted=0,
            items_updated=0,
            errors=0,
        )

        self.session.add(crawl_run)
        self.session.flush()

        return crawl_run

    def finish(
        self,
        crawl_run: CrawlRun,
        pages_crawled: int,
        items_found: int,
        items_inserted: int,
        items_updated: int,
        errors: int,
    ) -> CrawlRun:

        crawl_run.finished_at = datetime.now(timezone.utc)

        crawl_run.pages_crawled = pages_crawled
        crawl_run.items_found = items_found
        crawl_run.items_inserted = items_inserted
        crawl_run.items_updated = items_updated
        crawl_run.errors = errors

        self.session.flush()

        return crawl_run