from __future__ import absolute_import
from fuzzywuzzy import process, fuzz
from sopel import module

import os
import sqlite3
import requests

# Nutr_No constants
CALORIE = 208
PROTEIN = 203
FAT = 204
CARB = 205
SUGAR = 269
FIBER = 291

LOOKUPURL = "https://ndb.nal.usda.gov/ndb/search/list"

apikeyfn = os.path.join(os.path.dirname(__file__), 'usdaapikey')
with open(apikeyfn, 'r') as f:
    APIKEY = f.read().strip()

class NDBSearch():
    def __init__(self):
        self.exclude_foodgroups = {'Baby Foods'}

    def process_response(self, r):
        if r.ok:
            return r.json()
        else:
            return {}

    def search(self, name):
        payload = {'format': 'json',
                  'ds': 'Standard Reference',
                  'q': name,
                  'sort': 'r',
                  'max': 50,
                  'api_key': APIKEY}
        url = 'https://api.nal.usda.gov/ndb/search/'
        r = requests.get(url, params=payload)
        return self.process_response(r)
    
    def get_calories(self, ndbno):
        payload = {'format': 'json', 
                   'api_key': APIKEY,
                   'nutrients': CALORIE,
                   'ndbno': ndbno}
        url = 'https://api.nal.usda.gov/ndb/nutrients/'
        r = requests.get(url, params=payload)
        data = self.process_response(r)
        if data and data['report']['total'] > 0:
            firstfood = data['report']['foods'][0]
            nutrients = firstfood['nutrients']
            for n in nutrients:
                nid = int(n['nutrient_id'])
                calperg = next(n['gm'] for n in nutrients if nid == CALORIE)
            return int(calperg)
        else:
            return False
        
NDBSearch = NDBSearch()

@module.rate(10)
@module.commands("cal", "calories")
@module.example("!calories cheddar cheese")
def calories_command(bot, trigger):
    query = trigger.group(2)
    results = NDBSearch.search(query)
    if 'list' in results.keys():
        import q; q.q(results['list']['item'])
        filtered_results = [food['name'] for food in results['list']['item'] if food['group'] not in NDBSearch.exclude_foodgroups]
        weighted = process.extract(query, filtered_results, scorer=fuzz.token_sort_ratio)
        topFood = [food for food in results['list']['item'] if food['name'] == weighted[0][0]][0]
        foodname = topFood['name']
        ndbno = topFood['ndbno']
        calories = NDBSearch.get_calories(ndbno)
        if calories:
              replystr = ('"{foodname}" has {calories:.0f} kcal per 100 g.'
                          'See more results at {url}?ds=Standard+Reference&qlookup={query}')
              bot.reply(replystr.format(
                foodname=foodname, 
                calories=calories, 
                url=LOOKUPURL,
                query=requests.utils.quote(query))
              )
        else:
            bot.reply("No result")
