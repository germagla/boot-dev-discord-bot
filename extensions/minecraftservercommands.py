from discord import Embed
from discord.ext import commands
import os
import boto3
from mcstatus import JavaServer


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
    async def start_minecraft_server(self, ctx):
        response = self.ec2_client.start_instances(InstanceIds=[self.instance_ID])
        if response['StartingInstances'][0]['CurrentState']['Name'] == 'pending':
            await ctx.respond('Server Starting...')
        elif response['StartingInstances'][0]['CurrentState']['Name'] == 'running':
            await ctx.respond('Server is already running.')
        else:
            await ctx.respond('Failed to start Server.')

    @commands.slash_command(name="stop_minecraft_server",
                            description="Stops the Minecraft server")
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
        response = self.ec2_client.describe_instances(InstanceIds=[self.instance_ID])
        if response['Reservations'][0]['Instances'][0]['State']['Name'] == 'running':
            embed = Embed(title="Server Status",
                          description=f"Server is running. ",
                          color=0x00ff00)

            try:
                server = await JavaServer.async_lookup(self.server_ip)
                embed.description += f"There are {server.status().players.online} players online."
                embed.add_field(name="Online Players",
                                value='\n'.join([x.name for x in server.status().players.sample]),
                                inline=False)
                await ctx.respond(embed=embed)
            except Exception as e:
                embed.description += f'Failed to fetch player list with error:\n{e}'
                await ctx.respond(embed=embed)
                # await ctx.respond(f'Server is running. Failed to fetch player list with error:\n{e}')
        elif response['Reservations'][0]['Instances'][0]['State']['Name'] == 'stopped':
            await ctx.respond('Server is stopped.')
        elif response['Reservations'][0]['Instances'][0]['State']['Name'] == 'stopping':
            await ctx.respond('Server is stopping.')
        elif response['Reservations'][0]['Instances'][0]['State']['Name'] == 'pending':
            await ctx.respond('Server is starting.')
        else:
            await ctx.respond('Server is in an unknown state.')

    @commands.slash_command(name="get_server_ip",
                            description="Gets the IP address of the Minecraft server")
    async def get_server_ip(self, ctx):
        await ctx.respond(f'The Minecraft server IP address is {self.server_ip}', ephemeral=True)

    @commands.slash_command(name="ping_minecraft_server", description="Pings the Minecraft server")
    async def ping_minecraft_server(self, ctx):
        pass


def setup(bot):
    bot.add_cog(MinecraftServerCommands(bot))
