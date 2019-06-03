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
    bad_form_name = []

    def start_requests(self):

        # Scrape starting single #
        # self.get_next = False
        self.get_moves = False
        num = '386'  # Deoxys
        num = '492'  # Shaymin
        num = '745'  # Lycanroc
        num = '026'  # Raichu
        # num = '479'  # Rotom
        # num = '025'
        # num = '521'

        num = '001'  # Start
        yield scrapy.Request(f'https://www.serebii.net/pokedex-sm/{num}.shtml', callback=self.parse_sm_xy, meta={'gen': 'sm'})
        yield scrapy.Request(f'https://www.serebii.net/pokedex-xy/{num}.shtml', callback=self.parse_sm_xy, meta={'gen': 'xy'})

        # Scrape starting from #001
        # yield scrapy.Request('https://www.serebii.net/pokedex-sm/001.shtml', callback=self.parse_sm_xy, meta={'gen': 'sm'})
        # yield scrapy.Request('https://www.serebii.net/pokedex-xy/001.shtml', callback=self.parse_sm_xy, meta={'gen': 'xy'})

        self.crawler.signals.connect(self.spider_idle, signal=signals.spider_idle)  # Call self.spider_idle once all yields have returned

    def get_form_name(self, base_name, form_alt):
        form_name = form_alt.replace(base_name, '') if form_alt.count(base_name) >= 1 else form_alt
        form_name = form_name.replace('Forme', '').strip()
        form_name = form_name.replace('Form', '').strip()
        form_name = form_name.replace('Regular', '').strip()
        if form_name:
            form_name = f'{base_name}({form_name.strip()})'
        else:
            form_name = base_name

        return form_name

    def get_form_speed(self, speed_dct, form_name, index):
        if speed_dct[form_name]:
            return speed_dct[form_name]
        elif index == 0:
            return speed_dct['base']
        elif speed_dct['alternate']:
            return speed_dct['alternate']
        else:
            return speed_dct['base']

    def get_form_pic(self, response, expected_length, index):
        pic_len = response.xpath(f'(//table/tr/td[text()="Alternate Forms"]/ancestor::table[@class="dextable"])[last()]//td[@class="pkmn"]/img/@src')
        if expected_length - len(pic_len) == 1:  # Site does not have normal form with alternate forms
            if index == 0:
                pic = response.xpath('//table[@class="dextable"]/tr[2]/td/table/tr/td[1]/img/@src').get()
            else:
                pic = response.xpath(f'(//table/tr/td[text()="Alternate Forms"]/ancestor::table[@class="dextable"]//td[@class="pkmn"]/img)[{index}]/@src').get()
        else:
            pic = response.xpath(f'(//table/tr/td[text()="Alternate Forms"]/ancestor::table[@class="dextable"]//td[@class="pkmn"]/img)[{index + 1}]/@src').get()
        if not pic:
            pic = response.xpath(f'(//table/tr/td[text()="Gender Differences"]/ancestor::table[@class="dextable"]//td[@class="pkmn"]/img)[{index + 1}]/@src').get()

        return pic

    def create_form_name_dct(self, name, forms_reposnse):
        alt_name_dct = {}
        all_alternate_forms = []
        for alt_name in forms_reposnse.xpath('@alt').getall():
            if self.get_form_name(name, alt_name) in alt_name_dct.values():
                print(f"DUPLICATE!!!!!!!!!!!!!!!! - name: {self.get_form_name(name, alt_name)} form: {alt_name})")
            alt_form_name = self.get_form_name(name, alt_name)
            alt_name_dct[alt_name] = alt_form_name
            all_alternate_forms.append(alt_form_name)

        return alt_name_dct, all_alternate_forms

    def create_form_ability_dct(self, alt_name_dct, response):
        form_ability_dct = {'base': []}
        for form in alt_name_dct.values():
            form_ability_dct[form] = []
        current = 'base'

        for b in response.xpath('(//a[@name="general"]/ancestor::div//td[@align="left" and @class="fooinfo"])[1]//b'):
            for alt in alt_name_dct:
                if alt in b.xpath("text()").get().strip():
                    current = alt_name_dct[alt]

            if b.xpath('../@href').get():  # if <b> is an ability, it is child of a <a href> tag
                ability = b.xpath("text()").get().strip()
                form_ability_dct[current].append(ability)

        return form_ability_dct

    def create_form_speed_dct(self, alt_name_dct, response):
        form_speed_dct = {'base': '',
                          'alternate': ''}
        for form in alt_name_dct.values():
            form_speed_dct[form] = []

        for b in response.xpath('//table[@class="dextable"]/tr/td[starts-with(text(), "Base Stats")]/../preceding-sibling::tr//b[starts-with(text(), "Stats")]'):
            stat_header = b.xpath("text()").get().strip()
            if stat_header == 'Stats':
                key = 'base'
            else:
                key = 'alternate'

            for alt in alt_name_dct:
                if alt in stat_header:
                    key = alt_name_dct[alt]

            speed = b.xpath('../../following-sibling::tr/td[starts-with(text(), "Base Stats")]/following-sibling::td[last()]//text()').get().strip()
            form_speed_dct[key] = speed

        return form_speed_dct

    def get_moveset(self, response, icon):
        if not self.get_moves:
            return {}

        move_dct = {}  # <k,v> : <move url, level>
        for item in response.xpath('//tr/th[@class="attheader" and starts-with(text(), "Attack")]'):
            for move in item.xpath('../../tr'):
                move_url = move.xpath('td/a[starts-with(@href, "/attackdex")]/@href')
                if not move_url or move_url.get() in move_dct:  # if row has move url and has not been visited for current pokemon
                    continue  # Iterate loop without moving forward

                move_url = move_url.get()  # get actual url from html tag

                if item.xpath('../th[text()="Form"]'):
                    allowed_forms = move.xpath('td[last()]//img/@src').getall()
                    if icon not in allowed_forms:
                        continue

                level = ''
                if item.xpath('../th[text()="Level"]'):
                    level_value = move.xpath('td[1]//text()').get()
                    if str.isdigit(level_value):
                        level = level_value

                move_dct[move_url] = level

        return move_dct

    def parse_sm_xy(self, response):

        header = response.xpath('//table[@class="dextab"]/tr/td[@width="65%"]/table/tr')
        icon = header.xpath('td[1]/img/@src').get().strip()
        number = header.xpath('td[2]//text()').get().strip().split(' ')[0]
        name = header.xpath('td[2]//text()').get().strip().split(' ')[1]

        forms = response.xpath('//table[@class="dextable"]/tr[2]/td/div/a/img')
        if forms:
            alt_name_dct, alternate_forms_lst = self.create_form_name_dct(name, forms)
            form_ability_dct = self.create_form_ability_dct(alt_name_dct, response)
            form_speed_dct = self.create_form_speed_dct(alt_name_dct, response)

            for i in range(len(forms)):
                form_icon = forms[i].xpath('@src').get()
                form_alt_name = forms[i].xpath('@alt').get()
                form_name = alt_name_dct[form_alt_name]
                form_pic = self.get_form_pic(response, len(forms), i)
                form_abilities = form_ability_dct[form_name] if form_ability_dct[form_name] else form_ability_dct['base']
                form_base_speed = self.get_form_speed(form_speed_dct, form_name, i)
                alternate_forms = [form_item for form_item in alternate_forms_lst if form_item != form_name]
                form_move_dct = self.get_moveset(response, form_icon)

                # print(f'name: {form_name} number: {number} alt: {form_alt_name} icon: {form_icon} pic: {form_pic} abilities: {form_abilities} base_speed: {form_base_speed} alternate_forms: {alternate_forms}')
                yield self.create_pokemon(url=response.request.url,
                                          base_name=name,
                                          name=form_name,
                                          number=number,
                                          generation=response.meta['gen'],
                                          icon=response.urljoin(form_icon),
                                          pic=response.urljoin(form_pic),
                                          abilities=form_abilities,
                                          base_speed=form_base_speed,
                                          alternate_forms=alternate_forms
                                          )

                for move_url, level in form_move_dct.items():
                    yield response.follow(move_url, callback=self.parse_move, meta={'lvl': level, 'gen': response.meta['gen'], 'name': form_name}, dont_filter=True)
        else:
            pic = response.xpath('//table[@class="dextable"]/tr[2]/td/table/tr/td[1]/img/@src').get()
            abilities = response.xpath('(//a[@name="general"]/ancestor::div//td[@align="left" and @class="fooinfo"])[1]/a/b//text()').getall()
            base_speed = response.xpath('//table[@class="dextable"]/tr/td[starts-with(text(), "Base Stats")]/following-sibling::td[last()]//text()').get()
            move_dct = self.get_moveset(response, icon)

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

            for move_url, level in move_dct.items():
                yield response.follow(move_url, callback=self.parse_move, meta={'lvl': level, 'gen': response.meta['gen'], 'name': name})

        next_page = response.xpath('//table/tr/td[@align="right"]/table[@border="0"]/tr/td/a/@href')
        if next_page and self.get_next:
            yield response.follow(next_page.get(), callback=self.parse_sm_xy, meta={'gen': response.meta['gen']})

    def create_pokemon(self, **kwargs):
        pokemon = PokemonItem()
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
        pokemon['mega_list'] = kwargs.get('mega_list', [])
        pokemon['moves'] = []
        pokemon['priority_moves'] = []

        self.dct[pokemon['generation']][pokemon['name']] = pokemon  # Save pokemon by name to corresponding generation dictionary

        if not pokemon['abilities']:
            self.no_abilities.append(f'POKEMON: {pokemon["name"]} | URL: {pokemon["url"]} | GEN: {pokemon["generation"]}{pokemon["number"]}')

        if 'html' in pokemon['pic'] or not pokemon['pic']:
            self.bad_pic.append(f'POKEMON: {pokemon["name"]} | URL: {pokemon["url"]} | GEN: {pokemon["generation"]}{pokemon["number"]} | PIC: {pokemon["pic"]}')

        if '.html' in pokemon['icon'] or not pokemon['icon']:
            self.bad_icon.append(f'POKEMON: {pokemon["name"]} | URL: {pokemon["url"]} | GEN: {pokemon["generation"]}{pokemon["number"]} | ICON: {pokemon["icon"]}')

        # print(f'{kwargs.get("is_mega", "")} POKEMON: {pokemon["name"]} |  URL: {pokemon["url"]} | PIC: {pokemon["pic"]} | ICON: {pokemon["icon"]} | ABILITIES: {pokemon["abilities"]} | SPEED: {pokemon["base_speed"]} | GEN: {pokemon["generation"]}{pokemon["number"]}')
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

        current_move_url = response.request.url
        if current_move_url not in self.move_dct['all']:
            move = MoveItem()
            move['url'] = current_move_url
            gen = response.xpath('//table[@class="dextab"]/tr/td[@class="curr"]/a//text()')
            if gen:
                gen = gen_dct[gen.get()]
            else:
                gen = gen_dct[move['url'].split("/")[3]]

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
                    yield response.follow(url.get(), callback=self.parse_move, dont_filter=True)

        if 'name' in response.meta:
            move = self.move_dct['all'][current_move_url]

            p_lvl = response.meta['lvl']
            p_gen = response.meta['gen']
            p_name = response.meta['name']

            pokemon = self.dct[p_gen][p_name]
            pokemon['moves'].append({'name': move['name'], 'level': p_lvl, 'priority': move['priority']})

            if move['priority'] != '0':
                pokemon['priority_moves'].append({'name': move['name'], 'level': p_lvl, 'priority': move['priority']})

        # print(f'MOVE: {move["name"]}  |  URL: {move["url"]}  |  GEN: {move["generation"]}')
        # yield move

    def spider_idle(self, spider):
        for i in self.no_abilities:
            print(f'NO ABILITIES: {i}')

        for i in self.bad_form_name:
            print(f'BAD NAME: {i}')

        for i in self.bad_pic:
            print(f'PIC: {i}')

        # print(f'SM: {self.dct["sm"]}')
        # print(f'XY: {self.dct["xy"]}')

        print("DONE")
