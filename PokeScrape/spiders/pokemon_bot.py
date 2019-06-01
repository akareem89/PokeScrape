# -*- coding: utf-8 -*-
import scrapy
from scrapy import signals
import hashlib
import re

from PokeScrape.items import PokemonItem, MoveItem


class PokemonBotSpider(scrapy.Spider):
    name = 'pokemon_bot'
    allowed_domains = ["serebii.net"]
    handle_httpstatus_list = [301]

    # Dictionary for all pokemon in each generation
    dct = {
        'sm': {},
        'xy': {}
    }

    # Dictionary for all moves in each generation
    move_dct = {
        'sm': {},
        'xy': {},
        'bw': {},
        'dp': {},
        'rs': {},
        'gs': {},
        'I': {},
        'all': {},  # All moves from all generation; key on move url
    }

    get_next = True  # Scrape all pokemon in generation
    get_moves = True  # Scrape move info for pokemon

    bad_pic = []
    bad_icon = []
    no_abilities = []

    def start_requests(self):

        # # Scrape starting single #
        # self.get_next = False
        # # self.get_moves = False
        # # num = '386'  # Deoxys
        # num = '492'  # Shaymin
        # yield scrapy.Request(f'https://www.serebii.net/pokedex-sm/{num}.shtml', callback=self.parse_sm_xy, meta={'gen': 'sm'})
        # # yield scrapy.Request(f'https://www.serebii.net/pokedex-xy/{num}.shtml', callback=self.parse_sm_xy, meta={'gen': 'xy'})

        # Scrape starting from #001
        yield scrapy.Request('https://www.serebii.net/pokedex-sm/001.shtml', callback=self.parse_sm_xy, meta={'gen': 'sm'})
        yield scrapy.Request('https://www.serebii.net/pokedex-xy/001.shtml', callback=self.parse_sm_xy, meta={'gen': 'xy'})

        self.crawler.signals.connect(self.spider_idle, signal=signals.spider_idle)  # Call self.spider_idle once all yields have returned

    def parse_sm_xy(self, response):

        header = response.xpath('//table[@class="dextab"]/tr/td[@width="65%"]/table/tr')
        icon = header.xpath('td[1]/img/@src').get().strip()
        number = header.xpath('td[2]//text()').get().strip().split(' ')[0]
        name = header.xpath('td[2]//text()').get().strip().split(' ')[1]
        pic = response.xpath('//table[@class="dextable"]/tr[2]/td/table/tr/td[1]/img/@src').get()
        abilities = response.xpath('//a[@name="general"]/../../table[4]/tr[2]/td/a/b//text()').getall()
        base_speed = response.xpath(
            '//table[@class="dextable"]/tr/td[starts-with(text(), "Base Stats")]/following-sibling::td[last()]//text()').get()

        seen_moves = []
        for item in response.xpath('//tr/th[@class="attheader" and starts-with(text(), "Attack")]'):
            for move in item.xpath('../../tr'):
                if move.xpath('td/a[starts-with(@href, "/attackdex")]//text()'):  # if row has move url
                    level = ''
                    if item.xpath('../th[text()="Level"]'):
                        level_value = move.xpath('td[1]//text()').get()
                        if str.isdigit(level_value):
                            level = level_value

                    move_url = move.xpath('td/a[starts-with(@href, "/attackdex-")]/@href').get()

                    if move_url not in seen_moves and self.get_moves:
                        seen_moves.append(move_url)
                        yield response.follow(move_url, callback=self.parse_move, meta={'lvl': level, 'gen': response.meta['gen'], 'name': name})

        mega_list = []
        for mega in response.xpath('//table[@class="dextable"]/tr/td/font/b[starts-with(text(), "Mega")]'):
            mega_name = mega.xpath('ancestor-or-self::table/tr[3]/td[2]//text()').get()

            if mega_name not in mega_list:
                mega_list.append(mega_name)  # Add Mega to base form list of Mega Evolutions
                mega_pic = mega.xpath('ancestor-or-self::table/tr[3]/td[1]//td[1]/img/@src').get()
                mega_abilities = mega.xpath(
                    'ancestor-or-self::table/following-sibling::*[1]/tr[2]/td/a/b//text()').getall()
                mega_base_speed = mega.xpath(
                    'ancestor-or-self::table/following-sibling::*/tr/td[starts-with(text(), "Base Stats")]/following-sibling::td[last()]//text()').get()

                yield self.create_pokemon(url=response.request.url,
                                          name=mega_name,
                                          number=number,
                                          generation=response.meta['gen'],
                                          icon=response.urljoin(icon),
                                          pic=response.urljoin(mega_pic),
                                          abilities=mega_abilities,
                                          base_speed=mega_base_speed,
                                          is_mega='MEGA'
                                          )

        yield self.create_pokemon(url=response.request.url,
                                  name=name,
                                  number=number,
                                  generation=response.meta['gen'],
                                  icon=response.urljoin(icon),
                                  pic=response.urljoin(pic),
                                  abilities=abilities,
                                  base_speed=base_speed,
                                  mega_list=mega_list
                                  )

        next_page = response.xpath('//table/tr/td[@align="right"]/table[@border="0"]/tr/td/a/@href')
        if next_page and self.get_next:
            yield response.follow(next_page.get(), callback=self.parse_sm_xy, meta={'gen': response.meta['gen']})

    def create_pokemon(self, **kwargs):
        pokemon = PokemonItem()
        pokemon['url'] = kwargs.get('url')
        pokemon['generation'] = kwargs.get('generation')
        pokemon['number'] = kwargs.get('number')
        pokemon['name'] = kwargs.get('name')
        pokemon['icon'] = kwargs.get('icon')
        pokemon['pic'] = kwargs.get('pic')
        pokemon['abilities'] = kwargs.get('abilities', [])
        pokemon['base_speed'] = kwargs.get('base_speed')
        pokemon['mega_list'] = kwargs.get('mega_list', [])
        pokemon['moves'] = []
        pokemon['priority_moves'] = []

        self.dct[pokemon['generation']][pokemon['name']] = pokemon  # Save pokemon by name to corresponding generation dictionary

        if not pokemon['abilities']:
            self.no_abilities.append(f'POKEMON: {pokemon["name"]} | URL: {pokemon["url"]} | GEN: {pokemon["generation"]}{pokemon["number"]}')

        if '.png' not in pokemon['pic']:
            self.bad_pic.append(f'POKEMON: {pokemon["name"]} | URL: {pokemon["url"]} | GEN: {pokemon["generation"]}{pokemon["number"]} | PIC: {pokemon["pic"]}')

        if '.png' not in pokemon['icon']:
            self.bad_icon.append(f'POKEMON: {pokemon["name"]} | URL: {pokemon["url"]} | GEN: {pokemon["generation"]}{pokemon["number"]} | ICON: {pokemon["icon"]}')

        print(f'{kwargs.get("is_mega", "")} POKEMON: {pokemon["name"]} |  URL: {pokemon["url"]} | PIC: {pokemon["pic"]} | ICON: {pokemon["icon"]} | ABILITIES: {pokemon["abilities"]} | SPEED: {pokemon["base_speed"]} | GEN: {pokemon["generation"]}{pokemon["number"]}')
        # print(pokemon)
        return pokemon

    def parse_move(self, response):
        gen_dct = {
            'Gen VII Dex': 'sm',
            'Gen VI Dex': 'xy',
            'Gen V Dex': 'bw',
            'Gen IV Dex': 'dp',
            'Gen III Dex': 'rs',
            'Gen II Dex': 'gs',
            'Gen I Dex': 'I',
            'attackdex-sm': 'sm',
            'attackdex-xy': 'xy',
            'attackdex-bw': 'bw',
            'attackdex-dp': 'dp',
            'attackdex': 'rs',
            'attackdex-gs': 'gs',
            'attackdex-rby': 'I'
        }

        gen_3_priority = {
            'Helping Hand': '+5',
            'Magic Coat': '+4',
            'Snatch': '+4',
            'Detect': '+3',
            'Endure': '+3',
            'Follow Me': '+3',
            'Protect': '+3',
            'ExtremeSpeed': '+1',
            'Fake Out': '+1',
            'Mach Punch': '+1',
            'Quick Attack': '+1',
            'Vital Throw': '-1',
            'Focus Punch': '-3',
            'Revenge': '-4',
            'Counter': '-5',
            'Mirror Coat': '-5',
            'Roar': '-6',
            'Whirlwind': '-6'
        }

        move = MoveItem()
        move['url'] = response.request.url
        gen = response.xpath('//table[@class="dextab"]/tr/td[@class="curr"]/a//text()')
        if gen:
            gen = gen_dct[gen.get()]
        else:
            gen = gen_dct[move['url'].split("/")[3]]
            # print(f'ELSE gen: {gen}')

        if move['url'] not in self.move_dct['all']:
            move['generation'] = gen

            if gen == gen_dct['Gen III Dex']:
                move['name'] = response.xpath('//table[@class="dextab"]/tr[2]/td[1]//text()').get().strip()
                move['type'] = response.urljoin(
                    response.xpath('//table[@class="dextab"]/tr[2]/td[2]/div/img/@src').get())
                move['category'] = ''
                move['pp'] = response.xpath('//table[@class="dextab"]/tr[4]/td[1]//text()').get().strip()
                move['attack'] = response.xpath('//table[@class="dextab"]/tr[4]/td[2]//text()').get().strip()
                move['accuracy'] = response.xpath('//table[@class="dextab"]/tr[4]/td[3]//text()').get().strip()
                if move['name'] in gen_3_priority:
                    move['priority'] = gen_3_priority[move['name']]
                else:
                    move['priority'] = '0'
            else:
                move['name'] = response.xpath('//table[@class="dextable"]/tr[2]/td[1]//text()').get().strip()
                move['type'] = response.urljoin(
                    response.xpath('//table[@class="dextable"]/tr[2]/td[2]/a/img/@src').get())
                if response.xpath('//table[@class="dextable"]/tr[1]/td[3]/b[text()="Category"]'):
                    move['category'] = response.urljoin(
                        response.xpath('//table[@class="dextable"]/tr[2]/td[3]/a/img/@src').get())
                else:
                    move['category'] = ''
                move['pp'] = response.xpath('//table[@class="dextable"]/tr[4]/td[1]//text()').get().strip()
                move['attack'] = response.xpath('//table[@class="dextable"]/tr[4]/td[2]//text()').get().strip()
                move['accuracy'] = response.xpath('//table[@class="dextable"]/tr[4]/td[3]//text()').get().strip()
                priority_header = response.xpath('//table[@class="dextable"]/tr/td/b[text()="Speed Priority"]')
                move['priority'] = priority_header.xpath('../../following-sibling::tr[1]/td[2]//text()').get().strip()

            self.move_dct[move['generation']][move['name']] = move
            self.move_dct['all'][move['url']] = move

            remaining = response.xpath('//table[@class="dextab"]/tr/td[@class="pkmn"]/a/@href')
            # print(f'remaining: {remaining}')
            if remaining:
                for url in remaining:
                    yield response.follow(url.get(), callback=self.parse_move)

        if 'name' in response.meta:
            move = self.move_dct['all'][move['url']]

            p_lvl = response.meta['lvl']
            p_gen = response.meta['gen']
            p_name = response.meta['name']

            pokemon = self.dct[p_gen][p_name]
            pokemon['moves'].append({'name': move['name'], 'level': p_lvl, 'priority': move['priority']})

            if move['priority'] != '0':
                pokemon['priority_moves'].append({'name': move['name'], 'level': p_lvl, 'priority': move['priority']})
                # print(f'priority_move: {move}')

        # print(f'MOVE: {move["name"]}  |  URL: {move["url"]}  |  GEN: {move["generation"]}')
        yield move

    def spider_idle(self, spider):

        # print(f'SM: {self.dct["sm"]}')
        # print(f'XY: {self.dct["xy"]}')

        print("DONE")
