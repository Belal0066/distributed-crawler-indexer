import scrapy
from itemloaders.processors import TakeFirst, MapCompose, Join
import re

def clean_whitespace_in(text):
    if text:
        return re.sub(r"\s+", " ", text).strip()
    return text

class SnipdexItem(scrapy.Item):
    url = scrapy.Field(output_processor=TakeFirst())

    title = scrapy.Field(
        input_processor=MapCompose(str.strip, clean_whitespace_in),
        output_processor=TakeFirst(),
    )

    description = scrapy.Field(
        input_processor=MapCompose(str.strip, clean_whitespace_in),
        output_processor=TakeFirst(),
    )

    keywords = scrapy.Field(
        input_processor=MapCompose(str.strip, clean_whitespace_in),
    )

    text = scrapy.Field(
        input_processor=MapCompose(str.strip, clean_whitespace_in),
        output_processor=Join(separator=" ")
    )

    links = scrapy.Field(
        input_processor=MapCompose(str.strip),
    )

    timestamp = scrapy.Field(output_processor=TakeFirst())

    content_type = scrapy.Field(output_processor=TakeFirst())

    language = scrapy.Field(
        input_processor=MapCompose(str.strip),
        output_processor=TakeFirst()
    )

    status_code = scrapy.Field(
        output_processor=TakeFirst()
    )  
