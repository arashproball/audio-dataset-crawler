# Audio Dataset Crawler

A modular Python-based crawler for collecting and preparing audio content from multiple Persian-language websites.

The project is designed as a practical data-collection pipeline with support for:

* Website crawling and link discovery
* `robots.txt` handling
* Polite crawling with configurable delays
* HTTP fetching with retry and exponential backoff
* Playwright browser fallback for JavaScript-driven or protected pages
* Resumable crawling through persistent crawler state
* Site-specific parsing
* Persian/Jalali date normalization
* PostgreSQL storage
* Duplicate detection and upsert
* Vector embeddings using `pgvector`
* CSV and Parquet export
* Semantic search over collected audio content

---

## 1. Project Structure

```text
interview task/
│
├── crawlers/
│   ├── __init__.py
│   ├── base_crawler.py
│   ├── browser.py
│   ├── khamenei.py
│   ├── vaezin.py
│   └── iranseda.py
│
├── src/
│   ├── database/
│   │   ├── connection.py
│   │   ├── models.py
│   │   └── repositories/
│   │       ├── audio_item_repository.py
│   │       └── crawl_run_repository.py
│   │
│   ├── cleaning/
│   │   └── audio_cleaner.py
│   │
│   ├── export/
│   │   └── exporter.py
│   │
│   └── analysis/
│       └── semantic_search.py
│
├── migrations/
│   └── versions/
│
├── tests/
│
├── state/
│   ├── khamenei.json
│   ├── vaezin.json
│   └── iranseda.json
│
├── exports/
│
├── .env
├── .gitignore
├── alembic.ini
├── requirements.txt
└── task.py
```

---

# 2. Architecture

The crawler is organized into several layers:

```text
                    ┌─────────────────────┐
                    │      task.py        │
                    │   Pipeline Runner   │
                    └──────────┬──────────┘
                               │
              ┌────────────────┼────────────────┐
              │                │                │
              ▼                ▼                ▼
       KhameneiCrawler   VaezinCrawler   IransedaCrawler
              │                │                │
              └────────────────┼────────────────┘
                               ▼
                        BaseCrawler
                               │
                 ┌─────────────┴─────────────┐
                 │                           │
                 ▼                           ▼
          HTTP Requests                Playwright
                 │                           │
                 └─────────────┬─────────────┘
                               ▼
                         Site Parser
                               │
                               ▼
                         AudioItem
                               │
                               ▼
                         AudioCleaner
                               │
                               ▼
                     PostgreSQL / pgvector
                               │
                 ┌─────────────┴─────────────┐
                 ▼                           ▼
             CSV/Parquet                Semantic Search
```

The generic crawling functionality is implemented in `BaseCrawler`, while website-specific behavior is isolated inside individual crawler classes.

---

# 3. Supported Websites

The current pipeline contains crawlers for:

* `farsi.khamenei.ir`
* `vaezin.com`
* `iranseda.ir`

Each website has a dedicated crawler because the HTML structure, pagination mechanism, and audio delivery mechanism differ between websites.

---

# 4. BaseCrawler

`BaseCrawler` provides common crawling functionality shared by all crawlers.

Its responsibilities include:

* URL normalization
* Domain restriction
* Target-path restriction
* URL queue management
* Duplicate URL prevention
* `robots.txt` loading
* HTTP requests
* Retry and exponential backoff
* Playwright fallback
* Generic link discovery
* Persistent crawl state
* Crawl delays
* Logging

The site-specific crawlers only implement the parsing logic required for their respective websites.

---

# 5. URL Discovery

URLs are maintained using:

```python
deque
```

along with:

```python
queued_urls
visited_urls
```

This prevents the same URL from being repeatedly added or crawled.

The crawler only follows URLs that:

1. Use `http` or `https`
2. Belong to the same domain
3. Satisfy the configured path restrictions
4. Have not already been visited
5. Have not already been queued

Fragments are removed during URL normalization so that:

```text
https://example.com/page#section1
https://example.com/page#section2
```

are treated as the same page.

---

# 6. Resumable Crawling

Crawler state is stored as JSON.

For example:

```text
state/khamenei.json
state/vaezin.json
state/iranseda.json
```

The state contains:

```json
{
    "queue": [],
    "queued_urls": [],
    "visited_urls": []
}
```

After completing a page, the state is saved.

This allows a crawling process interrupted by:

* system failure
* network failure
* process termination
* time limitations

to continue from its previous state.

The state can also be reset through the project configuration.

---

# 7. Robots.txt

Before crawling a URL, the crawler loads the site's `robots.txt`.

If `robots.txt` cannot be loaded, the crawler blocks the URL rather than continuing without the site's crawling policy.

This provides a conservative failure behavior.

---

# 8. Fetching Strategy

The crawler supports two fetching mechanisms.

## HTTP

Normal pages are initially fetched using `requests`.

Transient failures such as:

```text
408
429
500
502
503
504
```

are retried.

The retry mechanism uses exponential backoff with jitter.

Conceptually:

```text
attempt 1 → short delay
attempt 2 → longer delay
attempt 3 → longer delay
```

## Playwright

Playwright is used when a normal HTTP client is insufficient.

Typical cases include:

* JavaScript-rendered content
* browser-only content
* anti-bot/protection responses
* dynamically generated media
* pages whose useful content is created after page execution

The browser uses the configured crawler User-Agent.

---

# 9. Khamenei Crawler

The Khamenei crawler targets audio content from:

```text
farsi.khamenei.ir
```

The crawler identifies audio players through the site's audio-player structures and extracts information such as:

* content ID
* title
* content URL
* audio URL
* publication date
* tags
* image
* speaker
* audio title

The crawler supports several possible audio URL locations, including player data attributes, download links, and HTML audio sources.

Persian digits are normalized before date conversion.

Jalali dates are converted to Gregorian ISO dates.

---

# 10. Vaezin Crawler

The Vaezin crawler targets audio articles using the site's article structure.

Audio articles are identified through:

```css
article.bokchrsimt
```

Audio information is extracted from the corresponding player container.

The crawler collects:

* content ID
* audio title
* audio URL
* publication date
* speaker
* image URL

The site's textual date representation is normalized and converted to ISO Gregorian format.

---

# 11. IranSeda Crawler

IranSeda uses a more dynamic architecture than the other sources.

Episode pages contain player controls such as:

```text
SIDPlayer(...)
```

rather than exposing the final media URL directly in the static HTML.

Therefore, the crawler uses Playwright for IranSeda.

The general flow is:

```text
IranSeda page
      │
      ▼
Rendered episode DOM
      │
      ▼
Episode discovery
      │
      ▼
SIDPlayer interaction
      │
      ▼
Browser network activity
      │
      ▼
Media URL
      │
      ▼
AudioItem
```

The crawler does not construct or guess media URLs from filename or CDN patterns.

Instead, the URL is captured from browser network activity after the player is activated.

This is important because the media URL is dynamically generated by the site's player infrastructure.

---

# 12. Common AudioItem Schema

All crawlers normalize their results into the same data structure:

```python
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
```

This provides a common interface between crawlers and downstream processing.

---

# 13. Cleaning and Normalization

Generic cleaning is centralized in:

```text
src/cleaning/audio_cleaner.py
```

The purpose of this separation is to prevent website-specific crawlers from duplicating generic data-cleaning logic.

Crawler-specific transformations are kept in the crawler only when they are required to correctly interpret the source website.

Examples include:

* resolving relative URLs
* converting Jalali dates
* normalizing Persian digits before date conversion

---

# 14. Database

The project uses PostgreSQL.

The database currently contains two main tables:

```text
audio_items
crawl_runs
```

## audio_items

Stores normalized audio records.

Important fields include:

```text
id
source
content_id
title
content_url
audio_url
published_at
tags
crawled_at
image_url
speaker
audio_title
embedding
```

A uniqueness constraint prevents duplicate audio records for the same source and audio URL:

```text
(source, audio_url)
```

---

# 15. Crawl Runs

The `crawl_runs` table records execution-level metadata.

It contains:

```text
id
source
started_at
finished_at
pages_crawled
items_found
items_inserted
items_updated
errors
```

This allows crawl executions to be monitored independently from the collected content.

---

# 16. Database Upsert

Collected items are inserted or updated using the repository layer.

The uniqueness rule:

```text
(source, audio_url)
```

is used to identify an existing audio item.

The repository returns whether a record was inserted or updated, allowing crawl statistics to be recorded.

---

# 17. Vector Search

The project uses PostgreSQL `pgvector`.

The `audio_items` table contains:

```text
embedding VECTOR(384)
```

Embeddings are generated using:

```text
intfloat/multilingual-e5-small
```

The model produces 384-dimensional embeddings and supports multilingual text.

The embedding is generated from the cleaned textual information associated with each audio item.

This enables semantic retrieval rather than relying only on exact keyword matching.

---

# 18. Semantic Search

The semantic search pipeline is conceptually:

```text
User query
    │
    ▼
Multilingual embedding model
    │
    ▼
384-dimensional vector
    │
    ▼
PostgreSQL / pgvector
    │
    ▼
Nearest audio items
```

For example, a query about a specific topic can retrieve semantically related audio content even when the exact query words do not appear in the title.

---

# 19. Export

The collected dataset can be exported into:

```text
CSV
Parquet
```

These formats make the dataset suitable for:

* exploratory data analysis
* Python/Pandas workflows
* machine-learning experiments
* external data processing
* dataset delivery

A data dictionary is also included to document the meaning and expected type of each exported field.

---

# 20. Configuration

Runtime configuration is stored in `.env`.

Example:

```env
DATABASE_URL=postgresql+psycopg2://crawler_user:crawler_password@localhost:5432/audio_dataset

USER_AGENT=TaskCrawler/1.0

CRAWLER_DELAY=2
CRAWLER_MAX_RETRIES=3
CRAWLER_USE_BROWSER_FALLBACK=true

RESET_STATE=false

KHAMENEI_START_URL=https://farsi.khamenei.ir
KHAMENEI_MAX_PAGE=10
KHAMENEI_TIMEOUT=3
KHAMENEI_STATE_FILE=state/khamenei.json
KHAMENEI_PATH_FLAG=true
KHAMENEI_INCLUDE_PATHS=/audio-content,/audio-index

VAEZIN_START_URL=https://vaezin.com/
VAEZIN_MAX_PAGE=10
VAEZIN_TIMEOUT=10
VAEZIN_STATE_FILE=state/vaezin.json

IRANSEDA_START_URL=http://podcast.iranseda.ir/podcasthome/?p=6118
IRANSEDA_MAX_PAGE=10
IRANSEDA_TIMEOUT=30
IRANSEDA_STATE_FILE=state/iranseda.json
```

Credentials and environment-specific values should not be committed to the repository.

---

# 21. Running the Project

Activate the project environment:

```bash
conda activate task
```

Then run:

```bash
python task.py
```

Alternatively, using the full environment path:

```bash
conda run -p /home/arash/anaconda3/envs/task \
    --no-capture-output \
    python task.py
```

---

# 22. Resetting Crawler State

To start a crawler from the beginning, its state file can be reset.

For example:

```text
state/iranseda.json
```

After resetting, the crawler starts again from the configured `START_URL`.

State reset should be used carefully because it removes the crawler's knowledge of previously visited URLs.

---

# 23. Logging

The crawler uses Python's standard logging framework.

Example:

```text
2026-09-24 17:59:14 | INFO | IransedaCrawler | Crawling: ...
```

Logs provide information about:

* crawler startup
* state loading
* URL fetching
* retries
* browser fallback
* page completion
* discovered URLs
* extracted audio items
* database operations
* errors

This makes failures easier to diagnose during long-running crawls.

---

# 24. Politeness and Reliability

The crawler supports:

* configurable request delay
* identifiable User-Agent
* retry limits
* exponential backoff
* persistent state
* duplicate URL prevention
* robots.txt checking
* browser fallback

The goal is to reduce unnecessary requests and make the crawling process recoverable.

---

# 25. Testing

Site-specific parsing and cleaning logic should be tested independently from network access.

Tests should cover cases such as:

* valid HTML structures
* missing fields
* malformed dates
* Persian digits
* relative URLs
* missing audio URLs
* duplicate records
* invalid content IDs

Network-dependent crawling should not be required for ordinary parser unit tests.

---

# 26. Data Pipeline

The complete data pipeline is:

```text
Websites
   │
   ▼
Discovery
   │
   ▼
robots.txt check
   │
   ▼
Fetch
 ┌─┴─────────────┐
 │               │
HTTP          Playwright
 │               │
 └──────┬────────┘
        ▼
Site-specific parsing
        │
        ▼
AudioItem
        │
        ▼
Cleaning / normalization
        │
        ▼
PostgreSQL
        │
   ┌────┴─────┐
   ▼          ▼
Export     Embedding
CSV        pgvector
Parquet       │
              ▼
       Semantic Search
```

---

# 27. Design Principles

The implementation follows several principles:

### Separation of concerns

Generic crawling behavior is kept in `BaseCrawler`.

Website-specific parsing is implemented in individual crawler classes.

Cleaning and storage are separated from crawling.

### Resumability

Crawler state is persisted so interrupted jobs can continue.

### Defensive parsing

Missing or malformed fields should not terminate the entire crawl.

### No URL guessing

Dynamic media URLs, particularly on IranSeda, are captured from the site's actual browser/network behavior rather than being constructed from observed URL patterns.

### Consistent data model

All sources are converted into the same `AudioItem` schema.

### Reproducibility

Crawler configuration, database migrations, exports, and execution metadata are kept separate from source-specific implementation details.

---

# 28. Current Dataset

The pipeline currently supports storing normalized records from the supported sources in a shared PostgreSQL dataset.

The collected records can then be:

1. cleaned,
2. stored,
3. embedded,
4. exported,
5. searched semantically.

This allows the crawler to serve as the first stage of a larger audio-data analysis and machine-learning pipeline.

---

# 29. Limitations

The websites have different technical architectures, so crawling behavior is not identical across sources.

In particular:

* some content is available through normal HTTP responses;
* some pages require browser rendering;
* some media URLs are generated dynamically;
* website HTML structures may change over time.

Therefore, each site-specific crawler intentionally contains its own parsing rules while sharing the common crawling infrastructure.

---

# 30. Future Improvements

Possible future improvements include:

* richer crawl monitoring
* additional parser tests
* more detailed crawl metrics
* concurrent crawling with per-domain rate limiting
* improved media metadata extraction
* scheduled incremental crawls
* more advanced semantic retrieval
* audio transcription and speech-to-text processing
* audio-level embeddings
* analytical dashboards

These extensions can be added without changing the common `AudioItem` data contract.
