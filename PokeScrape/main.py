import json
from os import path

from scrapy import cmdline


def run_priority_bot():
    cmdline.execute("scrapy crawl priority_bot ".split())


def run_pokemon_bot():
    cmdline.execute("scrapy crawl pokemon_bot ".split())


def run_pokemon_bot_w_output():
    cmdline.execute("scrapy crawl pokemon_bot -o pokemon.json ".split())


def check_count():
    print("IN check_count")
    count_dct = {}

    for i in range(1, 8):
        json_file = f"gen{i}.json"

        if path.exists(json_file):
            print(f"OPENING: {json_file}")
            # poke_dct = {}
            with open(json_file) as json_data:
                poke_dct = json.load(json_data)
                count_dct[json_file] = len(poke_dct)

    print(f"count_dct: {count_dct}")





# run_priority_bot()

run_pokemon_bot()
check_count()

# run_pokemon_bot_w_output()
