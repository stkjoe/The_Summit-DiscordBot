import discord
from discord.ext import commands
from discord.utils import get
import MySQLdb
from datetime import datetime, timedelta
import os
import requests
import json

# If true, will read the an alternative text file for tokens
debug=False

filename = 'settings.txt'
if debug:
    filename = 'dev.txt'

with open(filename) as json_file:
    data = json.load(json_file)
    TOKENS = data['TOKEN']
    RDS = data['RDS']
    IDS = data['ID']
    SITE = data['SITE']

class Client(discord.Client):
    channel_cooldowns = {}
    COOLDOWN = 30

    def on_cooldown(message, command):
        try:
            last_time = channel_cooldown[message.channel.id][command]
        except KeyError:
            channel_cooldown[message.channel.id][command] = datetime.now() - datetime.timedelta(seconds=COOLDOWN * 2)
            return False
        last_time_since = datetime.now() - last_time
        if last_time_since <= COOLDOWN:
            channel_cooldown[message.channel.id][command] = datetime.now()
            return last_time_since
        return False

    def build_embed(title="", description="", color=0xffffff, thumbnail=""):
        embed = discord.Embed(
            title=title,
            description=description,
            color=color
        )
        if thumbnail:
            embed.set_thumbnail(url=thumbnail)
        return embed

    async def send_embed(message, content, command):
        seconds = on_cooldown(message, command)
        if seconds:
            resp = discord.Embed(
                title="Command is on cooldown!",
                description="{} seconds remain".format(seconds),
                color=0xff0000
            )
            await message.channel.send(embed=resp)
        else:
            await message.channel.send(embed=content)

    async def add_role(message, role_id, desc):
        role = get(message.guild.roles, id=role_id)
        await message.author.add_roles(role)
        return desc

    async def on_message(message):
        if message.author.bot:
            # Ignore own messages
            return
        if message.channel.id == base_camp_id:
            # Reads the base_camp channel for codes
            if message.startswith("sumt"):
                conn = MySQLdb.connect(
                    host=RDS['DEFAULT']['RDS_HOSTNAME'],
                    port=int(RDS['DEFAULT']['RDS_PORT']),
                    user=RDS['DEFAULT']['RDS_USERNAME'],
                    passwd=RDS['DEFAULT']['RDS_PASSWORD'],
                    db=RDS['DEFAULT']['RDS_DB_NAME'],
                )
                if conn.is_connected():
                    cursor = conn.cursor()
                    query = ("SELECT participant, captain FROM role_Table WHERE code=%s")
                    cursor.execute(query, message.content)
                    result = cursor.fetchone()
                    if result:
                        roles = []
                        participant = bool(result[0])
                        captain = bool(result[1])
                        if captain:
                            roles.append(add_role(message, ID['ROLE']['CAPTAIN'], "Captain"))
                        if participant:
                            roles.append(add_role(message, ID['ROLE']['PARTICIPANT'], "Participant"))
                        resp = discord.Embed(
                            title="Success",
                            description="The following roles have been added:\n\n{}".format("\n".join(roles)),
                            color=0x80ff00
                            )
                    else:
                        resp = discord.Embed(
                            title="Failure",
                            description="Please make sure you are entering the code correctly.",
                            color=0xff0000
                            )
                    cursor.close()
                    conn.close()
                else:
                    resp = discord.Embed(title="Failure", description="Please make sure you are entering the code correctly.", color=0xff0000)
            await message.channel.delete()
            temp = await message.channel.send(embed=resp)
            await temp.channel.delete(delay=8)
            
        else:
            text_message = message.content.lower()
            if message.content.startswith("!"):
                if text_message.startswith("!help"):
                    resp = build_embed(
                        title="Help",
                        description="\n".join(
                            [
                                "**General**",
                                "``!twitch``: Displays the contest Twitch link",
                                "``!youtube``: Displays the contest YouTube link",
                                "``!site`` / ``!website``: Displays the contest Website link",
                                "``!live``: Check if the contest Twitch stream is live"
                            ]
                        ),
                        color=0xffffff,
                    )
                    send_embed(message, resp, "help")
                elif text_message.startswith("!twitch"):
                    resp = build_embed(
                        title="Twitch Channel",
                        description=SITE['TWITCH'],
                        color=0x6441a5,
                        thumbnail="https://i.imgur.com/7QEx1ny.png" #TODO: change image
                    )
                    send_embed(message, resp, "twitch")
                elif text_message.startswith("!youtube"):
                    resp = build_embed(
                        title="YouTube Channel",
                        description=SITE['YOUTUBE'], #TODO: add youtube domain
                        color=0xc4302b,
                        thumbnail="https://i.imgur.com/eyLvJEo.png"
                    )
                    send_embed(message, resp, "youtube")
                elif text_message.startswith("!site") or text_message.startswith("!website"):
                    resp = build_embed(
                        title="The Summit Website",
                        description=SITE['WEBSITE'],
                        thumbnail="" #TODO: change image to official one
                    )
                    send_embed(message, resp, "site")
                elif text_message.startswith("!live"):
                    twitch_html = requests.get("https://api.twitch.tv/kraken/streams/The_Summit_ORG?client_id={}".format(twitch_token))
                    twitch = json.loads(twitch_html.content)
                    if twitch["stream"] is not None:
                        resp = build_embed(
                            title="The Summit ORG is LIVE",
                            description="https://www.twitch.tv/The_Summit_ORG",
                            color=0x6441a5,
                            thumbnail="https://i.imgur.com/7QEx1ny.png"
                        )
                    else:
                        resp = build_embed(
                            title="The Summit ORG is NOT Live"
                        )
                    send_embed(message, resp, "live")

client = Client()
client.run(discord_token)
