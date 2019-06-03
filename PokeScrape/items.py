# -*- coding: utf-8 -*-

# Define here the models for your scraped items
#
# See documentation in:
# https://doc.scrapy.org/en/latest/topics/items.html

import scrapy
from scrapy import Field, Item


class PokemonItem(Item):
    generation = Field()
    number = Field()
    base_name = Field()
    name = Field()
    icon = Field()
    moves = Field()
    priority_moves = Field()
    abilities = Field()
    base_speed = Field()
    pic = Field()
    mega_list = Field()
    alternate_forms = Field()
    url = Field()


class PriorityItem(Item):
    move_name = Field()
    priority = Field()
    type = Field()
    category = Field()
    pp = Field()
    attack = Field()
    accuracy = Field()


class MoveItem(Item):
    url = Field()
    generation = Field()
    name = Field()
    priority = Field()
    type = Field()
    category = Field()
    pp = Field()
    attack = Field()
    accuracy = Field()
