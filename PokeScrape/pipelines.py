# -*- coding: utf-8 -*-

# Define your item pipelines here
#
# Don't forget to add your pipeline to the ITEM_PIPELINES setting
# See: https://doc.scrapy.org/en/latest/topics/item-pipeline.html

#
# class PokescrapePipeline(object):
#     def process_item(self, item, spider):
#         return item


from scrapy.exporters import JsonItemExporter
from scrapy import signals
from scrapy.xlib.pydispatch import dispatcher


def item_type(item):
    return type(item).__name__.replace('Item', '').lower()  # TeamItem => team


class MultiJSONItemPipeline(object):
    count = 1
    SaveTypes = ['gen7', 'gen6', 'gen5', 'gen4', 'gen3', 'gen2', 'gen1', 'move']

    def __init__(self):
        dispatcher.connect(self.spider_opened, signal=signals.spider_opened)
        dispatcher.connect(self.spider_closed, signal=signals.spider_closed)

    def spider_opened(self, spider):
        self.files = dict([(name, open(name + '.json', 'w+b')) for name in self.SaveTypes])
        self.exporters = dict([(name, JsonItemExporter(self.files[name])) for name in self.SaveTypes])
        [e.start_exporting() for e in self.exporters.values()]

    def spider_closed(self, spider):
        [e.finish_exporting() for e in self.exporters.values()]
        [f.close() for f in self.files.values()]

    def process_item(self, item, spider):
        what = item_type(item)
        if what in set(self.SaveTypes):
            self.exporters[what].export_item(item)
        # self.count += 1
        # print(f"count: {self.count}")
        return item
