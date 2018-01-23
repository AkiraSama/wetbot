import logging
import random
import re

import discord
from discord.ext import commands

log = logging.getLogger(__name__)
log.setLevel(logging.DEBUG)

class UtilCog(object):
    roll_check = re.compile(
        r'(\b)(?P<roll>(?P<dice>\d*)d(?P<sides>\d+|%)(?P<sign>[+-])?(?P<modifier>\d*)(?:dc)?(?P<threshold>\d*))($|\s)',
        re.IGNORECASE)

    def __init__(self, bot):
        self.bot = bot

    @commands.command(aliases=['c'])
    async def choose(self, ctx, *, pipe_separated_choices):
        """PROGRAMMED VERY FAST
        
        example usage:
        !choose one | two | three"""
        if random.random() > 0.95:
            await ctx.send("yes")
            return
        choices = pipe_separated_choices.split('|')
        await ctx.send('**{}**'.format(random.choice(choices).strip()))

    @commands.command()
    async def roll(self, ctx, *, expressions):
        """roll dice for numbers

        Matches to the expression:
        ``[die]d(sides)[+/-][modifier][dc][threshold]``
        Where...
        die       == number of die to roll  (1 if none)
        sides     == number of sides per die (100 if %)
        modifier  == number to add to each result
        threshold == number required for roll to succeed

        Note that the only required elements are the 'd' and the number of
        sides. Everything else can be included or disincluded at your leisure.
        """
        dice_rolls = []
        while self.roll_check.match(expressions):
            dice_roll, *expressions = expressions.split(maxsplit=1)
            expressions = expressions[0] if expressions else ''
            dice_rolls.append(self.roll_check.match(dice_roll))
        results = ctx.author.mention
        if not dice_rolls:
            await ctx.send(results + " I can't roll that doofus")
            return
        for dice_roll in dice_rolls:
            rolls = tuple(
                (random.randrange((100 if dice_roll.group('sides') == '%' else int(dice_roll.group('sides')))) + 1 + (
                     int(dice_roll.group('modifier')) if dice_roll.group('sign') == '+' else
                    -int(dice_roll.group('modifier')) if dice_roll.group('sign') == '-' else 0
                ) for x in range(int(dice_roll.group('dice')) if dice_roll.group('dice') else 1)))
            results += ' {} = {}{}'.format(
                dice_roll.group('roll'),
                str(sum(rolls)),
                (' (' + ', '.join(str(r) + (
                 ('**\u2713**' if int(dice_roll.group('threshold')) <= r
                    else '\u2718') if dice_roll.group('threshold') else '')
                 for r in rolls) + ')' if len(rolls) > 1 else
                 ('**\u2713**' if int(dice_roll.group('threshold')) <= sum(rolls)
                    else '\u2718') if dice_roll.group('threshold') else ''))
            await ctx.send('{}{}'.format(results, ' **' + expressions + '**' if expressions else ''))

def setup(bot):
    log.info("adding UtilCog to bot")
    bot.add_cog(UtilCog(bot))

