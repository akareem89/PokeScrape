import json
import math
from os import path

from scrapy import cmdline


def run_priority_bot():
    cmdline.execute("scrapy crawl priority_bot ".split())


def run_pokemon_bot():
    cmdline.execute("scrapy crawl pokemon_bot ".split())


def run_pokemon_bot_w_output():
    cmdline.execute("scrapy crawl pokemon_bot -o pokemon.json ".split())


def check_count(folder=""):
    print("IN check_count")
    count_dct = {}

    for i in range(1, 8):
        json_file = f"{folder}gen{i}.json"

        if path.exists(json_file):
            print(f"OPENING: {json_file}")
            # poke_dct = {}
            with open(json_file) as json_data:
                poke_dct = json.load(json_data)
                count_dct[json_file] = len(poke_dct)

    print(f"count_dct: {count_dct}")


def group_alternate_forms(base_name, pokemon_lst):
    # pokemon_lst = pokemon['alternate_forms'].copy()
    # base_name = pokemon['base_name']

    checked_hash = {}  # all groups key initial pokemon in group
    while pokemon_lst:
        current_pokemon = pokemon_lst[0]
        current_hash = poke_hash(current_pokemon)
        checked_hash[current_pokemon['name']] = [current_pokemon]

        for other_pokemon in pokemon_lst[1:]:
            if current_hash == poke_hash(other_pokemon):
                checked_hash[current_pokemon['name']].append(other_pokemon)
                pokemon_lst.remove(other_pokemon)

        pokemon_lst.remove(current_pokemon)

    groups = {}
    if len(checked_hash) > 1:
        groups[base_name] = []
        for key, lst in checked_hash.items():
            if len(lst) > 1:  # If has more than one item per has, find a way to group under single name
                if base_name in lst:  # if base name is in list of grouped item with single hash, they will be under base name
                    groups[base_name] = lst
                else:
                    name_lst = [pokemon['name'] for pokemon in lst]
                    common = find_common(name_lst, base_name)  # Find common name in group
                    if common:
                        use_common = True
                        for item, value in checked_hash.items():  # Ensure common name does not exist in another hash group
                            name_lst = [pokemon['name'] for pokemon in value]
                            if item != key and word_in_all(common, name_lst):
                                use_common = False

                        if not use_common and len(groups[base_name]) < len(lst):  # group with most forms takes priority in cases of groups with same common name
                            for item in groups[base_name]:
                                groups[item] = [item]

                            groups[base_name] = lst
                        else:
                            groups[f'{base_name}({common})'] = lst
                    else:
                        for item in lst:
                            groups[item['name']] = [item]  # If there is not a common name, each form will be its own group
            else:
                groups[lst[0]['name']] = lst

    else:
        for form_lst in checked_hash.values():
            groups[base_name] = form_lst  # No differences found between forms - all grouped under base name
            # groups[base_name] = [form['name'] for form in form_lst]  # No differences found between forms - all grouped under base name

    if not groups[base_name]:
        del groups[base_name]

    return groups


def find_common(lst, base):
    lst = [name.replace('(', ' ') for name in lst]
    lst = [name.replace(')', ' ') for name in lst]
    lst = [name.replace(base, '') for name in lst]

    for form_name in lst:
        words = form_name.strip().split(' ')  # 'Green Core
        for word in words:
            if word_in_all(word, lst):
                return word

    return ''


def word_in_all(word, lst):
    is_valid = True
    i = 0
    while is_valid and i < len(lst):
        if word not in lst[i]:
            is_valid = False
        i += 1

    return is_valid


def poke_hash(pokemon):
    speed_hash = hash(pokemon['base_speed'])

    abilities_hash = 0
    for ability in pokemon['abilities']:
        abilities_hash += hash(ability)

    moves_hash = 0
    for move in pokemon['moves']:
        # for move in poke_dct['priority_moves']:
        moves_hash += hash(move['name'])

    return speed_hash + abilities_hash + moves_hash


gen_dct = {
    'sm': '7',
    'xy': '6',
    'bw': '5',
    'dp': '4',
    'rs': '3',
    'gs': '2',
    'rby': '1',
}

def format_for_priority(gen=None):
    speed_abilities = ['Chlorophyll', 'Swift Swim', 'Slush Rush', 'Surge Surfer', 'Unburden', 'Quick Feet']
    save_dir = '_formatted/'
    load_dir = '_json/'
    json_file = f"{load_dir}gen{gen}.json"
    if path.exists(json_file):
        print(f"OPENING: {json_file}")

        with open(json_file) as json_data:
            scrape_dct = json.load(json_data)

            poke_dct = {}
            has_alternates = {}
            for pokemon in scrape_dct:
                if pokemon['alternate_forms']:  # Add to poke_dict after grouping
                    if pokemon['base_name'] in has_alternates:
                        has_alternates[pokemon['base_name']].append(pokemon)
                    else:
                        has_alternates[pokemon['base_name']] = [pokemon]
                else:
                    item_dct = {
                        'number': pokemon['number'].replace('#', '').strip(),
                        'generation': gen_dct[pokemon['generation']],
                        'name': pokemon['name'],
                        'priority_moves': {move['name']: move for move in pokemon['priority_moves']},
                        # 'all_moves': {move['name']: move for move in pokemon['moves']},
                        'abilities': [ability for ability in pokemon['abilities'] if ability in speed_abilities],
                        'speed': pokemon['base_speed'],
                        'pic': get_image_filename(pokemon['pic']),
                        'icon': get_image_filename(pokemon['icon']),
                        'alternate_forms': pokemon['alternate_forms'],
                        'mega_list': pokemon['mega_list'],
                        'base_name': pokemon['base_name'],
                        'url': pokemon['url']
                    }

                    poke_dct[item_dct['name'].lower()] = item_dct

            for base_name, pokemon_lst in has_alternates.items():

                # print(f"{base_name} has alternate- {[pokemon['name'] for pokemon in pokemon_lst]}")
                groupings = group_alternate_forms(base_name, pokemon_lst)

                # print(f"GROUPS: {groupings}")

                for group_name, lst in groupings.items():
                    pokemon = lst[0]  # Use first pokemon in list
                    item_dct = {
                        'number': pokemon['number'].replace('#', '').strip(),
                        'name': group_name,
                        'priority_moves': {move['name']: move for move in pokemon['priority_moves']},
                        # 'all_moves': {move['name']: move for move in pokemon['moves']},
                        'abilities': [ability for ability in pokemon['abilities'] if ability in speed_abilities],
                        'speed': pokemon['base_speed'],
                        'pic': get_image_filename(pokemon['pic']),
                        'icon': get_image_filename(pokemon['icon']),
                        'alternate_forms': pokemon['alternate_forms'],
                        'mega_list': pokemon['mega_list'],
                        'base_name': pokemon['base_name'],
                        'url': pokemon['url']
                    }

                    poke_dct[item_dct['name'].lower()] = item_dct

            with open(f'{save_dir}gen{gen}.json', 'w') as outfile:
                json.dump(poke_dct, outfile)

def get_image_filename(image_url):
    x = [a for a in image_url.split('/') if a]
    filename = '/'.join(x[-2:])

    return filename

def get_speed(gen, pokemon_name, level, nature, iv, ev=None, **kwargs):
    with open(f'saved/scarf_gen{gen}.json') as json_data:
        poke_dct = json.load(json_data)

        pokemon = poke_dct[pokemon_name.lower()]
        base_speed = int(pokemon['speed'])


        ability_multiplier = {
            'Chlorophyll': 2,
            'Swift Swim': 2,
            'Slush Rush': 2,
            'Sand Rush': 2,
            'Surge Surfer': 2,
            'Unburden': 2,
            'Quick Feet': 1.5,
        }

        scarf_multiplier = 1.5

        if gen < 3:
            speed = int(((base_speed + iv) * 2 + 63) * level / 100) + 5
        else:
            speed = int((int(((2 * base_speed + iv + int(ev/4)) * level) / 100) + 5) * nature)

        return speed


# run_priority_bot()

# run_pokemon_bot()

# format_for_priority(3)

# check_count()
for i in range(3, 8):
    format_for_priority(i)

# print(f"Mimikyu: {get_speed(7, 'Mimikyu', 67, 1, 31, 252)}")
#
# print(f"Charizard: {get_speed(2, 'Charizard', 67, 1, 15)}")

# check_count("saved/")
# run_pokemon_bot_w_output()

# /Mimikyu


#
