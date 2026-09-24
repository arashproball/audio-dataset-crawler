
import re
from datetime import datetime

from bs4 import BeautifulSoup

from crawlers.base_crawler import BaseCrawler, AudioItem


class VaezinCrawler(BaseCrawler):

    def __init__(self, start_url, **kwargs):
        super().__init__(
            start_url=start_url,
            **kwargs
        )

        self.items: list[AudioItem] = []

    def parse(self, response, soup: BeautifulSoup):

        articles = soup.select(
            "article.bokchrsimt"
        )

        if not articles:
            self.logger.debug(
                "No audio articles found: %s",
                response["url"]
            )
            return

        for article in articles:

            audio_container = self.find_audio_player(
                article
            )

            if audio_container is None:
                self.logger.debug(
                    "No audio container found in article: %s",
                    response["url"]
                )
                continue

            audio_url = self.extract_audio_url(
                audio_container
            )

            if audio_url is None:
                self.logger.debug(
                    "No audio URL found in article: %s",
                    response["url"]
                )
                continue

            content_id = self.extract_content_id(
                article
            )

            content_url = response["url"]

            audio_title = self.extract_audio_title(
                article
            )

            speaker = self.extract_speaker(
                article
            )

            image_url = self.extract_image_url(
                article
            )

            published_at = self.extract_date(
                article
            )

            item = AudioItem(
                source="vaezin.com",
                content_id=content_id,
                title=None,
                content_url=content_url,
                published_at=published_at,
                speaker=speaker,
                tags=None,
                image_url=image_url,
                audio_url=audio_url,
                crawled_at=datetime.now(),
                audio_title=audio_title,
            )

            self.items.append(item)

            self.logger.info(
                "Vaezin audio extracted | "
                f"content_id={content_id} | "
                f"audio_title={audio_title}"
            )

    @staticmethod
    def find_audio_player(article):

        return article.select_one(
            "div.bakplsoh"
        )

    @staticmethod
    def extract_audio_title(article):

        element = article.select_one(
            "h1.titlsohnh a"
        )

        if element is None:
            return None

        return element.get_text(
            " ",
            strip=True
        )

    @staticmethod
    def extract_content_id(article):

        element = article.select_one(
            "div.shorsoh"
        )

        if element is None:
            return None

        text = element.get_text(
            " ",
            strip=True
        )

        text = text.translate(
            str.maketrans(
                "۰۱۲۳۴۵۶۷۸۹",
                "0123456789"
            )
        )

        match = re.search(
            r"\d+",
            text
        )

        if match is None:
            return None

        return int(match.group())

    def extract_date(self, article):

        element = article.select_one(
            "div.tarkpso.shorsoh"
        )

        if element is None:
            return None

        value = element.get_text(
            " ",
            strip=True
        )

        value = value.replace(
            "تاریخ :",
            ""
        ).strip()

        return self.normalize_date(
            value
        )

    @staticmethod
    def normalize_date(value):

        month_map = {
            "ژانویه": "01",
            "فوریه": "02",
            "مارس": "03",
            "آوریل": "04",
            "می": "05",
            "ژوئن": "06",
            "جولای": "07",
            "آگوست": "08",
            "سپتامبر": "09",
            "اکتبر": "10",
            "نوامبر": "11",
            "دسامبر": "12",
        }

        value = value.strip()

        value = value.translate(
            str.maketrans(
                "۰۱۲۳۴۵۶۷۸۹",
                "0123456789"
            )
        )

        for month_name, month_number in month_map.items():

            if month_name not in value:
                continue

            parts = value.split()

            if len(parts) < 3:
                return None

            day = parts[0]
            year = parts[-1]

            return (
                f"{year}-"
                f"{month_number}-"
                f"{day.zfill(2)}"
            )

        return None

    @staticmethod
    def extract_speaker(article):

        element = article.select_one(
            "div.catsshn a"
        )

        if element is None:
            return None

        return element.get_text(
            " ",
            strip=True
        )

    @staticmethod
    def extract_image_url(article):

        image = article.select_one(
            "div.picsingsokh img"
        )

        if image is None:
            return None

        return image.get(
            "src"
        )

    @staticmethod
    def extract_audio_url(container):

        source = container.select_one(
            "audio source[src]"
        )

        if source is not None:

            src = source.get(
                "src"
            )

            if src:
                return src

        audio = container.select_one(
            "audio[src]"
        )

        if audio is not None:

            src = audio.get(
                "src"
            )

            if src:
                return src

        link = container.select_one(
            "a[href$='.mp3']"
        )

        if link is not None:

            href = link.get(
                "href"
            )

            if href:
                return href

        return None
