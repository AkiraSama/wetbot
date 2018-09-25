import asyncio
import logging
import random
import re
from datetime import datetime, timedelta

from discord.ext.commands import Context, command, clean_content

from wetbot.bot import Wetbot

log = logging.getLogger(__name__)
log.setLevel(logging.DEBUG)

ROLL_CHECK = re.compile(
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

TIME_FORMAT = re.compile(
    r'('
    r'((?P<days>\d+)d)?'
    r'((?P<hours>\d+)h)?'
    r'((?P<minutes>\d+)m)?'
    r'((?P<seconds>\d+)s)?'
    r')'
)

POLL_PERIOD = 3600


class UtilCog(object):
    def __init__(self, bot: Wetbot):
        self.bot = bot
        self.db = bot.db.util
        self._polling_future = bot.loop.create_task(self.poll_reminders())
        self._reminders = []

    def __unload(self):
        futures = asyncio.gather(
            self._polling_future,
            *self._reminders,
            return_exceptions=True,
        )
        try:
            futures.cancel()
        except asyncio.CancelledError:
            pass

    @command(aliases=['c'])
    async def choose(self, ctx: Context, *, pipe_separated_choices: str):
        """PROGRAMMED VERY FAST

        example usage:
        !choose one | two | three"""
        if random.random() > 0.95:
            await ctx.send("yes")
            return
        choices = pipe_separated_choices.split('|')
        await ctx.send('**{}**'.format(random.choice(choices).strip()))

    @command(ignore_extra=False)
    async def flip(self, ctx: Context):
        """fine"""

        await ctx.send('**{}**'.format(
            'heads' if random.random() < 0.5 else 'tails'))

    @command()
    async def roll(self, ctx: Context, *, expressions: str = 'd20'):
        """roll dice for numbers

        Matches to the expression:
        ``[die]d<sides>[+/-<modifier>][dc<threshold>]``
        Where...
        die       == number of die to roll  (1 if none)
        sides     == number of sides per die (100 if %)
        modifier  == number to add to each result
        threshold == number required for roll to succeed

        Note that the only required elements are the 'd' and the number of
        sides. Everything else can be included or excluded at your leisure.
        """

        dice_rolls = []
        # Match valid expressions in expressions until we've got no more.
        while ROLL_CHECK.match(expressions):
            dice_roll, *expressions = expressions.split(maxsplit=1)
            expressions = expressions[0] if expressions else ''
            dice_rolls.append(ROLL_CHECK.match(dice_roll))

        # We begin our output with a mention to the calling user.
        output = ctx.author.mention
        if not dice_rolls:  # No valid expressions.
            await ctx.send(output + " I can't roll that doofus")
            return

        # Evaluate each dice roll expression.
        for dice_roll in dice_rolls:
            rolls = []

            # Number of dice is optional, assume 1.
            if dice_roll.group('dice'):
                dice = int(dice_roll.group('dice'))
            else:
                dice = 1

            # Special syntax % for 100-sided die.
            if dice_roll.group('sides') == '%':
                sides = 100
            else:
                sides = int(dice_roll.group('sides'))

            # Do all the rolling.
            for _ in range(dice):
                num = random.randrange(sides) + 1

                # Resolve modifiers for each roll.
                if dice_roll.group('modifier'):
                    modifier = int(dice_roll.group('modifier'))
                    if dice_roll.group('sign') == '-':
                        modifier *= -1
                    num += modifier

                rolls.append(num)

            roll_sum = sum(rolls)
            threshold = dice_roll.group('threshold')

            if len(rolls) > 1:
                # We've got more than one roll, the suffix appended to the
                # sum will be a list of the individual rolls.

                end = ' ({})'.format(', '.join(  # Join all the rolls.
                    str(roll) + (
                        # If a threshold exists, chuck in some Unicode.
                        ('**\u2713**'
                         if int(threshold) <= roll
                         else '\u2718')
                        if threshold else ''
                    ) for roll in rolls
                ))
            else:
                # We have only one roll, the sum is sufficient to represent
                # the dice rolled.
                if threshold:
                    # If a threshold exists, chuck in some Unicode.
                    end = ('**\u2713**'
                           if int(threshold) <= roll_sum
                           else '\u2718')
                else:
                    end = ''

            # Extend our output with the results of this roll.
            output += ' {roll} = {sum}{end}'.format(
                roll=dice_roll.group('roll'),
                sum=roll_sum,
                end=end,
            )

        # Send across all the results, and anything in expressions that
        # wasn't matched as a dice roll.
        await ctx.send('{output}{rest}'.format(
            output=output,
            rest=f' **{expressions}**' if expressions else ''
        ))

    async def schedule_reminder(self, reminder_doc):
        date = datetime.fromtimestamp(reminder_doc['timestamp'])
        diff = date - datetime.utcnow()
        if diff <= timedelta(POLL_PERIOD):
            async def reminder():
                await asyncio.sleep(diff.total_seconds())
                delete_result = await self.db.reminders.delete_one(
                    {'_id': reminder_doc['_id']})
                if delete_result.deleted_count == 0:
                    return
                channel = self.bot.get_channel(
                    reminder_doc['channel_id'])
                mention = self.bot.get_user(
                    reminder_doc['user_id']).mention
                text = reminder_doc['text']
                await channel.send(
                    f"{mention} {text}")
            self._reminders.append(
                self.bot.loop.create_task(reminder())
            )

    async def poll_reminders(self):
        while True:
            async for reminder in self.db.reminders.find():
                await self.schedule_reminder(reminder)
            await asyncio.sleep(POLL_PERIOD)

    @command()
    async def remind(self, ctx: Context,
                     time_delay: str, *,
                     reminder_text: clean_content()
                     ):
        """https://www.youtube.com/watch?v=YVkUvmDQ3HY

        takes a time_delay in the format of
        ``[days]d[hours]h[minutes]m[seconds]``

        still limited to 14 days because I don't wanna deal with
        absolute loads of reminders for future dates clogging up
        my database atm
        """

        delay = TIME_FORMAT.match(time_delay)
        delay_dict = {
            key: int(value)
            for key, value
            in delay.groupdict(default=0).items()
        }

        delta = timedelta(**delay_dict)
        if delta == timedelta(0):
            await ctx.send("invalid timestring!")
            return
        if delta > timedelta(days=14):
            await ctx.send("nnnnnnno")
            return
        remind_time = datetime.utcnow() + delta

        doc = {
            'timestamp': remind_time.timestamp(),
            'text': reminder_text,
            'channel_id': ctx.channel.id,
            'user_id': ctx.author.id,
        }

        result = await self.db.reminders.insert_one(doc)
        doc['_id'] = result.inserted_id

        await self.schedule_reminder(doc)
        await ctx.send(f"I'll remind you about that in {delta}")


def setup(bot: Wetbot):
    log.info("adding UtilCog to bot")
    bot.add_cog(UtilCog(bot))
