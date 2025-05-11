# Define here the models for your scraped items
#
# See documentation in:
# https://docs.scrapy.org/en/latest/topics/items.html

import scrapy
from itemloaders.processors import TakeFirst, MapCompose, Join, Identity
import re

def sanitize_text(text):
    """Return sanitized text."""
    if not text:
        return ""
    text = re.sub(r"\s+", " ", text).strip()
    return text

def extract_keywords(keywords_str):
    """Extract keywords from a comma-separated string."""
    if not keywords_str:
        return []
    # Split, strip whitespace, and filter empty strings
    return [kw.strip() for kw in keywords_str.split(",") if kw.strip()]

class SnipdexItem(scrapy.Item):
    # Required fields
    url = scrapy.Field(output_processor=TakeFirst())
    status_code = scrapy.Field(output_processor=TakeFirst())
    timestamp = scrapy.Field(output_processor=TakeFirst())
    
    # Content
    title = scrapy.Field(
        input_processor=MapCompose(sanitize_text),
        output_processor=TakeFirst()
    )
    description = scrapy.Field(
        input_processor=MapCompose(sanitize_text),
        output_processor=TakeFirst()
    )
    text = scrapy.Field(
        input_processor=MapCompose(sanitize_text),
        output_processor=Join(" ")
    )
    html = scrapy.Field(output_processor=TakeFirst())  # Raw HTML content
    
    # Metadata
    content_type = scrapy.Field(output_processor=TakeFirst())
    language = scrapy.Field(output_processor=TakeFirst())
    keywords = scrapy.Field(
        input_processor=MapCompose(extract_keywords),
        output_processor=Identity()
    )
    
    # Links for further crawling
    links = scrapy.Field(output_processor=Identity())  