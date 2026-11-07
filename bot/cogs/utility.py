import discord
from discord.ext import commands

class Utility(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.command(name='serverinfo')
    async def serverinfo(self, ctx):
        await ctx.send(f"Server Name: {ctx.guild.name}, Total Members: {ctx.guild.member_count}")

async def setup(bot):
    await bot.add_cog(Utility(bot))