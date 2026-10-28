import discord
from discord.ext import commands
import random
import threading
import json
import os
from flask import Flask
from collections import Counter

app = Flask(__name__)
SAVE_FILE = "save.json"
players = {}
dev_mode_users = set()
DEV_IDS = [1200298327531585537]

def load_save():
    global players, dev_mode_users
    if os.path.exists(SAVE_FILE):
        try:
            with open(SAVE_FILE, "r", encoding="utf-8") as f:
                data = json.load(f)
                for uid, pdata in data.get("players", {}).items():
                    pdata["met_npcs"] = set(pdata.get("met_npcs", ["千户","尤莉"]))
                    pdata["npc_met_km"] = pdata.get("npc_met_km", {"千户":0,"尤莉":0})
                    players[int(uid)] = pdata
                dev_mode_users = set(data.get("dev_mode_users", []))
        except Exception as e:
            print(f"[SAVE] 加载失败: {e}")

def save_now():
    try:
        save_data = {
            "players": {uid: {**pdata, "met_npcs": list(pdata["met_npcs"])} for uid, pdata in players.items()},
            "dev_mode_users": list(dev_mode_users)
        }
        with open(SAVE_FILE, "w", encoding="utf-8") as f:
            json.dump(save_data, f, ensure_ascii=False, indent=2)
    except Exception as e:
        print(f"[SAVE] 保存失败: {e}")

load_save()

def format_backpack(inventory):
    counter = Counter(inventory)
    seen = []
    for i in inventory:
        if i not in seen:
            seen.append(i)
    lines = []
    for name in seen:
        c = counter[name]
        if c > 1:
            lines.append(f"{name} x{c}")
        else:
            lines.append(name)
    return lines, counter

def get_unique_for_trade(inventory):
    seen = []
    for i in inventory:
        if i not in seen:
            seen.append(i)
    return seen

@app.route("/")
def index():
    total = sum(p['km'] for p in players.values())
    return f"Kettenkrad v17.5 | {len(players)}人 {total}km"

def run_flask():
    port = int(os.environ.get("PORT", 10000))
    app.run(host="0.0.0.0", port=port)

intents = discord.Intents.default()
bot = commands.Bot(command_prefix="/", intents=intents)

SPECIAL_REWARDS = {
    "尤莉的笑脸": {"text": "尤莉：嘿嘿~ 千户你看我笑得可爱吗？\n千户：...笨蛋。", "image": "https://cdn.discordapp.com/attachments/1519326691095478272/1564967112982663238/44b80e01a3f2b3cb9d0bb35479393411.jpg?ex=6ae330b3&is=6ae1df33&hm=f0847625bf118e334badacf391241518b4bbcc611c24ba28d41bc2febedd04f2&", "color": 0xf2c17c, "effect": "food+1"},
    "尤莉的歌声": {"text": "尤莉：♪~ 拉拉拉~ 终末世界也要唱歌！", "image": None, "color": 0xf2c17c, "effect": "fuel+2"},
    "尤莉的拥抱": {"text": "尤莉：千户，好冷啊，抱一下！\n千户：等等、太近了！", "image": "https://cdn.discordapp.com/attachments/1519326691095478272/1564966003581128754/50.jpg?ex=6ae32faa&is=6ae1de2a&hm=fb7591952c82a057ddf76abf5f6848c4eb919b39a6c4d2ee62e52eacf38729d8&", "color": 0xf2c17c, "effect": "food+3"},
    "日记(千户写的)": {"text": "千户的日记：今天尤莉又把枪弄丢了...", "image": None, "color": 0x8b9a7d, "effect": "none"},
    "金泽的眼镜": {"text": "金泽：没有这个我看不清地图了...算了，送你吧。", "image": None, "color": 0x87ceeb, "effect": "none"},
    "石像爷爷的刻刀": {"text": "石像爷爷：用这个刻，能刻得更久。", "image": None, "color": 0xa9a9a9, "effect": "none"},
    "管制官的密钥": {"text": "管制官：密钥已移交...工厂将永远运行。", "image": None, "color": 0xff4444, "effect": "fuel+50"},
    "发光的努可": {"text": "努可把子弹吃掉了，全身发光...\n效果：燃料充满", "image": None, "color": 0xffffff, "effect": "fuel_full"},
    "电能 x100": {"text": "努可：努可！ (释放100电能)", "image": None, "color": 0xffffff, "effect": "fuel+100"},
    "星空的照片": {"text": "……嗯。\n\n千户：...好美。\n—— 终末的星空", "image": "https://cdn.discordapp.com/attachments/1519326691095478272/1564967131077152878/IMG-20261028-WA8675.jpg?ex=6ae330b7&is=6ae1df37&hm=8553fc19adecb9faf90bf90e5eb82dd40857b36c06b75a47853e4ab9210ad731&", "color": 0x000000, "effect": "END"},
    "END标记": {"text": "上面什么都没有了。\n但旅途本身，就是意义。\n—— 少女终末旅行 完", "image": "https://cdn.discordapp.com/attachments/1519326691095478272/1564967119534432256/images_32.jpg?ex=6ae330b4&is=6ae1df34&hm=3568f2eb3183a449c878197dd0c48b29a5cecd1b1a677c2ae390f19078c38b85&", "color": 0x000000, "effect": "END"},
    "小地藏雕像": {"text": "石像爷爷：保佑你们的旅途。", "image": None, "color": 0xa9a9a9, "effect": "none"},
    "飞机设计图": {"text": "石井：这架飞机本来想去上层的", "image": None, "color": 0xdeb887, "effect": "none"},
    "世界地图(残缺)": {"text": "金泽：这地图我画了半辈子", "image": None, "color": 0x87ceeb, "effect": "none"},
}

ALL_NPCS = {
    "金泽": {"color": 0x87ceeb, "km_need": 50},
    "石像爷爷": {"color": 0xa9a9a9, "km_need": 150},
    "石井": {"color": 0xdeb887, "km_need": 300},
    "管制官": {"color": 0xff4444, "km_need": 500},
    "努可": {"color": 0xffffff, "km_need": 700},
    "尤莉": {"color": 0xf2c17c, "km_need": 0},
    "千户": {"color": 0x8b9a7d, "km_need": 0},
    "上层的幽灵": {"color": 0x000000, "km_need": 1000},
}

DROP_TABLE = {
    "尤莉": [("尤莉的笑脸", 5), ("尤莉的歌声", 15), ("尤莉的拥抱", 10), ("空弹壳", 70)],
    "千户": [("日记(千户写的)", 30), ("修理工具", 20), ("旧式相机胶卷", 50)],
    "金泽": [("世界地图(残缺)", 20), ("手绘地图碎片", 50), ("金泽的眼镜", 30)],
    "石像爷爷": [("小地藏雕像", 40), ("石像 x10", 30), ("石像爷爷的刻刀", 30)],
    "石井": [("飞机设计图", 15), ("土豆干", 50), ("螺旋桨碎片", 35)],
    "管制官": [("燃料桶 x20", 40), ("军用口粮 x10", 40), ("管制官的密钥", 20)],
    "努可": [("发光的努可", 20), ("电能 x100", 50), ("被吃掉的子弹", 30)],
    "上层的幽灵": [("星空的照片", 50), ("END标记", 50)],
}

RANDOM_LOOT = [
    ("生锈的螺栓", 15, "垃圾"), ("空罐头", 15, "垃圾"), ("旧报纸", 10, "垃圾"),
    ("破布", 8, "垃圾"), 
    ("燃料桶(半满)", 18, "燃料+5"), ("燃料桶 x20", 9, "燃料+20"),
    ("压缩口粮 x1", 14, "食物+1"), ("土豆干 x2", 13, "食物+2"),
    ("尤莉的笑脸", 1, "稀有"), ("小地藏雕像", 2, "稀有"),
    ("发光的石头", 2, "垃圾"), ("38式步枪子弹 x5", 7, "垃圾"),
]

ALL_ITEMS_POOL = [
    "压缩口粮 x10", "压缩口粮 x1", "土豆干", "土豆干 x2", "军用口粮 x10", "燃料桶 x20", "燃料桶(半满)",
    "生锈的螺栓", "空罐头", "旧报纸", "破布", "发光的石头", "38式步枪子弹 x5", "空弹壳", "被吃掉的子弹",
    "手绘地图碎片", "世界地图(残缺)", "金泽的眼镜", "小地藏雕像", "石像 x10", "石像爷爷的刻刀",
    "飞机设计图", "螺旋桨碎片", "管制官的密钥", "日记(千户写的)", "修理工具", "旧式相机胶卷",
    "尤莉的笑脸", "尤莉的歌声", "尤莉的拥抱", "发光的努可", "电能 x100", "星空的照片", "END标记"
]

def roll(npc):
    table = DROP_TABLE.get(npc, [("垃圾", 100)]); r=random.randint(1,100); cur=0
    for item,p in table:
        cur+=p
        if r<=cur: return item
    return table[-1][0]

def get_player(uid):
    if uid not in players:
        players[uid] = {
            "km":0,"food":2,"fuel":8,"step":0,"visited_airplane":False,"ended":False,
            "met_npcs":set(["千户","尤莉"]),
            "npc_met_km":{"千户":0,"尤莉":0},
            "inventory":["Kettenkrad履带摩托","38式步枪","手枪与一发子弹","千户的日记","毛毯 x2"]
        }
        save_now()
    if "npc_met_km" not in players[uid]:
        players[uid]["npc_met_km"] = {}
    return players[uid]

class RestartView(discord.ui.View):
    def __init__(self, user_id):
        super().__init__(timeout=None)
        self.user_id = user_id
    @discord.ui.button(label="重新开始", style=discord.ButtonStyle.primary, emoji="🔄")
    async def restart(self, interaction: discord.Interaction, button: discord.ui.Button):
        if interaction.user.id != self.user_id:
            await interaction.response.send_message("❌ 这不是你的终点", ephemeral=True); return
        players[interaction.user.id] = {
            "km": 0, "food": 2, "fuel": 8, "step": 0,
            "visited_airplane": False, "ended": False,
            "met_npcs": set(["千户","尤莉"]),
            "npc_met_km": {"千户":0,"尤莉":0},
            "inventory": ["Kettenkrad履带摩托","38式步枪","手枪与一发子弹","千户的日记","毛毯 x2"]
        }
        save_now()
        await interaction.response.edit_message(embed=discord.Embed(title="🔄 旅途重新开始", description="一切回到了起点。\n0km / 1000km\n背包、进度、图鉴已全部重置。", color=0x8b9a7d), view=None)
    @discord.ui.button(label="留在终点", style=discord.ButtonStyle.secondary, emoji="⭐")
    async def stay(self, interaction: discord.Interaction, button: discord.ui.Button):
        if interaction.user.id != self.user_id: return
        await interaction.response.edit_message(embed=discord.Embed(title="—— 留在星空下", description="……嗯。\n你们选择留在1000km，仰望星空。", color=0x000000), view=self)

class TradeView(discord.ui.View):
    def __init__(self, from_id, to_id=None, npc_name=None, inventory=None):
        super().__init__(timeout=120)
        self.from_id = from_id
        self.to_id = to_id
        self.npc_name = npc_name
        self.offer = None
        inv = inventory or []
        if not inv:
            return
        _, counter = format_backpack(inv)
        unique = get_unique_for_trade(inv)
        opts = []
        for idx, item in enumerate(unique[:25]):
            cnt = counter[item]
            label = f"{item} (x{cnt})" if cnt > 1 else item
            opts.append(discord.SelectOption(label=label[:100], value=f"{idx}|{item}"))
        
        self.select_give = discord.ui.Select(
            placeholder=f"选择物品 - 共{len(inv)}件 {len(unique)}种",
            min_values=1, max_values=1, options=opts
        )
        self.select_give.callback = self.select_callback
        self.add_item(self.select_give)

    async def select_callback(self, interaction: discord.Interaction):
        if interaction.user.id != self.from_id:
            await interaction.response.send_message("❌ 不是你的交易", ephemeral=True)
            return
        raw = self.select_give.values[0]
        _, item_name = raw.split("|", 1)
        self.offer = item_name
        await interaction.response.send_message(f"已选择：**{self.offer}** ，点下方 ✅确认 交易", ephemeral=True)

    @discord.ui.button(label="确认交易", style=discord.ButtonStyle.success, emoji="🤝")
    async def confirm(self, interaction: discord.Interaction, button: discord.ui.Button):
        if interaction.user.id != self.from_id:
            await interaction.response.send_message("❌ 不是你的交易", ephemeral=True)
            return
        if not self.offer:
            await interaction.response.send_message("❌ 请先选择一个物品", ephemeral=True)
            return
        p = get_player(self.from_id)
        if self.offer not in p["inventory"]:
            await interaction.response.send_message("❌ 物品已不存在", ephemeral=True)
            return
        if self.npc_name:
            reward = roll(self.npc_name)
            p["inventory"].remove(self.offer)
            p["inventory"].append(reward)
            sp = SPECIAL_REWARDS.get(reward)
            if sp:
                if sp["effect"]=="food+1": p["food"]+=1
                if sp["effect"]=="food+3": p["food"]+=3
                if sp["effect"]=="fuel+2": p["fuel"]+=2
                if sp["effect"]=="fuel+50": p["fuel"]+=50
                if sp["effect"]=="fuel+100": p["fuel"]+=100
                if sp["effect"]=="fuel_full": p["fuel"]=999
                emb=discord.Embed(title=f"✨ {reward}", description=f"{sp['text']}\n\n{self.offer} -> {reward}", color=sp["color"])
                if sp["image"]: emb.set_image(url=sp["image"])
                await interaction.response.edit_message(embed=emb, view=None)
            else:
                await interaction.response.edit_message(embed=discord.Embed(title=f"与 {self.npc_name} 交易", description=f"{self.offer} -> {reward}", color=ALL_NPCS[self.npc_name]["color"]), view=None)
        else:
            get_player(self.to_id)["inventory"].append(self.offer)
            p["inventory"].remove(self.offer)
            await interaction.response.edit_message(embed=discord.Embed(title="交易完成", description=f"{self.offer} 已给对方"), view=None)
        save_now()

class GiveItemView(discord.ui.View):
    def __init__(self, user_id):
        super().__init__(timeout=120); self.user_id=user_id
        opts1=[discord.SelectOption(label=i) for i in ALL_ITEMS_POOL[:25]]
        self.sel1=discord.ui.Select(placeholder="选择物品1-25", options=opts1, min_values=1, max_values=5); self.sel1.callback=self.cb1; self.add_item(self.sel1)
        if len(ALL_ITEMS_POOL)>25:
            opts2=[discord.SelectOption(label=i) for i in ALL_ITEMS_POOL[25:]]
            self.sel2=discord.ui.Select(placeholder="选择物品26-更多", options=opts2, min_values=1, max_values=5); self.sel2.callback=self.cb2; self.add_item(self.sel2)
    async def cb1(self, interaction: discord.Interaction):
        if interaction.user.id!=self.user_id: return
        p=get_player(self.user_id); p["inventory"].extend(self.sel1.values); save_now()
        await interaction.response.send_message(f"✅ 已给予：{', '.join(self.sel1.values)}", ephemeral=True)
    async def cb2(self, interaction: discord.Interaction):
        if interaction.user.id!=self.user_id: return
        p=get_player(self.user_id); p["inventory"].extend(self.sel2.values); save_now()
        await interaction.response.send_message(f"✅ 已给予：{', '.join(self.sel2.values)}", ephemeral=True)

@bot.tree.command(name="开发者", description="开发者模式[仅限]")
async def 开发者(interaction: discord.Interaction):
    if interaction.user.id not in DEV_IDS: await interaction.response.send_message("❌ 你不是开发者", ephemeral=True); return
    if interaction.user.id in dev_mode_users:
        dev_mode_users.remove(interaction.user.id); await interaction.response.send_message(embed=discord.Embed(title="DEV 已关闭", color=0xff0000))
    else:
        dev_mode_users.add(interaction.user.id); d=get_player(interaction.user.id); 
        for k in ALL_NPCS.keys(): d["met_npcs"].add(k); d["npc_met_km"][k]=d["km"]
        await interaction.response.send_message(embed=discord.Embed(title="DEV 已开启", color=0xffd700))
    save_now()

@bot.tree.command(name="跳跃", description="开发者跳跃[仅限]")
async def 跳跃(interaction: discord.Interaction, km: int):
    if interaction.user.id not in dev_mode_users: await interaction.response.send_message("❌ 需先 /开发者", ephemeral=True); return
    d=get_player(interaction.user.id); d["km"]=km; d["step"]+=1; save_now()
    await interaction.response.send_message(embed=discord.Embed(title="DEV跳跃", description=f"已到 {km}km", color=0xffd700))

@bot.tree.command(name="给予", description="开发者给予")
async def 给予(interaction: discord.Interaction):
    if interaction.user.id not in dev_mode_users: await interaction.response.send_message("❌ 需先 /开发者", ephemeral=True); return
    await interaction.response.send_message(embed=discord.Embed(title="DEV给予", color=0xffd700), view=GiveItemView(interaction.user.id), ephemeral=True)

@bot.tree.command(name="步行", description="步行1000km到上层")
async def 步行(interaction: discord.Interaction):
    data = get_player(interaction.user.id)
    is_dev_now = interaction.user.id in dev_mode_users
    if data["ended"] and not is_dev_now:
        embed = discord.Embed(title="—— 1000km，终点", description="你们已经在终点了。\n要重新开始吗？", color=0x000000)
        embed.set_image(url="https://cdn.discordapp.com/attachments/1519326691095478272/1564967119534432256/images_32.jpg?ex=6ae330b4&is=6ae1df34&hm=3568f2eb3183a449c878197dd0c48b29a5cecd1b1a677c2ae390f19078c38b85&")
        await interaction.response.send_message(embed=embed, view=RestartView(interaction.user.id), ephemeral=True)
        return
    prev_km = data["km"]
    data["step"] += 1

    if not is_dev_now and data["fuel"] <= 0:
        move = random.randint(1, 2); data["km"] += move; low_fuel = True
    else:
        move = random.randint(3, 5); data["km"] += move; low_fuel = False

    if data["step"] == 2 and not data["visited_airplane"]:
        data["visited_airplane"] = True; data["food"] += 10
        data["inventory"].extend(["压缩口粮 x10", "生锈的仪表盘"]); save_now()
        await interaction.response.send_message(embed=discord.Embed(title="发现报废战斗机", description="获得：压缩口粮 x10", color=0x8b9a7d))
        return

    if not is_dev_now:
        data["food"] -= 1; data["fuel"] = max(0, data["fuel"] - 1)
        if data["food"] <= 0:
            players.pop(interaction.user.id, None); save_now()
            await interaction.response.send_message(embed=discord.Embed(title="饿死了...", color=0x000000))
            return

    if data["km"] >= 1000 and not data["ended"]:
        data["ended"] = True; data["met_npcs"].add("上层的幽灵"); data["npc_met_km"]["上层的幽灵"]=data["km"]; data["inventory"].append("星空的照片"); save_now()
        embed = discord.Embed(title="—— 1000km，终点", description="……嗯。\n\n千户：我们现在这样，是正确的吗？\n尤莉：我们现在是世界上最幸福的人。\n—— 少女终末旅行 完", color=0x000000)
        embed.set_image(url="https://cdn.discordapp.com/attachments/1519326691095478272/1564967119534432256/images_32.jpg?ex=6ae330b4&is=6ae1df34&hm=3568f2eb3183a449c878197dd0c48b29a5cecd1b1a677c2ae390f19078c38b85&")
        await interaction.response.send_message(embed=embed, view=RestartView(interaction.user.id))
        return

    if prev_km < 750 <= data["km"]:
        save_now()
        await interaction.response.send_message(embed=discord.Embed(title="⚠️ 补给线断绝", description=f"已到达 {data['km']}km\n越接近上层，城市越干净...\n**从现在起，地上不会再生成食物和燃料**\n食物{data['food']} 燃料{data['fuel']}", color=0xff4444))
        return

    if data["km"] < 750:
        force_met = []
        for name, nd in ALL_NPCS.items():
            if name == "上层的幽灵": continue
            if name not in data["met_npcs"] and data["km"] >= nd["km_need"]:
                data["met_npcs"].add(name); data["npc_met_km"][name]=data["km"]; force_met.append(name)
        if force_met:
            save_now()
            desc = ""
            for n in force_met:
                desc += f"✅ 遇到了 **{n}**！ 在 {data['km']}km\n"
            desc += f"\n⚠️ **只能在15km内交易**，超过 {data['km']+15}km 后他就会离开！\n"
            desc += f"用 `/交易 npc:{force_met[0]}` 交易"
            await interaction.response.send_message(embed=discord.Embed(title=f"📍 发现 {len(force_met)} 个旅人", description=desc, color=0xffd700))
            return
    else:
        for name, nd in ALL_NPCS.items():
            if name not in data["met_npcs"] and data["km"] >= nd["km_need"] and name != "上层的幽灵":
                if random.random() < 0.35 or is_dev_now:
                    data["met_npcs"].add(name); data["npc_met_km"][name]=data["km"]; save_now()
                    await interaction.response.send_message(embed=discord.Embed(
                        title=f"📍 遇到了 {name}！", 
                        description=f"在 {data['km']}km 遇到\n\n⚠️ 只能在 **{data['km']}km - {data['km']+15}km** 内交易\n超过就会离开！快用 `/交易 npc:{name}`",
                        color=nd["color"]
                    ))
                    return

    if data["km"] < 550:
        roll_type = random.choices(["空空", "食物", "杂物"], weights=[30, 45, 25])[0]
    else:
        roll_type = random.choices(["空空", "食物", "杂物"], weights=[45, 35, 20])[0]

    push_text = "\n\n⛽ 没燃料了，只能推着Kettenkrad走 (1-2km)" if low_fuel else ""

    if roll_type == "空空":
        save_now()
        embed = discord.Embed(title="空空", description=random.choice(["什么都没有...", "只有风声...", "空空如也", "尤莉：千户，好无聊啊~"]) + push_text, color=0x555555)
        embed.set_author(name=f"{data['km']}/1000km | Step {data['step']} | 食物{data['food']} 燃料{data['fuel']} | 本次+{move}km")
        await interaction.response.send_message(embed=embed); return

    if roll_type == "食物":
        if data["km"] >= 750 and not is_dev_now:
            save_now()
            await interaction.response.send_message(embed=discord.Embed(title="空空", description="真正的上层，什么都没有...只有风\n*750km后已无补给*" + push_text, color=0x111111))
            return
        food_pool = ["压缩口粮 x1", "土豆干 x2", "压缩口粮 x10", "军用口粮 x10", "燃料桶(半满)", "燃料桶(半满)", "燃料桶 x20", "燃料桶 x20"]
        food_item = random.choice(food_pool)
        data["inventory"].append(food_item)
        if "口粮" in food_item or "土豆" in food_item:
            add = 10 if "x10" in food_item else (2 if "x2" in food_item else 1)
            data["food"] += add
        if "燃料" in food_item:
            if "x20" in food_item: data["fuel"] += 20
            else: data["fuel"] += 5
        save_now()
        embed = discord.Embed(title="🍙 找到食物！" if "口粮" in food_item or "土豆" in food_item else "⛽ 找到燃料！", description=f"获得 **{food_item}**" + push_text, color=0x8b9a7d if "口粮" in food_item else 0xffaa00)
        embed.set_author(name=f"{data['km']}/1000km | Step {data['step']} | 食物{data['food']} 燃料{data['fuel']} | 本次+{move}km")
        await interaction.response.send_message(embed=embed); return

    if roll_type == "杂物":
        loot_pool = RANDOM_LOOT
        if data["km"] >= 750 and not is_dev_now:
            loot_pool = [x for x in RANDOM_LOOT if "食物" not in x[2] and "燃料" not in x[2]]
        item, _, typ = random.choices(loot_pool, weights=[w for _, w, _ in loot_pool])[0]
        data["inventory"].append(item)
        if "食物+" in typ and not is_dev_now: data["food"] += int(typ.split("+")[1])
        if "燃料+" in typ and not is_dev_now: data["fuel"] += int(typ.split("+")[1])
        data["fuel"] = max(0, data["fuel"]); save_now()
        embed = discord.Embed(title="在废墟里翻到了..." if "稀有" not in typ else "✨ 稀有！", description=f"获得 {item}" + push_text, color=0xffd700 if "稀有" in typ else 0xa9a9a9)
        embed.set_author(name=f"{data['km']}/1000km | Step {data['step']} | 食物{data['food']} 燃料{data['fuel']} | 本次+{move}km")
        await interaction.response.send_message(embed=embed); return

    save_now()
    embed = discord.Embed(title="空空", description="什么都没有..." + push_text, color=0x555555)
    embed.set_author(name=f"{data['km']}/1000km | Step {data['step']} | 食物{data['food']} 燃料{data['fuel']} | 本次+{move}km")
    await interaction.response.send_message(embed=embed)

@bot.tree.command(name="背包", description="背包")
async def 背包(interaction: discord.Interaction):
    d=get_player(interaction.user.id)
    lines, _ = format_backpack(d["inventory"])
    text = "\n".join(lines) if lines else "空空如也"
    if len(text) > 3500:
        text = text[-3500:]
    embed = discord.Embed(title=f"{d['km']}/1000km 背包", description=text, color=0x8b9a7d)
    embed.set_footer(text=f"共{len(d['inventory'])}件 | 食物{d['food']} 燃料{d['fuel']}")
    await interaction.response.send_message(embed=embed)

@bot.tree.command(name="交易", description="交易")
@discord.app_commands.choices(npc=[discord.app_commands.Choice(name=k, value=k) for k in ALL_NPCS.keys()])
async def 交易(interaction: discord.Interaction, 用户: discord.Member=None, npc: str=None):
    await interaction.response.defer(ephemeral=True)
    if not 用户 and not npc:
        await interaction.followup.send("用法：/交易 用户:@xxx 或 /交易 npc:金泽", ephemeral=True)
        return
    d=get_player(interaction.user.id)
    if not d["inventory"]:
        await interaction.followup.send("❌ 背包空的", ephemeral=True)
        return
    if npc:
        if npc not in d["met_npcs"] and interaction.user.id not in dev_mode_users:
            await interaction.followup.send(f"❌ 你还没遇到过 {npc}", ephemeral=True)
            return
        if interaction.user.id not in dev_mode_users:
            met_at = d["npc_met_km"].get(npc, 0)
            dist = d["km"] - met_at
            if dist > 15:
                await interaction.followup.send(embed=discord.Embed(
                    title="❌ 他已经不在这里了",
                    description=f"你在 {met_at}km 遇到 {npc}，现在已经 {d['km']}km，离开了 {dist}km。",
                    color=0x555555
                ), ephemeral=True)
                return
        view = TradeView(interaction.user.id, npc_name=npc, inventory=d["inventory"])
        met_at = d["npc_met_km"].get(npc, 0)
        await interaction.followup.send(embed=discord.Embed(
            title=f"与 {npc} 交易", 
            description=f"在 {met_at}km 遇到，现在 {d['km']}km (距离 {d['km']-met_at}km)\n还能交易 {15-(d['km']-met_at)}km",
            color=ALL_NPCS[npc]["color"]
        ), view=view, ephemeral=True)
    else:
        if 用户.id == interaction.user.id:
            await interaction.followup.send("❌ 不能跟自己交易", ephemeral=True); return
        view = TradeView(interaction.user.id, to_id=用户.id, inventory=d["inventory"])
        await interaction.followup.send(f"{用户.mention} 收到一个交易请求", embed=discord.Embed(title="玩家交易"), view=view, ephemeral=True)

@bot.tree.command(name="图鉴", description="图鉴")
async def 图鉴(interaction: discord.Interaction):
    d=get_player(interaction.user.id); desc=""
    for n,nd in ALL_NPCS.items():
        has = '✅' if n in d["met_npcs"] or interaction.user.id in dev_mode_users else '❓'
        if has=='✅' and n in d["npc_met_km"]:
            desc+=f"{has} {n} - {nd['km_need']}km (在{d['npc_met_km'][n]}km遇到)\n"
        else:
            desc+=f"{has} {n} - {nd['km_need']}km\n"
    await interaction.response.send_message(embed=discord.Embed(title="图鉴", description=desc))

@bot.event
async def on_ready():
    await bot.tree.sync()
    print("Bot 上线 v17.5 - 背包合并")

threading.Thread(target=run_flask, daemon=True).start()
bot.run(os.getenv("DISCORD_TOKEN"))
