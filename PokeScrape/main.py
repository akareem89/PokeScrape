from scrapy import cmdline



def run_priority_bot():
    cmdline.execute("scrapy crawl priority_bot ".split())

def run_pokemon_bot():
    cmdline.execute("scrapy crawl pokemon_bot ".split())

def run_pokemon_bot_w_output():
    cmdline.execute("scrapy crawl pokemon_bot -o pokemon.json ".split())

# run_priority_bot()

run_pokemon_bot()

# run_pokemon_bot_w_output()