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
    CHANNEL_ID = data['ID']['CHANNEL']
    SITE = data['SITE']
    DB = data['DB']

roles = [x.lower() for x in list(ROLE_ID.keys())]
cooldown = {}
cooldown_time = 30

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

    def on_cooldown(self, message):
        try:
            last_time = cooldown[message.author.id]
        except KeyError:
            cooldown[message.author.id] = datetime.now()
            return False
        last_time_since = (datetime.now() - last_time).total_seconds()
        if last_time_since <= cooldown_time:
            return int(last_time_since)
        cooldown[message.author.id] = datetime.now()
        return False

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
        if teamtag:
            await member.edit(nick="[{}] {}".format(teamtag, username))            
        else:
            await member.edit(nick="{}".format(username))
        db.close()
        if ret:
            return added_roles

    async def on_message(self, message):
        if message.author.bot:
            # Ignore own messages
            return
        if message.content.startswith("!roles"):
            cd = self.on_cooldown(message)
            if not cd:
                old_roles = [x.name for x in message.author.roles[1:]]
                new_roles = await self.on_member_join(message.author, True)
                if isinstance(new_roles, list):
                    if set(old_roles) != set(new_roles):
                        new = ["+" + x for x in list(set(new_roles) - set(old_roles))]
                        old = ["-" + x for x in list(set(old_roles) - set(new_roles))]
                        resp = discord.Embed(
                            title="Roles Updated Successfully",
                            description="Roles were updated for {}\n{}\n{}".format(message.author.name, "\n".join(new), "\n".join(old)),
                            color=0x00ff00
                        )
                    else:
                        resp = discord.Embed(
                            title="No Roles Update",
                            description="There are no new roles for {}.\nIf this is an error, contact Rizen".format(message.author.name),
                            color=0x00ff00
                        )
                else:
                    resp = discord.Embed(
                        title="Roles Update Failure",
                        description="There is no website user associated with this user.\nIf this is an error, contact Rizen",
                        color=0xff0000
                    )
            else:
                resp = discord.Embed(
                    title="Command Cooldown",
                    description="You must wait for {} seconds before trying again!".format(cd),
                    color=0xff0000
                )
            temp = await message.channel.send(embed=resp, delete_after=5)

client = Client()
client.run(TOKEN['DISCORD'])