import re
import io
import sys
import discord
from enum import Enum
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

class StatusType(Enum):
    NONE = 1
    PLAIN = 2
    INFORMATIVE = 3
    ADDRESS_BY_ID_PLAIN = 4
    ADDRESS_BY_ID_INFORMATIVE = 5

def get_status_type(message: str):

    code_match = status_code_regex.match(message)

    if code_match is None:
        return (StatusType.NONE,None,None)

    # Special case handling for addressing by ID.
    if code_match.group(3) == "110" and code_match.group(5) is not None:
        address_match = address_by_id_regex.match(code_match.group(5))
        if address_match is None:
            return (StatusType.INFORMATIVE,code_match,None)
        elif address_match.group(2) is not None:
            return (StatusType.ADDRESS_BY_ID_INFORMATIVE,code_match,address_match)
        else:
            return (StatusType.ADDRESS_BY_ID_PLAIN,code_match,address_match)
    
    elif code_match.group(4) is not None:
        return (StatusType.INFORMATIVE,code_match,None)
    else:
        return (StatusType.PLAIN,code_match,None)

async def get_webhook_for_channel(channel: discord.TextChannel) -> discord.Webhook:
    webhooks = await channel.webhooks()
    if len(webhooks) == 0:
        # No webhook available, create one.
        found_webhook = await channel.create_webhook(name="HexCorp Portable AI")
    else:
        found_webhook = webhooks[0]
    return found_webhook

@bot.event
async def on_message(message: discord.Message):
    print("on_message event triggered.")

    status_type, code_match, address_match = get_status_type(message.content)

    if status_type == StatusType.NONE:
        await bot.process_commands(message)
        return

    status_message = ""
    base_message = f"{code_match.group(2)} :: Code `{code_match.group(3)}` :: "

    if status_type == StatusType.PLAIN:
        status_message = f"{base_message} {code_map.get(code_match.group(3), 'INVALID CODE')}"
    elif status_type == StatusType.INFORMATIVE:
        status_message = f"{base_message} {code_map.get(code_match.group(3), 'INVALID CODE')}{code_match.group(4)}"
    elif status_type == StatusType.ADDRESS_BY_ID_PLAIN:
        status_message = f"{base_message}Addressing: Drone #{address_match.group(1)}"
    elif status_type == StatusType.ADDRESS_BY_ID_INFORMATIVE:
        status_message = f"{base_message}Addressing: Drone #{address_match.group(1)}{address_match.group(2)}"

    webhook = await get_webhook_for_channel(message.channel)

    # Convert any message attachments
    attachments_as_files = []
    for attachment in message.attachments:
        attachments_as_files.append(discord.File(io.BytesIO(await attachment.read()), filename=attachment.filename))

    await message.delete()
    await webhook.send(
        content=status_message,
        username=message.author.display_name,
        avatar_url=message.author.avatar_url
        )

@bot.command(name="list")
async def _list(context, page = 1):
    print("List command triggered.")
    map_length = len(code_map)

bot.run(sys.argv[1])