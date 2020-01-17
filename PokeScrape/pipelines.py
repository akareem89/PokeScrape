# -*- coding: utf-8 -*-

# Define your item pipelines here
#
# Don't forget to add your pipeline to the ITEM_PIPELINES setting
# See: https://doc.scrapy.org/en/latest/topics/item-pipeline.html

#
# class PokescrapePipeline(object):
#     def process_item(self, item, spider):
#         return item


import scrapy
from scrapy.pipelines.files import FilesPipeline

from scrapy.exporters import JsonItemExporter
from scrapy import signals
from pydispatch import dispatcher


def item_type(item):
    return type(item).__name__.replace('Item', '').lower()  # TeamItem => team


class MultiJSONItemPipeline(object):
    count = 1
    SaveTypes = ['gen8', 'gen7', 'gen6', 'gen5', 'gen4', 'gen3', 'gen2', 'gen1', 'move']
    top_dir = '_json/'

    def __init__(self):
        dispatcher.connect(self.spider_opened, signal=signals.spider_opened)
        dispatcher.connect(self.spider_closed, signal=signals.spider_closed)

    def spider_opened(self, spider):
        self.files = dict([(name, open(self.top_dir + name + '.json', 'w+b')) for name in self.SaveTypes])
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

class MultiImagesItemPipeline(FilesPipeline):
    SaveTypes = ['gen7', 'gen6', 'gen5', 'gen4', 'gen3', 'gen2', 'gen1']
    gen_dct = {
        'sm': 'gen7',
        'xy': 'gen6',
        'bw': 'gen5',
        'dp': 'gen4',
        'rs': 'gen3',
        'gs': 'gen2',
        'rby': 'gen1',
    }

    def get_media_requests(self, item, info):
        what = item_type(item)
        # if what == 'move':
        #     what = self.gen_dct[item['generation']] + 'move'
        for image_url in item.get('image_urls', []):
            yield scrapy.Request(image_url, meta={'filepatch': self.get_image_path(f"{what}_images", image_url)})

    def file_path(self, request, response=None, info=None):
        return '%s' % request.meta.get('filepatch')

    def get_image_path(self, top_dir, image_url):
        index_from_last = -1 if top_dir == 'move_images' else -2
        x = [a for a in image_url.split('/') if a]
        file_name = '/'.join(x[index_from_last:])
        full_path = f"{top_dir}/{file_name}"

        return full_path
