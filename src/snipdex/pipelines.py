# Define your item pipelines here
#
# Don't forget to add your pipeline to the ITEM_PIPELINES setting
# See: https://docs.scrapy.org/en/latest/topics/item-pipeline.html


# useful for handling different item types with a single interface
from itemadapter import ItemAdapter
from master_node.master_node import process_crawl_result_task  # Import the Celery task


class SnipdexPipeline:
    def process_item(self, item, spider):
        return item


class CeleryPipeline:
    def process_item(self, item, spider):
        # Assume item contains: 'url', 'data' (content), 'links' (new URLs)
        crawl_result = {
            "url": item.get("url"),
            "data": dict(item),  # or just the fields you want indexed
            "new_urls": item.get("links", [])
        }
        # Dispatch to Celery (asynchronously)
        process_crawl_result_task.delay(crawl_result)
        return item
