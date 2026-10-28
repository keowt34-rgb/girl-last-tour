import discord
from discord.ext import commands
import random
import threading
import json
import os
from flask import Flask

app = Flask(__name__)
SAVE_FILE = "save.json"
players = {}
dev_mode_users = set()
DEV_IDS = [1200298327531585537]  # 改你的ID

def load_save():
    global players, dev_mode_users
    if os.path.exists(SAVE_FILE):
        try:
            with open(SAVE_FILE, "r", encoding="utf-8") as f:
                data = json.load(f)
                for uid, pdata in data.get("players", {}).items():
                    pdata["met_npcs"] = set(pdata.get("met_npcs", ["千户","尤莉"]))
                    players[int(uid)] = pdata
                dev_mode_users = set(data.get("dev_mode_users", []))
                print(f"[SAVE] 已加载 {len(players)} 玩家")
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

@app.route("/")
def index():
    total = sum(p['km'] for p in players.values())
    return f"Kettenkrad v15.1 | {len(players)}人 {total}km"

def run_flask():
    port = int(os.environ.get("PORT", 10000))
    app.run(host="0.0.0.0", port=port)

intents = discord.Intents.default()
bot = commands.Bot(command_prefix="/", intents=intents)

# ===== 特殊奖励全量 =====
SPECIAL_REWARDS = {
    "尤莉的笑脸": {"text": "尤莉：嘿嘿~ 千户你看我笑得可爱吗？\n千户：...笨蛋。", "image": "https://i.imgur.com/8Km9tLL.gif", "color": 0xf2c17c, "effect": "food+1"},
    "尤莉的歌声": {"text": "尤莉：♪~ 拉拉拉~ 终末世界也要唱歌！", "image": None, "color": 0xf2c17c, "effect": "fuel+2"},
    "尤莉的拥抱": {"text": "尤莉：千户，好冷啊，抱一下！\n千户：等等、太近了！", "image": "https://i.imgur.com/3t6K9Qp.gif", "color": 0xf2c17c, "effect": "food+3"},
    "日记(千户写的)": {"text": "千户的日记：今天尤莉又把枪弄丢了...", "image": None, "color": 0x8b9a7d, "effect": "none"},
    "金泽的眼镜": {"text": "金泽：没有这个我看不清地图了...算了，送你吧。", "image": None, "color": 0x87ceeb, "effect": "none"},
    "石像爷爷的刻刀": {"text": "石像爷爷：用这个刻，能刻得更久。", "image": None, "color": 0xa9a9a9, "effect": "none"},
    "管制官的密钥": {"text": "管制官：密钥已移交...工厂将永远运行。", "image": None, "color": 0xff4444, "effect": "fuel+50"},
    "发光的努可": {"text": "努可把子弹吃掉了，全身发光...\n效果：燃料充满", "image": None, "color": 0xffffff, "effect": "fuel_full"},
    "电能 x100": {"text": "努可：努可！ (释放100电能)", "image": None, "color": 0xffffff, "effect": "fuel+100"},
    "星空的照片": {"text": "千户：...好美。\n尤莉：这就是...星星吗？\n—— 真结局《星空》", "image": "https://i.imgur.com/wQSkR6p.jpeg", "color": 0x000000, "effect": "END"},
    "END标记": {"text": "上面什么都没有了。\n但旅途本身，就是意义。\n—— 少女终末旅行 完", "image": None, "color": 0x000000, "effect": "END"},
    "小地藏雕像": {"text": "石像爷爷：保佑你们的旅途。", "image": None, "color": 0xa9a9a9, "effect": "none"},
    "飞机设计图": {"text": "石井：这架飞机本来想去上层的", "image": None, "color": 0xdeb887, "effect": "none"},
    "世界地图(残缺)": {"text": "金泽：这地图我画了半辈子", "image": None, "color": 0x87ceeb, "effect": "none"},
}

ALL_NPCS = {
    "金泽": {"desc": "地图", "talk": "世界比想象大...", "color": 0x87ceeb, "km_need": 50},
    "石像爷爷": {"desc": "雕刻", "talk": "雕刻证明存在过", "color": 0xa9a9a9, "km_need": 150},
    "石井": {"desc": "飞机", "talk": "想去上层", "color": 0xdeb887, "km_need": 300},
    "管制官": {"desc": "工厂AI", "talk": "生产还在继续...", "color": 0xff4444, "km_need": 500},
    "努可": {"desc": "白色生物", "talk": "努可！", "color": 0xffffff, "km_need": 700},
    "尤莉": {"desc": "同伴", "talk": "有吃的吗？", "color": 0xf2c17c, "km_need": 0},
    "千户": {"desc": "同伴", "talk": "记下来...", "color": 0x8b9a7d, "km_need": 0},
    "上层的幽灵": {"desc": "最终", "talk": "上面什么都没有了哦", "color": 0x000000, "km_need": 1000},
}

# ===== 完整掉落表 =====
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
    ("生锈的螺栓", 20, "垃圾"),
    ("空罐头", 20, "垃圾"),
    ("旧报纸", 15, "垃圾"),
    ("破布", 10, "垃圾"),
    ("燃料桶(半满)", 8, "燃料+5"),
    ("压缩口粮 x1", 10, "食物+1"),
    ("土豆干 x2", 5, "食物+2"),
    ("尤莉的笑脸", 1, "稀有"),
    ("小地藏雕像", 3, "稀有"),
    ("发光的石头", 3, "垃圾"),
    ("38式步枪子弹 x5", 5, "垃圾"),
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
        players[uid] = {"km":0,"food":2,"fuel":8,"step":0,"visited_airplane":False,"ended":False,"met_npcs":set(["千户","尤莉"]),"inventory":["Kettenkrad履带摩托","38式步枪","手枪与一发子弹","千户的日记","毛毯 x2"]}
        save_now()
    return players[uid]

class TradeView(discord.ui.View):
    def __init__(self, from_id, to_id=None, npc_name=None):
        super().__init__(timeout=120); self.from_id=from_id; self.to_id=to_id; self.npc_name=npc_name; self.offer=None
    @discord.ui.select(placeholder="选择物品", min_values=1, max_values=1, options=[discord.SelectOption(label="占位")])
    async def select_give(self, interaction: discord.Interaction, select: discord.ui.Select):
        if interaction.user.id!=self.from_id: return
        self.offer=select.values[0]
        await interaction.response.send_message(f"已选：{self.offer}", ephemeral=True)
    @discord.ui.button(label="确认", style=discord.ButtonStyle.success, emoji="🤝")
    async def confirm(self, interaction: discord.Interaction, button: discord.ui.Button):
        if interaction.user.id!=self.from_id or not self.offer: return
        p=get_player(self.from_id)
        if self.offer not in p["inventory"]: return
        if self.npc_name:
            reward=roll(self.npc_name); p["inventory"].remove(self.offer); p["inventory"].append(reward)
            sp=SPECIAL_REWARDS.get(reward)
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
            get_player(self.to_id)["inventory"].append(self.offer); p["inventory"].remove(self.offer)
            await interaction.response.edit_message(embed=discord.Embed(title="交易完成"), view=None)
        save_now()

# ===== 开发者随时拿物品 =====
class GiveItemView(discord.ui.View):
    def __init__(self, user_id):
        super().__init__(timeout=120)
        self.user_id = user_id
        opts1 = [discord.SelectOption(label=i) for i in ALL_ITEMS_POOL[:25]]
        self.sel1 = discord.ui.Select(placeholder="选择物品1-25 (可多选5个)", options=opts1, min_values=1, max_values=5)
        self.sel1.callback = self.cb1
        self.add_item(self.sel1)
        if len(ALL_ITEMS_POOL) > 25:
            opts2 = [discord.SelectOption(label=i) for i in ALL_ITEMS_POOL[25:]]
            self.sel2 = discord.ui.Select(placeholder="选择物品26-更多 (可多选5个)", options=opts2, min_values=1, max_values=5)
            self.sel2.callback = self.cb2
            self.add_item(self.sel2)
    async def cb1(self, interaction: discord.Interaction):
        if interaction.user.id != self.user_id: return
        p=get_player(self.user_id); p["inventory"].extend(self.sel1.values); save_now()
        await interaction.response.send_message(f"✅ 已给予：{', '.join(self.sel1.values)}", ephemeral=True)
    async def cb2(self, interaction: discord.Interaction):
        if interaction.user.id != self.user_id: return
        p=get_player(self.user_id); p["inventory"].extend(self.sel2.values); save_now()
        await interaction.response.send_message(f"✅ 已给予：{', '.join(self.sel2.values)}", ephemeral=True)

@bot.tree.command(name="开发者", description="开发者模式[仅限]")
async def 开发者(interaction: discord.Interaction):
    if interaction.user.id not in DEV_IDS:
        await interaction.response.send_message("❌ 你不是开发者", ephemeral=True); return
    if interaction.user.id in dev_mode_users:
        dev_mode_users.remove(interaction.user.id)
        await interaction.response.send_message(embed=discord.Embed(title="DEV 已关闭", color=0xff0000))
    else:
        dev_mode_users.add(interaction.user.id)
        d=get_player(interaction.user.id)
        for k in ALL_NPCS.keys(): d["met_npcs"].add(k)
        await interaction.response.send_message(embed=discord.Embed(title="DEV 已开启", description="✅ 无视消耗 ✅ 全图鉴 ✅ /跳跃 ✅ /给予随时拿物品", color=0xffd700))
    save_now()

@bot.tree.command(name="跳跃", description="开发者跳跃[仅限]")
async def 跳跃(interaction: discord.Interaction, km: int):
    if interaction.user.id not in dev_mode_users:
        await interaction.response.send_message("❌ 需先 /开发者", ephemeral=True); return
    d=get_player(interaction.user.id); d["km"]=km; d["step"]+=1; save_now()
    await interaction.response.send_message(embed=discord.Embed(title="DEV跳跃", description=f"已到 {km}km", color=0xffd700))

@bot.tree.command(name="给予", description="开发者给予物品[仅限开发者]")
async def 给予(interaction: discord.Interaction):
    if interaction.user.id not in dev_mode_users:
        await interaction.response.send_message("❌ 需先 /开发者", ephemeral=True); return
    await interaction.response.send_message(embed=discord.Embed(title="DEV给予", description="下拉选择，不会打错字", color=0xffd700), view=GiveItemView(interaction.user.id), ephemeral=True)

@bot.tree.command(name="步行", description="步行1000km到上层")
async def 步行(interaction: discord.Interaction):
    data=get_player(interaction.user.id)
    is_dev_now = interaction.user.id in dev_mode_users
    if data["ended"] and not is_dev_now:
        await interaction.response.send_message("旅途已结束...", ephemeral=True); return
    prev_km = data["km"]
    data["step"]+=1; data["km"]+=random.randint(2,4)

    if data["step"]==2 and not data["visited_airplane"]:
        data["visited_airplane"]=True; data["food"]+=10
        data["inventory"].extend(["压缩口粮 x10","生锈的仪表盘"]); save_now()
        await interaction.response.send_message(embed=discord.Embed(title="发现报废战斗机", description="获得：压缩口粮 x10", color=0x8b9a7d)); return

    if not is_dev_now:
        data["food"]-=1
        # 燃料耗尽维持0，不会变负数
        data["fuel"] = max(0, data["fuel"] - 1)
        if data["food"]<=0:
            players.pop(interaction.user.id, None); save_now()
            await interaction.response.send_message(embed=discord.Embed(title="饿死了...", color=0x000000)); return

        if data["km"]>=1000 and not data["ended"]:
        data["ended"]=True; data["met_npcs"].add("上层的幽灵"); data["inventory"].append("星空的照片"); save_now()
        embed=discord.Embed(title="—— 1000km，终点", description="……嗯。\n\n千户：我们现在这样，是正确的吗？\n尤莉：我们现在是世界上最幸福的人。\n—— 少女终末旅行 完", color=0x000000)
        # 原作图片写死本地，永久不走外链
        try:
            file = discord.File("ending.jpg", filename="ending.jpg")
            embed.set_image(url="attachment://ending.jpg")
            await interaction.response.send_message(embed=embed, file=file)
        except Exception as e:
            print(f"[IMG] ending.jpg 没找到: {e}")
            # 没图也发文字，不会报错
            await interaction.response.send_message(embed=embed)
        return

    if prev_km < 750 <= data["km"]:
        save_now()
        await interaction.response.send_message(embed=discord.Embed(title="⚠️ 补给线断绝", description=f"已到达 {data['km']}km\n越接近上层，城市越干净，食物燃料几乎没有了...\n**从现在起，地上不会再生成食物和燃料**\n请检查背包：食物{data['food']} 燃料{data['fuel']}\n*开发者不受影响*", color=0xff4444))
        return

    # ===== 750km以下强制遇光全部NPC，除了上层的幽灵 =====
    if data["km"] < 750:
        force_met = []
        for name, nd in ALL_NPCS.items():
            if name == "上层的幽灵":
                continue
            if name not in data["met_npcs"] and data["km"] >= nd["km_need"]:
                data["met_npcs"].add(name)
                force_met.append(name)
        if force_met:
            save_now()
            desc = "\n".join([f"遇到了 {n}！" for n in force_met])
            await interaction.response.send_message(embed=discord.Embed(title=f"📍 发现 {len(force_met)} 个旅人", description=desc, color=0xffd700))
            return
    else:
        # 750以上还是随机遇
        for name,nd in ALL_NPCS.items():
            if name not in data["met_npcs"] and data["km"]>=nd["km_need"] and name!="上层的幽灵":
                if random.random()<0.35 or is_dev_now:
                    data["met_npcs"].add(name); save_now()
                    await interaction.response.send_message(embed=discord.Embed(title=f"遇到了 {name}！", color=nd["color"])); return

    # ===== 新机率：空空40 食物40 杂物20 =====
    roll_type = random.choices(["空空","食物","杂物"], weights=[40,40,20])[0]

    if roll_type == "空空":
        save_now()
        embed=discord.Embed(title="空空", description=random.choice(["什么都没有...","只有风声...","空空如也","尤莉：千户，好无聊啊~"]), color=0x555555)
        embed.set_author(name=f"{data['km']}/1000km | Step {data['step']} | 食物{data['food']} 燃料{data['fuel']}")
        await interaction.response.send_message(embed=embed)
        return

    if roll_type == "食物":
        if data["km"] >= 750 and not is_dev_now:
            save_now()
            await interaction.response.send_message(embed=discord.Embed(title="空空", description="真正的上层，什么都没有...只有风\n*750km后已无补给*", color=0x111111))
            return
        food_item = random.choice(["压缩口粮 x1","土豆干 x2","压缩口粮 x10","军用口粮 x10","燃料桶(半满)"])
        data["inventory"].append(food_item)
        if "口粮" in food_item or "土豆" in food_item:
            add = 10 if "x10" in food_item else (2 if "x2" in food_item else 1)
            data["food"] += add
        if "燃料" in food_item:
            data["fuel"] += 5
        save_now()
        embed=discord.Embed(title="🍙 找到食物！", description=f"获得 **{food_item}**", color=0x8b9a7d)
        embed.set_author(name=f"{data['km']}/1000km | Step {data['step']} | 食物{data['food']} 燃料{data['fuel']}")
        await interaction.response.send_message(embed=embed)
        return

    if roll_type == "杂物":
        loot_pool = RANDOM_LOOT
        if data["km"] >= 750 and not is_dev_now:
            loot_pool = [x for x in RANDOM_LOOT if "食物" not in x[2] and "燃料" not in x[2]]
        item,_,typ = random.choices(loot_pool, weights=[w for _,w,_ in loot_pool])[0]
        data["inventory"].append(item)
        if "食物+" in typ and not is_dev_now: data["food"]+=int(typ.split("+")[1])
        if "燃料+" in typ and not is_dev_now: data["fuel"]+=int(typ.split("+")[1])
        data["fuel"] = max(0, data["fuel"])
        save_now()
        embed=discord.Embed(title="在废墟里翻到了..." if "稀有" not in typ else "✨ 稀有！", description=f"获得 {item}", color=0xffd700 if "稀有" in typ else 0xa9a9a9)
        extra = " | 最后250km 无补给" if data["km"]>=750 and not is_dev_now else ""
        embed.set_author(name=f"{data['km']}/1000km | Step {data['step']}{extra} | 食物{data['food']} 燃料{data['fuel']}")
        await interaction.response.send_message(embed=embed)
        return
        
    save_now()
    embed=discord.Embed(title="空空", description=random.choice(["什么都没有...","只有风声...","空空如也"]), color=0x555555)
    embed.set_author(name=f"{data['km']}/1000km | Step {data['step']} | 食物{data['food']} 燃料{data['fuel']}")
    await interaction.response.send_message(embed=embed)

@bot.tree.command(name="背包", description="背包")
async def 背包(interaction: discord.Interaction):
    d=get_player(interaction.user.id)
    await interaction.response.send_message(embed=discord.Embed(title=f"{d['km']}/1000km 背包", description="\n".join(d["inventory"]), color=0x8b9a7d))

@bot.tree.command(name="交易", description="交易")
@discord.app_commands.choices(npc=[discord.app_commands.Choice(name=k, value=k) for k in ALL_NPCS.keys()])
async def 交易(interaction: discord.Interaction, 用户: discord.Member=None, npc: str=None):
    if not 用户 and not npc: await interaction.response.send_message("用法：/交易", ephemeral=True); return
    d=get_player(interaction.user.id); opts=[discord.SelectOption(label=i) for i in d["inventory"][:25]]
    if npc:
        if npc not in d["met_npcs"] and interaction.user.id not in dev_mode_users:
            await interaction.response.send_message(f"❌ 没遇到过 {npc}", ephemeral=True); return
        view=TradeView(interaction.user.id, npc_name=npc); view.select_give.options=opts
        await interaction.response.send_message(embed=discord.Embed(title=f"与 {npc} 交易", color=ALL_NPCS[npc]["color"]), view=view)
    else:
        view=TradeView(interaction.user.id, to_id=用户.id); view.select_give.options=opts
        await interaction.response.send_message(f"{用户.mention} 交易", view=view)

@bot.tree.command(name="图鉴", description="图鉴")
async def 图鉴(interaction: discord.Interaction):
    d=get_player(interaction.user.id); desc=""
    for n,nd in ALL_NPCS.items(): desc+=f"{'✅' if n in d['met_npcs'] or interaction.user.id in dev_mode_users else '❓'} {n} - {nd['km_need']}km\n"
    await interaction.response.send_message(embed=discord.Embed(title="图鉴", description=desc))

@bot.event
async def on_ready():
    await bot.tree.sync()
    print("Bot 上线 v15.1")

threading.Thread(target=run_flask, daemon=True).start()
bot.run(os.getenv("DISCORD_TOKEN"))
