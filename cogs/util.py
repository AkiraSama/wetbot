import logging
import random
import re

from discord.ext import commands

log = logging.getLogger(__name__)
log.setLevel(logging.DEBUG)


class UtilCog(object):
    roll_check = re.compile(
        (r'(\b)'
         r'(?P<roll>'
         r'(?P<dice>\d*)d'
         r'(?P<sides>\d+|%)'
         r'(?P<sign>[+-])?(?P<modifier>\d*)'
         r'(?:dc)?(?P<threshold>\d*)'
         r')'
         r'($|\s)'
         ),
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
        ``[die]d<sides>[+/-<modifier>][dc<threshold>]``
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
            rolls = []

            dice = (int(dice_roll.group('dice'))
                    if dice_roll.group('dice')
                    else 1)

            sides = (100
                     if dice_roll.group('sides') == '%'
                     else int(dice_roll.group('sides')))

            for _ in range(dice):
                num = random.randrange(sides) + 1
                if dice_roll.group('modifier'):
                    modifier = int(dice_roll.group('modifier'))
                    if dice_roll.group('sign') == '-':
                        modifier *= -1
                    num += modifier
                rolls.append(num)

            roll_sum = sum(rolls)
            threshold = dice_roll.group('threshold')
            if len(rolls) > 1:
                end = ' ({})'.format(', '.join(
                    str(roll) + (
                        ('**\u2713**'
                         if int(threshold) <= roll
                         else '\u2718')
                        if threshold else ''
                    ) for roll in rolls
                ))
            else:
                if threshold:
                    end = ('**\u2713**'
                           if int(threshold) <= roll_sum
                           else '\u2718')
                else:
                    end = ''

            results += ' {roll} = {sum}{end}'.format(
                roll=dice_roll.group('roll'),
                sum=roll_sum,
                end=end,
            )
        await ctx.send('{results}{rest}'.format(
            results=results,
            rest=f' **{expressions}**' if expressions else ''
        ))


def setup(bot):
    log.info("adding UtilCog to bot")
    bot.add_cog(UtilCog(bot))
