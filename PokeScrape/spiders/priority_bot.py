# -*- coding: utf-8 -*-
import scrapy
import sys

from PokeScrape.items import PriorityItem


class PriorityBotSpider(scrapy.Spider):
    name = 'priority_bot'
    # allowed_domains = ['https://www.serebii.net/']
    allowed_domains = ["serebii.net"]
    start_urls = ['https://www.serebii.net/games/speedpriority.shtml']
    handle_httpstatus_list = [301]

    def parse(self, response):
        # print(response.text)
        priority_dct = {}

        current_stage = sys.maxsize
        for row in response.xpath('//table[@class="tab"]/tr'):
            # print("HERE")

            stage = row.xpath('td[@colspan="7"]//text()').re(r'Stage.*')
            if stage:
                # print("Stage: " + stage[0])
                current_stage = stage[0]

            move_name = row.xpath('td[@class="fooinfo"]/a//text()').extract_first()
            if move_name:
                # print("Move: " + move_name)

                i = row.xpath('td[1]/i//text()').extract_first()
                if i:
                    print("HAS i: " + i)

                move_type = row.xpath('td[2]/img/@src').extract_first().strip()
                # print("Type: " + move_type)

                cat = row.xpath('td[3]/img/@src').extract_first().strip()
                # print("Category: " + cat)

                pp = row.xpath('td[4]//text()').extract_first().strip()
                # print("PP: " + pp)

                att = row.xpath('td[5]//text()').extract_first().strip()
                # print("Attack: " + att)

                acc = row.xpath('td[6]//text()').extract_first().strip()
                # print("Accuracy: " + acc)

                move = PriorityItem()
                move['move_name'] = move_name
                move['priority'] = current_stage
                move['type'] = move_type
                move['category'] = cat
                move['pp'] = pp
                move['attack'] = att
                move['accuracy'] = acc
                priority_dct[move_name] = move
                print(move)

                yield move

        # print(priority_dct)