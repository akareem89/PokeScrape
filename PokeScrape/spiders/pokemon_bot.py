# -*- coding: utf-8 -*-
import random

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
        'xy': {},
        'bw': {},
        'dp': {},
        'rs': {},
        'gs': {},
        'rby': {},
    }

    # Dictionary for all moves in each generation
    move_dct = {
        'sm': {},
        'xy': {},
        'bw': {},
        'dp': {},
        'rs': {},
        'gs': {},
        'rby': {},
        'all': {},  # All moves from all generation; key on move url
    }

    get_moves = True  # Scrape move info for pokemon

    bad_pic = []
    bad_icon = []
    no_abilities = []
    no_moves = []
    bad_form_name = []

    stop_at = -1
    rs_stop = 386

    def start_requests(self):
        # Scrape starting single #
        # self.get_moves = False
        # self.stop_at = 0
        # num = '800'
        # num = '386'  # Deoxys
        # num = '492'  # Shaymin
        # num = '646'  # Kyurem
        # num = '550'  # Basculin
        # num = '745'  # Lycanroc
        # num = '026'  # Raichu
        # num = '479'  # Rotom

        # r = random.randint(1, 150)
        # num = ('0' * (3 - len(str(r)))) + str(r)
        num = '001'  # Start
        print(f"num: {num}")
        yield scrapy.Request(f'https://www.serebii.net/pokedex-sm/{num}.shtml', callback=self.parse_sm_xy, meta={'count': 0, 'gen': 'sm'})
        # yield scrapy.Request(f'https://www.serebii.net/pokedex-xy/{num}.shtml', callback=self.parse_sm_xy, meta={'count': 0, 'gen': 'xy'})
        #
        # yield scrapy.Request(f'https://www.serebii.net/pokedex-bw/{num}.shtml', callback=self.parse_bw_dp, meta={'count': 0, 'gen': 'bw'})
        # yield scrapy.Request(f'https://www.serebii.net/pokedex-dp/{num}.shtml', callback=self.parse_bw_dp, meta={'count': 0, 'gen': 'dp'})
        #
        # rs_stop = self.stop_at if self.stop_at >= 0 else self.rs_stop
        # for url in ['https://www.serebii.net/pokedex-rs/' + ('0' * (3 - len(str(x)))) + str(x) + '.shtml' for x in range(int(num), int(num) + rs_stop)]:
        #     yield scrapy.Request(url, callback=self.parse_rs, meta={'count': self.stop_at, 'gen': 'rs'})
        #
        # yield scrapy.Request(f'https://www.serebii.net/pokedex-gs/{num}.shtml', callback=self.parse_gs_rby, meta={'count': 0, 'gen': 'gs'})
        # yield scrapy.Request(f'https://www.serebii.net/pokedex/{num}.shtml', callback=self.parse_gs_rby, meta={'count': 0, 'gen': 'rby'})

        # DO NOT ERASE - ADIL
        # yield scrapy.Request(f'https://www.serebii.net/pokedex-dp/001.shtml', callback=self.parse_bw_dp, meta={'count': 0, 'gen': 'dp'})                                                                                                                                                                                 })

        self.crawler.signals.connect(self.spider_closed, signal=signals.spider_closed)  # Call self.spider_closed once all yields have returned

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
        alternate_forms = []

        alt_name_list = forms_reposnse.xpath('@alt').getall()
        alt_name_list = alt_name_list if alt_name_list else forms_reposnse.xpath('@title').getall()

        for alt_name in alt_name_list:
            alt_form_name = self.get_form_name(name, alt_name)
            alt_name_dct[alt_name] = alt_form_name
            alternate_forms.append(alt_form_name)

        return alt_name_dct, alternate_forms

    def create_form_ability_dct(self, alt_name_dct, response, gen=None):
        form_ability_dct = {'base': []}
        for form in alt_name_dct.values():
            form_ability_dct[form] = []
        current = 'base'

        if gen == 'dp':
            ability_section = reversed(response.xpath('(//a[@name="general"]/ancestor::div//td[@align="left" and @class="fooleft"])[1]//*'))
        else:
            ability_section = response.xpath('(//a[@name="general"]/ancestor::div//td[@align="left" and @class="fooinfo"])[1]//b')

        for b in ability_section:
            b_text = b.xpath("text()")
            if b_text:
                for alt in alt_name_dct:
                    if alt in b_text.get().strip():
                        current = alt_name_dct[alt]

            if b.xpath('../@href').get():  # if <b> is an ability, it is child of a <a href> tag
                ability = b.xpath("text()").get().strip()
                form_ability_dct[current].append(ability)

        return form_ability_dct

    def create_form_speed_dct(self, alt_name_dct, response, gen=None):
        form_speed_dct = {'base': '',
                          'alternate': ''}
        for form in alt_name_dct.values():
            form_speed_dct[form] = []

        if gen == 'sm' and response.xpath('//li[@title="Sun/Moon/Ultra Sun/Ultra Moon"]'):
            stat_sections_path = '//li[@title="Sun/Moon/Ultra Sun/Ultra Moon"]//table[@class="dextable"]/tr/td[starts-with(text(), "Base Stats")]/../preceding-sibling::tr//b[starts-with(text(), "Stats")]'
        else:
            stat_sections_path = '//table[@class="dextable"]/tr/td[starts-with(text(), "Base Stats")]/../preceding-sibling::tr//b[starts-with(text(), "Stats")]'

        if response.xpath('//a[@name="megastats"]'):  # if has mega
            stat_sections_path = f'//a[@name="megastats"]/preceding::{stat_sections_path[2:]}'  # Ensure we do not include mega stats

        for b in response.xpath(stat_sections_path):
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

    def get_moveset(self, response, gen=None, **kwargs):
        if not self.get_moves:
            return {}

        move_dct = {}  # <k,v> : <move url, level>

        if gen == 'rs':
            move_section = response.xpath('//tr/th/font[@color="#ffffff" and starts-with(text(), "Attack")]')
            row_selector = 'ancestor-or-self::table/tbody/tr'
            level_selector = '../../th/font[text()="Level"]'
        elif gen == 'sm' and response.xpath('//li[@title="Sun/Moon/Ultra Sun/Ultra Moon"]'):
            move_section = response.xpath('//li[@title="Sun/Moon/Ultra Sun/Ultra Moon"]//tr/th[@class="attheader" and starts-with(text(), "Attack")]')
            row_selector = '../../tr'
            level_selector = '../th[text()="Level"]'
        else:
            move_section = response.xpath('//tr/th[@class="attheader" and starts-with(text(), "Attack")]')
            row_selector = '../../tr'
            level_selector = '../th[text()="Level"]'

        for item in move_section:
            for move in item.xpath(row_selector):
                move_url = move.xpath('td/a[starts-with(@href, "/attackdex")]/@href')
                move_name = move.xpath('td/a[starts-with(@href, "/attackdex")]//text()')
                if not move_url or not move_name or move_url.get() in move_dct:  # if row has move url and has not been visited for current pokemon
                    continue  # Iterate loop without moving forward

                move_url = move_url.get()  # get actual url from html tag

                if item.xpath('../th[text()="Form"]'):
                    allowed_forms = move.xpath('td[last()]//img/@src').getall()
                    if kwargs.get("icon") and kwargs.get("icon") not in allowed_forms:
                        continue

                    allowed_forms = move.xpath('td[last()]//img/@title').getall()
                    if kwargs.get("title") and kwargs.get("title") not in allowed_forms:
                        continue

                level = ''
                if item.xpath(level_selector):
                    level_value = move.xpath('td[1]//text()').get()
                    if str.isdigit(level_value):
                        level = level_value

                move_dct[move_url] = level

        return move_dct

    def parse_sm_xy(self, response):
        gen = response.meta['gen']
        icon = response.xpath('//table[@class="dextab"]/tr/td[@width="65%"]/table/tr/td[1]/img/@src').get().strip()
        number = response.xpath('//table[@class="dextab"]/tr/td[@width="65%"]/table/tr/td[2]//text()').get().strip().split(' ')[0]
        name = response.xpath('//table[@class="dextab"]/tr/td[@width="65%"]/table/tr/td[2]//text()').get().strip().split(' ')[1]

        forms = response.xpath('//table[@class="dextable"]/tr[2]/td/div/a/img')
        if forms:
            alt_name_dct, alternate_forms = self.create_form_name_dct(name, forms)
            form_ability_dct = self.create_form_ability_dct(alt_name_dct, response)
            form_speed_dct = self.create_form_speed_dct(alt_name_dct, response, gen)

            for i in range(len(forms)):
                form_icon = forms[i].xpath('@src').get()
                form_alt_name = forms[i].xpath('@alt').get()
                form_name = alt_name_dct[form_alt_name]
                form_pic = self.get_form_pic(response, len(forms), i)
                form_abilities = form_ability_dct[form_name] if form_ability_dct[form_name] else form_ability_dct['base']
                form_base_speed = self.get_form_speed(form_speed_dct, form_name, i)
                form_move_dct = self.get_moveset(response, gen=gen, icon=form_icon)

                mega_dct = {}
                for mega in response.xpath('//table[@class="dextable"]/tr/td/font/b[starts-with(text(), "Mega") or starts-with(text(), "Ultra")]'):
                    mega_name = mega.xpath('ancestor-or-self::table/tr[3]/td[2]//text()').get()

                    if mega_name not in mega_dct:
                        mega_pic = mega.xpath('ancestor-or-self::table/tr[3]/td[1]//td[1]/img/@src').get()
                        mega_abilities = mega.xpath('ancestor-or-self::table/following-sibling::*[1]/tr[2]/td/a/b//text()').getall()
                        mega_base_speed = mega.xpath('ancestor-or-self::table/following-sibling::*/tr/td[starts-with(text(), "Base Stats")]/following-sibling::td[last()]//text()').get()

                        mega_pokemon = PokemonItem.create(url=response.request.url,
                                                          base_name=name,
                                                          name=mega_name,
                                                          number=number,
                                                          generation=gen,
                                                          icon=response.urljoin(icon),
                                                          pic=response.urljoin(mega_pic),
                                                          abilities=mega_abilities,
                                                          base_speed=mega_base_speed,
                                                          is_mega='MEGA'
                                                          )
                        mega_dct[mega_name] = mega_pokemon  # Add Mega to base form dct of Mega Evolutions

                pokemon = PokemonItem.create(url=response.request.url,
                                             base_name=name,
                                             name=form_name,
                                             number=number,
                                             generation=gen,
                                             icon=response.urljoin(form_icon),
                                             pic=response.urljoin(form_pic),
                                             abilities=form_abilities,
                                             base_speed=form_base_speed,
                                             mega_dct=mega_dct,
                                             alternate_forms=alternate_forms
                                             )
                for move_url, level in form_move_dct.items():
                    yield response.follow(move_url, callback=self.parse_move, meta={'size': len(form_move_dct), 'lvl': level, 'pokemon': pokemon}, dont_filter=True)
        else:
            pic = response.xpath('//table[@class="dextable"]/tr[2]/td/table/tr/td[1]/img/@src').get()
            abilities = response.xpath('(//a[@name="general"]/ancestor::div//td[@align="left" and @class="fooinfo"])[1]/a/b//text()').getall()
            base_speed = response.xpath('//table[@class="dextable"]/tr/td[starts-with(text(), "Base Stats")]/following-sibling::td[last()]//text()').get()
            move_dct = self.get_moveset(response, gen=gen)

            mega_dct = {}
            for mega in response.xpath('//table[@class="dextable"]/tr/td/font/b[starts-with(text(), "Mega")]'):
                mega_name = mega.xpath('ancestor-or-self::table/tr[3]/td[2]//text()').get()

                if mega_name not in mega_dct:
                    mega_pic = mega.xpath('ancestor-or-self::table/tr[3]/td[1]//td[1]/img/@src').get()
                    mega_abilities = mega.xpath('ancestor-or-self::table/following-sibling::*[1]/tr[2]/td/a/b//text()').getall()
                    mega_base_speed = mega.xpath('ancestor-or-self::table/following-sibling::*/tr/td[starts-with(text(), "Base Stats")]/following-sibling::td[last()]//text()').get()

                    mega_pokemon = PokemonItem.create(url=response.request.url,
                                                      base_name=name,
                                                      name=mega_name,
                                                      number=number,
                                                      generation=gen,
                                                      icon=response.urljoin(icon),
                                                      pic=response.urljoin(mega_pic),
                                                      abilities=mega_abilities,
                                                      base_speed=mega_base_speed,
                                                      is_mega='MEGA'
                                                      )
                    mega_dct[mega_name] = mega_pokemon  # Add Mega to base form dct of Mega Evolutions

            pokemon = PokemonItem.create(url=response.request.url,
                                         name=name,
                                         number=number,
                                         generation=gen,
                                         icon=response.urljoin(icon),
                                         pic=response.urljoin(pic),
                                         abilities=abilities,
                                         base_speed=base_speed,
                                         mega_dct=mega_dct
                                         )
            for move_url, level in move_dct.items():
                yield response.follow(move_url, callback=self.parse_move, meta={'size': len(move_dct), 'lvl': level, 'pokemon': pokemon}, dont_filter=True)

        next_page = response.xpath('//table/tr/td[@align="right"]/table[@border="0"]/tr/td/a/@href')
        if next_page and (self.stop_at == -1 or self.stop_at > response.meta['count']):
            yield response.follow(next_page.get(), callback=self.parse_sm_xy, meta={'count': response.meta['count'] + 1, 'gen': gen})

    def parse_bw_dp(self, response):
        gen = response.meta['gen']
        icon = response.xpath('//table[@class="dextab"]/tr/td[@width="65%"]/table/tr/td[1]/img/@src').get().strip()
        number = response.xpath('//table[@class="dextab"]/tr/td[@width="65%"]/table/tr/td[2]//text()').get().strip().split(' ')[0]
        name = response.xpath('//table[@class="dextab"]/tr/td[@width="65%"]/table/tr/td[2]//text()').get().strip().split(' ')[1]

        forms = response.xpath(f'(//td[text()="Alternate Forms"]/ancestor::table[@class="dextable"])[last()]//td[@class="pkmn"]/img')
        if forms:
            alt_name_dct, alternate_forms = self.create_form_name_dct(name, forms)
            form_ability_dct = self.create_form_ability_dct(alt_name_dct, response, gen)
            form_speed_dct = self.create_form_speed_dct(alt_name_dct, response)

            for i in range(len(forms)):
                form_alt_name = forms[i].xpath('@title').get()
                form_icon = response.xpath(f'//tr/th[@class="attheader" and starts-with(text(), "Attack")]/../th[text()="Form"]/../../tr/td[last()]//img[@title="{form_alt_name}"]/@src').get()
                form_name = alt_name_dct[form_alt_name]
                form_pic = self.get_form_pic(response, len(forms), i)
                form_abilities = form_ability_dct[form_name] if form_ability_dct[form_name] else form_ability_dct['base']
                form_base_speed = self.get_form_speed(form_speed_dct, form_name, i)
                form_move_dct = self.get_moveset(response, icon=form_icon)

                pokemon = PokemonItem.create(url=response.request.url,
                                             base_name=name,
                                             name=form_name,
                                             number=number,
                                             generation=gen,
                                             icon=response.urljoin(form_icon) if form_icon else response.urljoin(icon),
                                             pic=response.urljoin(form_pic),
                                             abilities=form_abilities,
                                             base_speed=form_base_speed,
                                             alternate_forms=alternate_forms
                                             )

                for move_url, level in form_move_dct.items():
                    yield response.follow(move_url, callback=self.parse_move, meta={'size': len(form_move_dct), 'lvl': level, 'pokemon': pokemon}, dont_filter=True)
        else:
            pic = response.xpath('//table[@class="dextable"]/tr[2]/td/table/tr/td[1]/img/@src').get()
            abilities = response.xpath('(//a[@name="general"]/ancestor::div//td[@align="left" and @class="fooinfo"])[1]/a/b//text()').getall()
            base_speed = response.xpath('//table[@class="dextable"]/tr/td[starts-with(text(), "Base Stats")]/following-sibling::td[last()]//text()').get()
            move_dct = self.get_moveset(response)

            pokemon = PokemonItem.create(url=response.request.url,
                                         name=name,
                                         number=number,
                                         generation=gen,
                                         icon=response.urljoin(icon),
                                         pic=response.urljoin(pic),
                                         abilities=abilities,
                                         base_speed=base_speed,
                                         )

            for move_url, level in move_dct.items():
                yield response.follow(move_url, callback=self.parse_move, meta={'size': len(move_dct), 'lvl': level, 'pokemon': pokemon}, dont_filter=True)

        next_page = response.xpath('//table/tr/td[@align="right"]/table[@border="0"]/tr/td/a/@href')
        if next_page and (self.stop_at == -1 or self.stop_at > response.meta['count']):
            yield response.follow(next_page.get(), callback=self.parse_bw_dp, meta={'count': response.meta['count'] + 1, 'gen': gen})

    def parse_rs(self, response):
        gen = response.meta['gen']
        icon = response.xpath('//table[@class="dextab"]/tr/td[@width="65%"]/table/tr/td[1]/img/@src').get()
        number = response.xpath('//table[@class="dextab"]/tr/td[@width="65%"]/table/tr/td[2]//text()').get().strip().split(' ')[0]
        name = response.xpath('//table[@class="dextab"]/tr/td[@width="65%"]/table/tr/td[2]//text()').get().strip().split(' ')[1]
        abilities = response.xpath('//table[@width="98%"][1]/tr[4]//b//text()').getall()
        if not abilities:
            ability = response.xpath('//table[@width="98%"][1]/tr[3]/td[2]/b/text()').get()
            abilities = [ability.split(':')[1].strip()]
        move_dct = self.get_moveset(response, gen=gen)

        if name == 'Deoxys':  # Deoxys is only pokemon with multiple forms in Gen 3
            alternate_forms = ['Deoxys(Ruby/Sapphire)', 'Deoxys(FireRed)', 'Deoxys(LeafGreen)', 'Deoxys(Emerald)']

            for i in range(len(alternate_forms)):
                form_name = alternate_forms[i]
                form_pic = response.xpath('//table[@border="0" and @width="128"]/tr/td[@valign="center" and @width="50%"]/img/@src').getall()[i * 2]
                form_base_speed = response.xpath('//table[@bordercolor="#868686"]/tr/td[starts-with(text(), "Base Stats")]/following-sibling::td[last()]//text()').getall()[i]

                # print(f'name: {form_name} number: {number} icon: {icon} pic: {form_pic} abilities: {abilities} base_speed: {form_base_speed} alternate_forms: {alternate_forms}')
                pokemon = PokemonItem.create(url=response.request.url,
                                             base_name=name,
                                             name=form_name,
                                             number=number,
                                             generation=gen,
                                             icon=response.urljoin(icon),
                                             pic=response.urljoin(form_pic),
                                             abilities=abilities,
                                             base_speed=form_base_speed,
                                             alternate_forms=alternate_forms
                                             )

                for move_url, level in move_dct.items():
                    yield response.follow(move_url, callback=self.parse_move, meta={'size': len(move_dct), 'lvl': level, 'pokemon': pokemon}, dont_filter=True)
        else:
            pic = response.xpath('//table[@border="0" and @width="128"]/tr/td[@valign="center" and @width="50%"]/img/@src').get()
            base_speed = response.xpath('//table[@bordercolor="#868686"]/tr/td[starts-with(text(), "Base Stats")]/following-sibling::td[last()]//text()').get()

            pokemon = PokemonItem.create(url=response.request.url,
                                         name=name,
                                         number=number,
                                         generation=gen,
                                         icon=response.urljoin(icon),
                                         pic=response.urljoin(pic),
                                         abilities=abilities,
                                         base_speed=base_speed,
                                         )

            for move_url, level in move_dct.items():
                yield response.follow(move_url, callback=self.parse_move, meta={'size': len(move_dct), 'lvl': level, 'pokemon': pokemon}, dont_filter=True)

    def parse_gs_rby(self, response):
        gen = response.meta['gen']
        icon = response.xpath('//table[@class="dextab"]/tr/td[@width="65%"]/table/tr/td[1]/img/@src').get().strip()
        number = response.xpath('//table[@class="dextab"]/tr/td[@width="65%"]/table/tr/td[2]//text()').get().strip().split(' ')[0]
        name = response.xpath('//table[@class="dextab"]/tr/td[@width="65%"]/table/tr/td[2]//text()').get().strip().split(' ')[1]
        pic = response.xpath('//table[@class="dextable"]/tr[2]/td/table/tr/td[1]/img/@src').get()
        base_speed = response.xpath('//table[@class="dextable"]/tr/td[starts-with(text(), "Base Stats")]/following-sibling::td[last()]//text()').get()
        move_dct = self.get_moveset(response)

        pokemon = PokemonItem.create(url=response.request.url,
                                     name=name,
                                     number=number,
                                     generation=gen,
                                     icon=response.urljoin(icon),
                                     pic=response.urljoin(pic),
                                     base_speed=base_speed,
                                     )

        for move_url, level in move_dct.items():
            yield response.follow(move_url, callback=self.parse_move, meta={'size': len(move_dct), 'lvl': level, 'pokemon': pokemon}, dont_filter=True)

        next_page = response.xpath('//table/tr/td[@align="right"]/table[@border="0"]/tr/td/a/@href')
        if next_page and (self.stop_at == -1 or self.stop_at > response.meta['count']):
            yield response.follow(next_page.get(), callback=self.parse_gs_rby, meta={'count': response.meta['count'] + 1, 'gen': gen})

    def add_pokemon(self, pokemon):
        if not pokemon['abilities'] and (pokemon['generation'] != 'gs' and pokemon['generation'] != 'rby'):
            self.no_abilities.append(f'POKEMON: {pokemon["name"]} | URL: {pokemon["url"]} | GEN: {pokemon["generation"]}{pokemon["number"]}')

        if not pokemon['moves']:
            self.no_moves.append(f'POKEMON: {pokemon["name"]} | URL: {pokemon["url"]} | GEN: {pokemon["generation"]}{pokemon["number"]} | PIC: {pokemon["pic"]}')

        if 'html' in pokemon['pic'] or not pokemon['pic']:
            self.bad_pic.append(f'POKEMON: {pokemon["name"]} | URL: {pokemon["url"]} | GEN: {pokemon["generation"]}{pokemon["number"]} | PIC: {pokemon["pic"]}')

        if '.html' in pokemon['icon'] or not pokemon['icon']:
            self.bad_icon.append(f'POKEMON: {pokemon["name"]} | URL: {pokemon["url"]} | GEN: {pokemon["generation"]}{pokemon["number"]} | ICON: {pokemon["icon"]}')

        self.dct[pokemon['generation']][pokemon['name']] = pokemon  # Save pokemon by name to corresponding generation dictionary

        for mega_name, mega in pokemon['mega_dct'].items():
            mega['moves'] = pokemon['moves']
            mega['priority_moves'] = mega['priority_moves']
            pokemon['mega_list'].append(mega_name)

            self.dct[pokemon['generation']][mega['name']] = mega
            print(f'MEGA:{mega["name"]} | URL:{mega["url"]} | PIC:{mega["pic"]} | ICON:{mega["icon"]} | ABILITIES:{mega["abilities"]} | SPEED:{mega["base_speed"]} | GEN:{mega["generation"]}{mega["number"]} | ALTS:{mega["alternate_forms"]} M={len(mega["moves"])}')

        print(f'POKEMON:{pokemon["name"]} | URL:{pokemon["url"]} | PIC:{pokemon["pic"]} | ICON:{pokemon["icon"]} | ABILITIES:{pokemon["abilities"]} | SPEED:{pokemon["base_speed"]} | GEN:{pokemon["generation"]}{pokemon["number"]} | ALTS:{pokemon["alternate_forms"]} M={len(pokemon["moves"])}')

        # print(pokemon)

    def parse_move(self, response):
        gen_dct = {
            'Gen VII Dex': 'sm',
            'Gen VI Dex': 'xy',
            'Gen V Dex': 'bw',
            'Gen IV Dex': 'dp',
            'Gen III Dex': 'rs',
            'Gen II Dex': 'gs',
            'Gen I Dex': 'rby',
            'attackdex-sm': 'sm',
            'attackdex-xy': 'xy',
            'attackdex-bw': 'bw',
            'attackdex-dp': 'dp',
            'attackdex': 'rs',
            'attackdex-gs': 'gs',
            'attackdex-rby': 'rby'
        }

        gen_3_priority = {
            'Helping Hand': '5',
            'Magic Coat': '4',
            'Snatch': '4',
            'Detect': '3',
            'Endure': '3',
            'Follow Me': '3',
            'Protect': '3',
            'ExtremeSpeed': '1',
            'Fake Out': '1',
            'Mach Punch': '1',
            'Quick Attack': '1',
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

            if gen == gen_dct['Gen III Dex']:  # Serebii does not have
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

            if '(' in move['priority']:
                move['priority'] = re.sub('\\(.*?\\)', '', move['priority']).strip()

            self.move_dct[move['generation']][move['name']] = move
            self.move_dct['all'][move['url']] = move

            remaining = response.xpath('//table[@class="dextab"]/tr/td[@class="pkmn"]/a/@href')

            if remaining:
                for url in remaining:
                    yield response.follow(url.get(), callback=self.parse_move, dont_filter=True)

            # print(f'MOVE: {move["name"]}| URL: {move["url"]} |  GEN: {move["generation"]}')
            yield move

        if 'pokemon' in response.meta and 'size' in response.meta:
            move = self.move_dct['all'][current_move_url]

            pokemon = response.meta['pokemon']
            expected_moves_size = response.meta['size']
            p_lvl = response.meta['lvl']

            pokemon['moves'].append({'name': move['name'], 'level': p_lvl, 'priority': move['priority']})

            if move['priority'] != '0':
                pokemon['priority_moves'].append({'name': move['name'], 'level': p_lvl, 'priority': move['priority']})

            if len(pokemon['moves']) == expected_moves_size:
                self.add_pokemon(pokemon)
                yield pokemon

    def spider_closed(self, spider):
        for i in self.no_abilities:
            print(f'NO ABILITIES: {i}')

        for i in self.no_moves:
            print(f'NO MOVES: {i}')

        for i in self.bad_icon:
            print(f'ICON: {i}')

        for i in self.bad_pic:
            print(f'PIC: {i}')

        # print(f'SM: {self.dct["sm"]}')
        # print(f'XY: {self.dct["xy"]}')
        #
        # print(f'BW: {self.dct["bw"]}')
        # print(f'DP: {self.dct["dp"]}')
        #
        # print(f'RS: {self.dct["rs"]}')
        #
        # print(f'GS: {self.dct["gs"]}')
        # print(f'RBY: {self.dct["rby"]}')
        print("DONE")
