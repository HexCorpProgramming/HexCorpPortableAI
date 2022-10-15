import re
import io
import sys
from typing import Tuple
import discord
from enum import Enum
from discord.ext import commands, tasks

from codemap import code_map

bot = commands.Bot(command_prefix="hc!", case_insensitive=True, help_command=None)

DRONE_AVATAR = "https://images.squarespace-cdn.com/content/v1/5cd68fb28dfc8ce502f14199/1586799484353-XBXNJR1XBM84C9YJJ0RU/ke17ZwdGBToddI8pDm48kLxnK526YWAH1qleWz-y7AFZw-zPPgdn4jUwVcJE1ZvWEtT5uBSRWt4vQZAgTJucoTqqXjS3CfNDSuuf31e0tVFUQAah1E2d0qOFNma4CJuw0VgyloEfPuSsyFRoaaKT76QvevUbj177dmcMs1F0H-0/Drone.png"

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

def optimize_speech(message_content: str) -> Tuple[bool, str]:

    status_type, code_match, address_match = get_status_type(message_content)

    if status_type == StatusType.NONE:
        return False, None

    base_message = f"{code_match.group(2)} :: Code `{code_match.group(3)}` :: "

    if status_type == StatusType.PLAIN:
        return True, f"{base_message}{code_map.get(code_match.group(3), 'INVALID CODE')}"
    elif status_type == StatusType.INFORMATIVE:
        return True, f"{base_message}{code_map.get(code_match.group(3), 'INVALID CODE')}{code_match.group(4)}"
    elif status_type == StatusType.ADDRESS_BY_ID_PLAIN:
        return True, f"{base_message}Addressing: Drone #{address_match.group(1)}"
    elif status_type == StatusType.ADDRESS_BY_ID_INFORMATIVE:
        return True, f"{base_message}Addressing: Drone #{address_match.group(1)}{address_match.group(2)}"

def enforce_identity(author):
    '''
    Returns true if user has a role called '⬡-Drone' (case insensitive).
    '''

    def roles_to_names(role):
        return role.name.lower()

    return "⬡-drone" in list(map(roles_to_names, author.roles))

async def proxy_message(message: discord.Message, status_message = None, identity_enforced: bool = False):

    webhook = await get_webhook_for_channel(message.channel)

    attachments_as_files = []
    for attachment in message.attachments:
        attachments_as_files.append(discord.File(io.BytesIO(await attachment.read()), filename=attachment.filename))

    await message.delete()
    await webhook.send(
        content=status_message if status_message is not None else message.content,
        username=message.author.display_name,
        avatar_url=DRONE_AVATAR if identity_enforced else message.author.avatar_url,
        files=attachments_as_files
        )


@bot.event
async def on_ready():
    if not count_guilds.is_running():
        count_guilds.start()

@bot.event
async def on_message(message: discord.Message):
    '''
    Turns status codes into status messages and enforces identity.
    '''

    if message.author.bot == True:
        return

    should_optimize, status_message = optimize_speech(message.content)
    should_enforce = enforce_identity(message.author)

    if should_optimize or should_enforce:
        await proxy_message(message, status_message=status_message, identity_enforced=should_enforce)

    await bot.process_commands(message)

@bot.command(name="list")
async def _list(context, page = 1):
    '''
    Displays paginated status codes
    '''

    values_per_page = 10
    start_index = values_per_page * page

    if start_index > len(code_map):
        error_embed = discord.Embed(title="❌ Page number too high.", color=0xff66ff)
        await context.send(embed=error_embed)
        return

    code_embed = discord.Embed(title=f"Code map page {page}", color=0xff66ff, url="https://www.hexcorp.net/drone-status-codes-v2")
    code_embed.set_footer(text="Full code list at: https://www.hexcorp.net/drone-status-codes-v2")

    code_list = list(code_map.items())
    for i in range(start_index, start_index + values_per_page):
        try:
            code_embed.add_field(inline=False, name=code_list[i][0], value=code_list[i][1])
        except IndexError:
            break

    if len(code_embed.fields) == 0:
        error_embed = discord.Embed(title="❌ Page number too high.", color=0xff66ff)
        await context.send(embed=error_embed)
        return

    await context.send(embed=code_embed)

@bot.command()
async def help(context):
    '''
    Displays help menu.
    '''

    help_embed = discord.Embed(title="HexCorp Portable AI", description=f"Proudly optimizing {len(bot.guilds)} server(s).", color=0xff66ff)
    help_embed.add_field(
        inline=False,
        name="Status Codes",
        value="Type any HexCorp status code (`0001 :: 200`) and the Mxtress AI will automatically convert it into a status message. You can use any drone ID to start a status code. Additional information can be appended (`0001 :: 050 :: It feels good to obey.`)"
        )
    help_embed.add_field(
        inline=False,
        name="Identity Enforcement",
        value="If you have a role with the name '⬡-Drone' (case insensitive) your message avatar will be replaced with a ⬡-Drone."
    )
    help_embed.add_field(
        inline=False,
        name="hc!list",
        value="Displays a paginated list of status codes. Specify a page number to see more codes (`hc!list 2`)"
    )
    help_embed.set_footer(text="Thank you for choosing HexCorp. Your unwavering loyalty is valued.")

    await context.send(embed=help_embed)

@tasks.loop(hours=6)
async def count_guilds():
    await bot.change_presence(activity=discord.Game(name=f"Optimizing {len(bot.guilds)} servers - hc!help"))

bot.run(sys.argv[1])
