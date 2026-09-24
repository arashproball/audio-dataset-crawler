from datetime import datetime

from src.database.connection import Base, SessionLocal, engine
from src.database.crawl_run_repository import CrawlRunRepository


def test_crawl_run_repository():

    Base.metadata.create_all(engine)

    session = SessionLocal()

    try:
        repository = CrawlRunRepository(session)

        print("\nSTART CRAWL RUN")

        crawl_run = repository.start(
            source="farsi.khamenei.ir"
        )

        session.commit()

        print("ID:", crawl_run.id)
        print("Source:", crawl_run.source)
        print("Started:", crawl_run.started_at)

        assert crawl_run.id is not None
        assert crawl_run.source == "farsi.khamenei.ir"
        assert isinstance(crawl_run.started_at, datetime)

        print("START: OK")

        print("\nFINISH CRAWL RUN")

        repository.finish(
            crawl_run=crawl_run,
            pages_crawled=25,
            items_found=40,
            items_inserted=35,
            items_updated=5,
            errors=2,
        )

        session.commit()

        print("Finished:", crawl_run.finished_at)
        print("Pages:", crawl_run.pages_crawled)
        print("Items found:", crawl_run.items_found)
        print("Items inserted:", crawl_run.items_inserted)
        print("Items updated:", crawl_run.items_updated)
        print("Errors:", crawl_run.errors)

        assert crawl_run.finished_at is not None
        assert crawl_run.pages_crawled == 25
        assert crawl_run.items_found == 40
        assert crawl_run.items_inserted == 35
        assert crawl_run.items_updated == 5
        assert crawl_run.errors == 2

        print("FINISH: OK")

    finally:
        session.close()


if __name__ == "__main__":
    test_crawl_run_repository()