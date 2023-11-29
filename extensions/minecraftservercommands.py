import asyncio

import discord
from discord.ext import commands
import os
import boto3
from mcstatus import JavaServer

server_management_channel_id = 1119297287831691275


# Helper Functions
def in_channel(channel_id):
    async def predicate(ctx):
        return ctx.channel.id == channel_id

    return commands.check(predicate)


def handle_wrong_channel_error(ctx, error):
    if isinstance(error, discord.errors.CheckFailure):
        return ctx.respond(
            embed=discord.Embed(
                title='Wrong channel',
                description=f"You can only use this command in <#{server_management_channel_id}>.",
                color=0xFF3838),
            ephemeral=True)
    else:
        return ctx.respond(
            embed=discord.Embed(
                title='Error',
                description=f"An error has occurred:\n{type(error)}\n{error}",
                color=0xFF3838),
            ephemeral=True)


# Main Cog
class MinecraftServerCommands(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.instance_ID = os.getenv('MINECRAFT_EC2_INSTANCE_ID')
        self.server_ip = os.getenv('MINECRAFT_EC2_INSTANCE_IP')
        self.ec2_client = boto3.client(
            'ec2',
            aws_access_key_id=os.getenv('AWS_ACCESS_KEY_ID'),
            aws_secret_access_key=os.getenv('AWS_SECRET_ACCESS_KEY'),
            region_name=os.getenv('AWS_REGION'))

    @commands.slash_command(name="start_minecraft_server",
                            description="Starts the Minecraft server")
    @in_channel(server_management_channel_id)
    async def start_minecraft_server(self, ctx):
        response = self.ec2_client.start_instances(InstanceIds=[self.instance_ID])
        embed = discord.Embed(title="Server Status")
        if response['StartingInstances'][0]['CurrentState']['Name'] == 'pending':
            embed.description = 'Server is starting.'
            message = await ctx.respond(embed=embed)
            state = self.ec2_client.describe_instances(InstanceIds=[self.instance_ID])['Reservations'][0]['Instances'][0]['State']['Name']
            while state == 'pending':
                await asyncio.sleep(5)
                state = self.ec2_client.describe_instances(InstanceIds=[self.instance_ID])['Reservations'][0]['Instances'][0]['State']['Name']
            if state == 'running':
                embed.description = 'Server started.'
                embed.color = discord.Color.green()
            else:
                embed.description = 'Server failed to start.'
                embed.color = discord.Color.red()
            await message.edit_original_response(embed=embed)
        elif response['StartingInstances'][0]['CurrentState']['Name'] == 'running':
            await ctx.respond('Server is already running.')
        else:
            await ctx.respond('Failed to start Server.')

    @commands.slash_command(name="stop_minecraft_server",
                            description="Stops the Minecraft server")
    @in_channel(server_management_channel_id)
    async def stop_minecraft_server(self, ctx):
        response = self.ec2_client.stop_instances(InstanceIds=[self.instance_ID])
        if response['StoppingInstances'][0]['CurrentState']['Name'] == 'stopping':
            await ctx.respond('Server Stopping...')
        elif response['StoppingInstances'][0]['CurrentState']['Name'] == 'stopped':
            await ctx.respond('Server is already stopped.')
        else:
            await ctx.respond('Failed to stop Server.')

    @commands.slash_command(name="server_status",
                            description="Checks the status of the Minecraft server")
    async def minecraft_server_status(self, ctx):
        embed = discord.Embed(title="Server Status")
        response = self.ec2_client.describe_instances(InstanceIds=[self.instance_ID])
        if response['Reservations'][0]['Instances'][0]['State']['Name'] == 'running':
            embed.description = 'Server is running.\n'

            try:
                server = await JavaServer.async_lookup(f"{self.server_ip}:8008")
                embed.color = discord.Color.green()
                if server.status().players.online == 0:
                    embed.description += "There are no players online."
                elif server.status().players.online == 1:
                    embed.description += f"{server.status().players.sample[0].name} is alone on the server."
                else:
                    embed.description += f"There is {server.status().players.online} player online."
                    embed.add_field(name="Online Players:",
                                    value='\n'.join([x.name for x in server.status().players.sample]),
                                    inline=False)
                await ctx.respond(embed=embed)
            except Exception as e:
                embed.description += f'Failed to fetch player list with error:\n{e}'
                embed.color = discord.Color.yellow()
                await ctx.respond(embed=embed)
                # await ctx.respond(f'Server is running. Failed to fetch player list with error:\n{e}')
        elif response['Reservations'][0]['Instances'][0]['State']['Name'] == 'stopped':
            embed.description = 'Server is off.'
            embed.color = discord.Color.darker_gray()
            await ctx.respond(embed=embed)
        elif response['Reservations'][0]['Instances'][0]['State']['Name'] == 'stopping':
            embed.description = 'Server is shutting down...'
            embed.color = discord.Color.dark_gray()
            await ctx.respond(embed=embed)
        elif response['Reservations'][0]['Instances'][0]['State']['Name'] == 'pending':
            embed.description = 'Server is starting...'
            embed.color = discord.Color.blue()
            await ctx.respond(embed=embed)
        else:
            embed.description = 'Server is in an unknown state.'
            embed.color = discord.Color.red()
            await ctx.respond(embed=embed)

    @commands.slash_command(name="get_server_ip",
                            description="Gets the IP address of the Minecraft server")
    async def get_server_ip(self, ctx):
        await ctx.respond(f'The Minecraft server IP address is {self.server_ip}', ephemeral=True)

    @commands.slash_command(name="ping_minecraft_server", description="Pings the Minecraft server")
    async def ping_minecraft_server(self, ctx):
        pass

    @start_minecraft_server.error
    async def start_minecraft_server_error(self, ctx, error):
        await handle_wrong_channel_error(ctx, error)
        return

    @stop_minecraft_server.error
    async def stop_minecraft_server_error(self, ctx, error):
        await handle_wrong_channel_error(ctx, error)
        return


def setup(bot):
    bot.add_cog(MinecraftServerCommands(bot))
