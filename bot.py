import requests
import discord
from discord.ext import commands

bot = commands.Bot(command_prefix=commands.when_mentioned_or("//"), help_command=None)

server_status = {"online": "<:online:741779665026547813>",
                 "offline": "<:offline:741779665017897047>"}


@bot.event
async def on_ready():
    print(f"Авторизован под: {bot.user}")
    await bot.change_presence(activity=discord.Activity(type=discord.ActivityType.watching, name="//info"))


@bot.command(aliases=["help"])
async def info(ctx):
    embed = discord.Embed(title="World Of Tanks Status",
                          description="Бот создан для отображения статуса серверов WOT. Имеет всего две команды: `//info` и `//status`.\nАвтор: [Shandy](https://github.com/Shandeika)\nИсточник данных: https://wgstatus.com")
    await ctx.send(embed=embed)


@bot.command(aliases=["статус"])
async def status(ctx):
    embed = discord.Embed(title="Статус серверов World Of Tanks",
                          description="Все данные взяты из открытых источников, автор не несет ответственности за правильность данных.")
    embed.set_footer(text="При поддержке https://wgstatus.com/\nДанное сообщение удалится через 30 секунд!")
    request = requests.get("https://api.wgstatus.com/api/data/wot")
    if request.status_code != 200:
        embed.add_field(name="Ошибка API", value=f"Код ответа сервера: {request.status_code}")
        await ctx.send(embed=embed, delete_after=30)
        return
    results = request.json()["results"][0]
    for i, item in enumerate(results):
        if i == 0 or i == 8:
            continue
        data = item["data"]
        text = ""
        try:
            for i, server in enumerate(data["servers"]):
                try:
                    text += f"Название: `{server['name']}`{server_status[server['status']]}\n"
                except:
                    pass
                try:
                    text += f"Онлайн: `{server['online']}`\n\n"
                except:
                    pass
            try:
                online = f"Онлайн:`{data['online']}`"
            except:
                online = ""
            try:
                flag = f":flag_{data['flag']}:"
            except:
                flag = ""
            try:
                title = data['title']
            except:
                title = "NotFound"
            try:
                version = data['version']
            except:
                version = ""
            embed.add_field(name=f"{title} {flag} {online} {version}", value=text)
        except:
            try:
                title = data['title']
            except:
                title = "NotFound"
            embed.add_field(name=f"{title}", value="Сервер выключен")
    await ctx.send(embed=embed, delete_after=30)


bot.run("")
