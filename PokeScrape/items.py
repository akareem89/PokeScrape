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
    mega_dct = Field()
    giga_form = Field()
    mega_list = Field()
    alternate_forms = Field()
    url = Field()
    images = Field()
    image_urls = Field()

    @staticmethod
    def create(**kwargs):
        gen_dct = {
            'swsh': 'Gen8Item',
            'sm': 'Gen7Item',
            'xy': 'Gen6Item',
            'bw': 'Gen5Item',
            'dp': 'Gen4Item',
            'rs': 'Gen3Item',
            'gs': 'Gen2Item',
            'rby': 'Gen1Item',
        }

        # cls = gen_dct[kwargs.get('generation')]

        # pokemon = PokemonItem()
        pokemon = eval(gen_dct[kwargs.get('generation')])()
        # print(f"pokemon: {type(pokemon)}")
        pokemon['url'] = kwargs.get('url')
        pokemon['generation'] = kwargs.get('generation')
        pokemon['number'] = kwargs.get('number')
        pokemon['base_name'] = kwargs.get('base_name', kwargs.get('name'))
        pokemon['name'] = kwargs.get('name')
        pokemon['icon'] = kwargs.get('icon')
        pokemon['pic'] = kwargs.get('pic')
        pokemon['abilities'] = kwargs.get('abilities', [])
        pokemon['base_speed'] = kwargs.get('base_speed')
        pokemon['alternate_forms'] = kwargs.get('alternate_forms', [])
        pokemon['mega_dct'] = kwargs.get('mega_dct', {})
        pokemon['giga_form'] = kwargs.get('giga_form', None)
        pokemon['mega_list'] = []
        pokemon['moves'] = []
        pokemon['priority_moves'] = []
        pokemon["image_urls"] = [pokemon['icon'], pokemon['pic']]



        return pokemon


class Gen8Item(PokemonItem):
    def __init__(self):
        super().__init__()


class Gen7Item(PokemonItem):
    def __init__(self):
        super().__init__()


class Gen6Item(PokemonItem):
    def __init__(self):
        super().__init__()


class Gen5Item(PokemonItem):
    def __init__(self):
        super().__init__()


class Gen4Item(PokemonItem):
    def __init__(self):
        super().__init__()


class Gen3Item(PokemonItem):
    def __init__(self):
        super().__init__()


class Gen2Item(PokemonItem):
    def __init__(self):
        super().__init__()


class Gen1Item(PokemonItem):
    def __init__(self):
        super().__init__()


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
    level = Field()
    images = Field()
    image_urls = Field()