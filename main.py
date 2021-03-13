import re
import sys
import discord
from discord.ext.commands import Bot

from codemap import code_map

bot = Bot(command_prefix="hc!", case_insensitive=True)

status_code_regex = re.compile(r'^((\d{4}) :: (\d{3}))( :: (.*))?$', re.DOTALL)
'''
Regex groups for full status code regex:
0: Full match. ("0001 :: 200 :: Additional information")
1: Plain status code ("0001 :: 200")
2: Author's drone ID ("0001")
3: Status code ("200")
4: Informative status addition with double colon (" :: Additional information")
5: Informative status text. ("Additional information")
'''

address_by_id_regex = re.compile(r'(\d{4})( :: (.*))?', re.DOTALL)
'''
This regex is to be checked on the status regex's 5th group when the status code is 110 (addressing).
0: Full match ("0001 :: Additional information")
1: ID of drone to address ("0001")
2: Informative status text with double colon (" :: Additional information")
3: Informative status text ("Additional information")
'''

@bot.event
async def on_message(message: discord.Message):
    print("on_message event triggered.")

    code_match = status_code_regex.match(message.content)

    if code_match is None:
        return

bot.run(sys.argv[1])