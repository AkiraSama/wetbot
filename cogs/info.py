import aiohttp
import json
import logging
import urllib.parse

import discord
from discord.ext import commands

log = logging.getLogger(__name__)
log.setLevel(logging.DEBUG)

WIKIPEDIA_URL = 'https://en.wikipedia.org/w/api.php'
UD_URL = 'http://api.urbandictionary.com/v0/define?term={}'
OXFORD_URL = 'https://od-api.oxforddictionaries.com/api/v1'

DEF_TEMPLATE = (
    '```\n{word}{domains}\n/{pronunciation}/, '
    '{category}\n{definition}```'
)

def json_format(response):
    return '```json\n{}```'.format(
        json.dumps(response, indent='  '))

class InfoCog(object):
    def __init__(self, bot):
        self.bot = bot
        self.session = bot.http._session
        self.active_definitions = {}

    async def _wiki_get_pageid(self, query):
        query = urllib.parse.quote_plus(query)
        query_string = ('?action=query'
                        '&list=search'
                        '&format=json'
                        '&srsearch={}'
                        '&srinfo=suggestion'
                        '&srprop=redirecttitle')

        async with self.session.get(
            WIKIPEDIA_URL + query_string.format(query),
            timeout=5
        ) as resp:
            if resp.status == 200:
                response = await resp.json()
                results = response.get('query')
                if results:
                    if results['search']:
                        return (str(results['search'][0]['pageid']), None)
                    else:
                        try:
                            return await self._wiki_get_pageid(
                                results['searchinfo']['suggestion'])
                        except KeyError:
                            return (
                                None,
                                "I got nothin ¯\_(ツ)_/¯")
                else:
                    return (
                        None,
                        json_format(response))

    @commands.command(aliases=('wiki', 'w'))
    async def wikipedia(self, ctx, *, query):
        """search all the knowledge"""
        pageid, error = await self._wiki_get_pageid(query)

        if pageid is None:
            await ctx.send(error)
            return

        query_string = ('?action=query'
                        '&prop=info'
                        '&format=json'
                        '&pageids={}'
                        '&inprop=url')

        async with self.session.get(
            WIKIPEDIA_URL + query_string.format(pageid),
            timeout=5
        ) as resp:
            if resp.status == 200:
                response = await resp.json()
                results = response.get('query')
                if results:
                    out = results['pages'][pageid]['canonicalurl']
                else:
                    out = json_format(response)

        await ctx.send(out)

    @commands.command(aliases=('ud',))
    async def urbandictionary(self, ctx, *, query):
        """search all the OTHER knowledge"""
        async with self.session.get(
            UD_URL.format(urllib.parse.quote(query)),
            timeout=5
        ) as resp:
            if resp.status == 200:
                response = await resp.json()
                results = response.get('list')
                if results:
                    out = ('http://urbandictionary.com/define.php?term=' +
                           urllib.parse.quote(results[0]['word']))
                elif response.get('result_type') == 'no_results':
                    out = "I got nothin ¯\_(ツ)_/¯"
                else:
                    out = json_format(response)

        await ctx.send(out)

    domain_str = lambda self, domains: ' ({})'.format(', '.join(domains))
    def iterate_definitions(self, response):
        for lexical_entry in response['lexicalEntries']:
            word = lexical_entry['text']
            pronunciation = '/ ᴏʀ /'.join(
                p['phoneticSpelling']
                for p
                in lexical_entry['pronunciations']
            )
            category = lexical_entry['lexicalCategory'].lower()
            for entry in lexical_entry['entries']:
                for sense in entry['senses']:
                    if 'definitions' not in sense:
                        continue
                    for definition in sense['definitions']:
                        yield {
                            'word': word,
                            'domains': (
                                self.domain_str(sense['domains'])
                                if 'domains' in sense
                                else ''),
                            'pronunciation': pronunciation,
                            'category': category,
                            'definition': definition
                        }
                    if 'subsenses' not in sense:
                        continue
                    for subsense in sense['subsenses']:
                        for definition in subsense['definitions']:
                            yield {
                                'word': word,
                                'domains': (
                                    self.domain_str(subsense['domains'])
                                    if 'domains' in subsense
                                    else ''),
                                'pronunciation': pronunciation,
                                'category': category,
                                'definition': definition
                            }


    @commands.command(aliases=('d',))
    async def define(self, ctx, *, query=None):
        """mommy fixed it
        
        after requesting a definition, use the command with no query
        in the same channel to cycle through additional meanings"""
        if not query:
            try:
                if ctx.channel.id in self.active_definitions:
                    await ctx.send(DEF_TEMPLATE.format(
                        **next(self.active_definitions[
                            ctx.channel.id
                        ])))
                    return
                else:
                    await ctx.send("no active definitions!")
            except StopIteration:
                await ctx.send("ran outta definitions, friend")
                del self.active_definitions[ctx.channel.id]
                return

        app_id = self.bot.config.get('oxford_dictionaries', 'app_id', '')
        app_key = self.bot.config.get('oxford_dictionaries', 'app_key', '')
        if not app_id or not app_key:
            await ctx.send("configuration incomplete")
            return
        headers = {
            'app_id': app_id,
            'app_key': app_key
        }

        word_id = None
        async with self.session.get(
            OXFORD_URL + '/search/en?q=' + urllib.parse.quote(query),
            headers=headers,
            timeout=5
        ) as resp:
            if resp.status == 200:
                response = await resp.json()
                if response['metadata']['total'] > 0:
                    word_id = response['results'][0]['id']
                else:
                    await ctx.send("I got nothin ¯\_(ツ)_/¯")
                    return

        async with self.session.get(
            OXFORD_URL + '/entries/en/' + word_id,
            headers=headers,
            timeout=5
        ) as resp:
            if resp.status == 200:
                result = (await resp.json())['results'][0]

        self.active_definitions[ctx.channel.id] = (
            self.iterate_definitions(result)
        )

        await ctx.send(DEF_TEMPLATE.format(
            **next(self.active_definitions[ctx.channel.id])
        ))

def setup(bot):
    log.info("adding InfoCog to bot")
    bot.add_cog(InfoCog(bot))

