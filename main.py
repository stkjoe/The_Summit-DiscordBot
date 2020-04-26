import discord
from discord.utils import get
import MySQLdb
from datetime import datetime, timedelta
import os
import requests
import json

with open('secret.txt') as json_file:
    data = json.load(json_file)
    TOKEN = data['TOKEN']
    ROLE_ID = data['ID']['ROLE']
    SITE = data['SITE']
    DB = data['DB']

roles = [x.lower() for x in list(ROLE_ID.keys())]
channel_cooldown = {}
COOLDOWN = 30

class Client(discord.Client):

    async def on_ready(self):
        db = self.get_db()
        cur = db.cursor()
        cur.execute("""CREATE TABLE IF NOT EXISTS teams (
            team_name VARCHAR(30) NOT NULL,
            team_tag VARCHAR(3) PRIMARY KEY,
            eliminated BOOLEAN DEFAULT false)"""
        )
        cur.execute("""CREATE TABLE IF NOT EXISTS users (
            discord_id BIGINT DEFAULT -1,
            osu_id INT PRIMARY KEY,
            team_tag VARCHAR(3) DEFAULT NULL,
            participant BOOLEAN DEFAULT false,
            captain BOOLEAN DEFAULT false,
            song_selector BOOLEAN DEFAULT false,
            commentator BOOLEAN DEFAULT false,
            judge BOOLEAN DEFAULT false,
            chat_moderator BOOLEAN DEFAULT false,
            website_maintainer BOOLEAN DEFAULT false,
            graphics_designer BOOLEAN DEFAULT false,
            staff BOOLEAN DEFAULT false,
            organiser BOOLEAN DEFAULT false,
            FOREIGN KEY (team_tag) REFERENCES teams(team_tag))"""
        )
        db.close()

    def get_db(self):
        db = MySQLdb.connect(
            host=DB['HOST'],
            user=DB['USER_NAME'],
            passwd=DB['PASSWORD'],
            db=DB['DATABASE']
        )
        return db

    def on_cooldown(self, message, command):
        try:
            last_time = channel_cooldown[message.channel.id][command]
        except KeyError:
            try:
                channel_cooldown[message.channel.id][command] = datetime.now()
            except KeyError:
                channel_cooldown[message.channel.id] = {}
                channel_cooldown[message.channel.id][command] = datetime.now()
            return False
        last_time_since = (datetime.now() - last_time).total_seconds()
        if last_time_since <= COOLDOWN:
            channel_cooldown[message.channel.id][command] = datetime.now()
            return last_time_since
        return False

    def build_embed(self, title="", description="", color=0xffffff, thumbnail=""):
        embed = discord.Embed(
            title=title,
            description=description,
            color=color
        )
        if thumbnail:
            embed.set_thumbnail(url=thumbnail)
        return embed

    async def send_embed(self, message, content, command):
        seconds = self.on_cooldown(message, command)
        if seconds:
            resp = discord.Embed(
                title="Command is on cooldown!",
                description="{} seconds remain".format(int(30 - seconds)),
                color=0xff0000
            )
            temp = await message.channel.send(embed=resp, delete_after=3)
        else:
            await message.channel.send(embed=content)

    async def add_role(self, member, role_id):
        role = get(member.guild.roles, id=role_id)
        await member.add_roles(role)
        return role.name

    async def on_member_join(self, member, ret=False):
        if member.bot:
            return
        added_roles = []
        db = self.get_db()
        cur = db.cursor(MySQLdb.cursors.DictCursor)
        if not cur.execute("SELECT * FROM users WHERE discord_id={}".format(member.id)):
            db.close()
            return
        user_roles = cur.fetchone()
        for role in member.roles[1:]:
            await member.remove_roles(role)
        for role in roles:
            if user_roles[role]:
                added_roles.append(await self.add_role(member, ROLE_ID[role.upper()]))
        userid = user_roles['osu_id']
        teamtag = user_roles['team_tag']
        response = requests.get("https://osu.ppy.sh/api/get_user?k={}&u={}".format(TOKEN['OSU'], userid))
        if response.status_code != 200:
            db.close()
            return
        username = json.loads(response.content)[0]["username"]
        await member.edit(nick="[{}] {}".format(teamtag, username))
        db.close()
        if ret:
            return added_roles

    async def on_message(self, message):
        if message.author.bot:
            # Ignore own messages
            return
        if message.content.startswith("!"):
            text_message = message.content.lower()
            if text_message.startswith("!help"):
                resp = self.build_embed(
                    title="Help",
                    description="\n".join(
                        [
                            "**General**",
                            "``!live``: Check if the contest Twitch stream is live",
                            "``!site`` / ``!website``: Displays the contest Website link",
                            "``!twitch``: Displays the contest Twitch link",
                            "``!youtube``: Displays the contest YouTube link",
                            "``!twitter``: Displays the contest Twitter link"
                        ]
                    ),
                    color=0xffffff,
                )
                await self.send_embed(message, resp, "help")
            elif text_message.startswith("!live"):
                twitch_html = requests.get("https://api.twitch.tv/kraken/streams/{}?client_id={}".format(SITE['TWITCH'].split("twitch.tv/")[1], TOKEN['TWITCH']))
                twitch = json.loads(twitch_html.content)
                try:
                    twitch["stream"]
                    resp = self.build_embed(
                        title="The Summit ORG is LIVE",
                        description=SITE['TWITCH'],
                        color=0x6441a5,
                        thumbnail="https://i.imgur.com/7QEx1ny.png"
                    )
                except KeyError:
                    resp = self.build_embed(
                        title="The Summit ORG is NOT Live"
                    )
                await self.send_embed(message, resp, "live")
            elif text_message.startswith("!site") or text_message.startswith("!website"):
                resp = self.build_embed(
                    title="The Summit Website",
                    description=SITE['WEBSITE'],
                    thumbnail="https://i.imgur.com/EagchHm.jpg"
                )
                await self.send_embed(message, resp, "site")
            elif text_message.startswith("!twitch"):
                resp = self.build_embed(
                    title="Twitch Channel",
                    description=SITE['TWITCH'],
                    color=0x6441a5,
                    thumbnail="https://i.imgur.com/7QEx1ny.png"
                )
                await self.send_embed(message, resp, "twitch")
            elif text_message.startswith("!youtube"):
                resp = self.build_embed(
                    title="YouTube Channel",
                    description=SITE['YOUTUBE'],
                    color=0xc4302b,
                    thumbnail="https://i.imgur.com/eyLvJEo.png"
                )
                await self.send_embed(message, resp, "youtube")
            elif text_message.startswith("!twitter"):
                resp = self.build_embed(
                    title="Twitter Profile",
                    description=SITE['TWITTER'],
                    color=0x00aced,
                    thumbnail="https://i.imgur.com/EvWLVOF.png"
                )
                await self.send_embed(message, resp, "twitter")
            elif text_message.startswith("!roles"):
                if get(message.guild.roles, id=ROLE_ID['STAFF']) in message.author.roles:
                    if len(message.mentions) == 1:
                        old_roles = [x.name for x in message.mentions[0].roles[1:]]
                        new_roles = await self.on_member_join(message.mentions[0], True)
                        if isinstance(new_roles, list):
                            if set(old_roles) != set(new_roles):
                                resp = self.build_embed(
                                    title="Roles Updated Successfully",
                                    description="Roles were updated for {}\n\n**Old Roles**\n{}\n**New Roles**\n{}".format(message.mentions[0].name, "\n".join(old_roles), "\n".join(new_roles)),
                                    color=0x00ff00
                                )
                            else:
                                resp = self.build_embed(
                                    title="No Roles Update",
                                    description="There are no new roles for {}.\nIf this is an error, contact Rizen".format(message.mentions[0].name),
                                    color=0x00ff00
                                )
                        else:
                            resp = self.build_embed(
                                title="Roles Update Failure",
                                description="There is no website user associated with this user.\nIf this is an error, contact Rizen",
                                color=0xff0000
                            )
                    elif len(message.mentions) > 1:
                        resp = self.build_embed(
                            title="Roles Update Failure",
                            description="You may only include one mention in the message.\nUsage: ``!roles @user``",
                            color=0xff0000
                        )
                    elif len(message.mentions) == 0:
                        resp = self.build_embed(
                            title="Roles Update Failure",
                            description="You must include one mention in the message.\nUsage: ``!roles @user``",
                            color=0xff0000
                        )
                    await message.channel.send(embed=resp)


client = Client()
client.run(TOKEN['DISCORD'])