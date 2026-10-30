import discord
from discord.ext import commands
import random, threading, json, os, time
from flask import Flask
from collections import Counter

app = Flask(__name__)
SAVE_FILE = "save.json"
players = {}
dev_mode_users = set()
DEV_IDS = [1200298327531585537]

FOOD_HUNGER = {
    "压缩口粮 x10": 100, "军用口粮 x10": 100, "压缩口粮 x1": 15,
    "土豆干 x2": 30, "土豆干": 15, "土豆干 x10": 100,
}

def load_save():
    global players, dev_mode_users
    if os.path.exists(SAVE_FILE):
        try:
            with open(SAVE_FILE, "r", encoding="utf-8") as f:
                data = json.load(f)
                for uid, pdata in data.get("players", {}).items():
                    pdata["met_npcs"] = set(pdata.get("met_npcs", ["千户","尤莉"]))
                    pdata["ever_met"] = set(pdata.get("ever_met", list(pdata["met_npcs"])))
                    pdata["npc_met_km"] = pdata.get("npc_met_km", {"千户":0,"尤莉":0})
                    players[int(uid)] = pdata
                dev_mode_users = set(data.get("dev_mode_users", []))
        except Exception as e:
            print(f"[SAVE] {e}")

def save_now():
    try:
        save_data = {
            "players": {uid: {**pdata, "met_npcs": list(pdata["met_npcs"]), "ever_met": list(pdata.get("ever_met", []))} for uid, pdata in players.items()},
            "dev_mode_users": list(dev_mode_users)
        }
        with open(SAVE_FILE, "w", encoding="utf-8") as f:
            json.dump(save_data, f, ensure_ascii=False, indent=2)
    except Exception as e:
        print(f"[SAVE] {e}")

load_save()

def format_backpack(inventory):
    counter = Counter(inventory)
    seen = []
    for i in inventory:
        if i not in seen:
            seen.append(i)
    lines = [f"{name} x{counter[name]}" if counter[name]>1 else name for name in seen]
    return lines, counter

def get_unique_for_trade(inventory):
    seen=[]
    for i in inventory:
        if i not in seen:
            seen.append(i)
    return seen

def get_food_value(name):
    return FOOD_HUNGER.get(name, 0)

def get_fuel_value(name):
    if "燃料桶 x20" in name: return 20
    if "燃料桶(半满)" in name: return 5
    if name=="燃料桶": return 5
    return 0

def sync_item(p, item_name, add=True):
    sign = 1 if add else -1
    fu = get_fuel_value(item_name)
    if fu: p["fuel"] = max(0, p["fuel"] + fu * sign)

@app.route("/")
def index():
    total = sum(p['km'] for p in players.values())
    return f"Kettenkrad v27 FINAL 3000km 报废2550 | {len(players)}人 {total}km"

def run_flask():
    port = int(os.environ.get("PORT", 10000))
    app.run(host="0.0.0.0", port=port)

intents = discord.Intents.default()
intents.guilds = True
bot = commands.Bot(command_prefix="/", intents=intents)

SPECIAL_REWARDS = {
    "尤莉的笑脸": {"text": "尤莉：嘿嘿~ 千户你看我笑得可爱吗？\n千户：...笨蛋。", "image": "https://cdn.discordapp.com/attachments/1519326691095478272/1564967112982663238/44b80e01a3f2b3cb9d0bb35479393411.jpg?ex=6ae48233&is=6ae330b3&hm=a3d9cfd6d08bdc57ff7bb72ac62a88a4df1baef67895aa2e02c488bd891afd1d&", "color": 0xf2c17c, "effect": "none"},
    "尤莉的歌声": {"text": "尤莉：♪~ 拉拉拉~ 终末世界也要唱歌！", "image": None, "color": 0xf2c17c, "effect": "none"},
    "尤莉的拥抱": {"text": "尤莉：千户，好冷啊，抱一下！", "image": "https://cdn.discordapp.com/attachments/1519326691095478272/1564966003581128754/50.jpg?ex=6ae4812a&is=6ae32faa&hm=0dd5f8327b674ecef36d16859a519425ff628b5013d3604e04bdafb46fe63e70&", "color": 0xf2c17c, "effect": "none"},
    "日记(千户写的)": {"text": "千户的日记：今天尤莉又把枪弄丢了...", "image": None, "color": 0x8b9a7d, "effect": "none"},
    "金泽的眼镜": {"text": "金泽：没有这个我看不清地图了...", "image": None, "color": 0x87ceeb, "effect": "none"},
    "世界地图(残缺)": {"text": "金泽：这地图我画了半辈子...", "image": None, "color": 0x87ceeb, "effect": "none"},
    "石像爷爷的刻刀": {"text": "石像爷爷：用这个刻，能刻得更久。", "image": None, "color": 0xa9a9a9, "effect": "none"},
    "小地藏雕像": {"text": "石像爷爷：保佑你们的旅途。", "image": None, "color": 0xa9a9a9, "effect": "none"},
    "飞机设计图": {"text": "石井：这架飞机本来想去上层的...", "image": None, "color": 0xdeb887, "effect": "none"},
    "管制官的密钥": {"text": "管制官：密钥已移交...工厂将永远运行。", "image": None, "color": 0xff4444, "effect": "none"},
    "发光的努可": {"text": "努可把子弹吃掉了，全身发光...", "image": None, "color": 0xffffff, "effect": "fuel_full"},
    "电能 x100": {"text": "努可：努可！ (释放100电能)", "image": None, "color": 0xffffff, "effect": "fuel+100"},
    "星空的照片": {"text": "……嗯。\n千户：...好美。\n—— 终末的星空", "image": "https://cdn.discordapp.com/attachments/1519326691095478272/1564967131077152878/IMG-20261028-WA8675.jpg?ex=6ae48237&is=6ae330b7&hm=6243d7a47ab67af6d0aec83328650e23cc8c6bca192569b30ea7479662c13011&", "color": 0x000000, "effect": "END"},
    "END标记": {"text": "上面什么都没有了。", "image": "https://cdn.discordapp.com/attachments/1519326691095478272/1564980687608483930/Screenshot_20261028_203421.jpg?ex=6ae48ed7&is=6ae33d57&hm=46ca2826a6e6c3e2c736128b40ec19b9cf1a5f3251ee45ef558ebbfc76ddb116&", "color": 0x000000, "effect": "END"},
}

NPC_DIALOGUE = {
    "金泽": "金泽：哦...又是旅人吗？",
    "石像爷爷": "石像爷爷：你们要去上层？",
    "石井": "石井：我的飞机...本来想飞到上层去的",
    "管制官": "管制官：...你们不是工厂的人吧？",
    "努可": "努可：努可！\n尤莉：哇！白白的！好可爱！",
}

ALL_NPCS = {
    "金泽": {"color": 0x87ceeb, "km_need": 150},
    "石像爷爷": {"color": 0xa9a9a9, "km_need": 450},
    "石井": {"color": 0xdeb887, "km_need": 900},
    "管制官": {"color": 0xff4444, "km_need": 1500},
    "努可": {"color": 0xffffff, "km_need": 2100},
    "尤莉": {"color": 0xf2c17c, "km_need": 0},
    "千户": {"color": 0x8b9a7d, "km_need": 0},
    "上层的幽灵": {"color": 0x000000, "km_need": 3000},
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
    ("生锈的螺栓", 15, "尤莉：这是什么？能吃吗？\n千户：不能"), 
    ("空罐头", 15, "尤莉：空的..."),
    ("旧报纸", 10, "千户：...几百年前的新闻了"),
    ("破布", 8, "尤莉：破的..."), 
    ("发光的石头", 2, "尤莉：哇！会发光！"),
    ("38式步枪子弹 x5", 7, "尤莉：子弹！"),
]

ALL_ITEMS_POOL = list(set(list(FOOD_HUNGER.keys()) + ["燃料桶 x20","燃料桶(半满)","生锈的螺栓","空罐头","旧报纸","破布","发光的石头","38式步枪子弹 x5","空弹壳","手绘地图碎片","世界地图(残缺)","金泽的眼镜","小地藏雕像","石像 x10","石像爷爷的刻刀","飞机设计图","螺旋桨碎片","管制官的密钥","日记(千户写的)","修理工具","旧式相机胶卷","尤莉的笑脸","尤莉的歌声","尤莉的拥抱","发光的努可","电能 x100","星空的照片","END标记"]))

FIXED_STORIES = {
    "fish": {
        "type": "km",
        "at": 85,
        "title": "📍 大型水坝",
        "pages": [
            "他们从寒冷的仓库出来后遇到了巨型水坝\n\n"
            "尤莉：是水坝耶！\n"
            "千户：我知道啦，那些水是融化掉了的雪水....我们下去看看，尤莉。\n"
            "尤莉：好！",
            
            "于是他们从旁边的楼梯走了下去\n\n"
            "尤莉：千户，我们下去是干嘛的。\n"
            "千户：看水坝啊。\n"
            "尤莉：就单单看水坝吗？\n"
            "千户：不可能只是单单看水坝啦...",
            
            "他们走到了楼梯口后，脱掉了鞋子前往水域"
            "千户：好冷...\n"
            "尤莉：我也是...啊秋!",
            
            "尤莉：千户你看！天空好蔚蓝耶！\n"
            "千户：嗯？\n"
            "千户：确实很蓝...这天气我们要不洗衣服吧。\n"
            "尤莉：诶？要洗衣服吗？",
            
            "他们换上了另一套服并绑绳子在各自的腰上防止被水冲走\n\n"
            "尤莉：千户干嘛要绑绳子啦。\n"
            "千户：防止被水冲走啊。\n"
            "尤莉：好吧...",
            
            "过了20分钟后尤莉看到了一条鱼，于是不顾千户的警告去抓了那条鱼\n\n"
            "尤莉：千户你看！是鱼耶！\n"
            "千户：干嘛去抓鱼啦...这很危险啦。不过在这个末日环境下竟然还有生物，真是奇迹。\n"
            "尤莉：千户要不我们把它烤来吃吧。\n"
            "千户：好主意！",
            
            "于是他们烤了鱼后并吃了下去\n\n"
            "尤莉：千户，你尝尝。很好吃！\n"
            "千户：给我我试看。\n"
            "千户：嗯~ 味道确实不错但有点怪\n"
            "—— 饥饿度+65%",
            
            "吃饱喝足后他们就躺在石头上享受风吹来的感觉\n\n"
            "千户：啊，爽了。\n"
            "尤莉：是啊。",
            
            "简单收拾了后他们就继续上路了"
        ],
        "images": {
            0: "https://cdn.discordapp.com/attachments/1519326691095478272/1565621088938106960/Screenshot_20261030_140306_com.android.chrome_edit_18555639303938.jpg?ex=6ae591c3&is=6ae44043&hm=f88d096397fcdeb6fb9a0dbc65aab17c732992bc5bcaceeea010492bc3267e8f&",
            1: "https://cdn.discordapp.com/attachments/1519326691095478272/1565621089609187358/Screenshot_20261030_140419_com.android.chrome_edit_18570951399769.jpg?ex=6ae591c3&is=6ae44043&hm=ef82b943fa1558a77831bd3d947ecd58666cf2dcdc78949cdc15b1e86bd6e83e&",
            3: "https://cdn.discordapp.com/attachments/1519326691095478272/1565621089936089158/Screenshot_20261030_140535_com.android.chrome_edit_18577987304976.jpg?ex=6ae591c3&is=6ae44043&hm=1a5398a86a42f2eda6b9ae966f759ec86b27c51dff0f45d780afea767ccdfce3&",
            4: "https://cdn.discordapp.com/attachments/1519326691095478272/1565621090687000586/Screenshot_20261030_140714_com.android.chrome_edit_18588518867995.jpg?ex=6ae591c3&is=6ae44043&hm=2991e56efa14090bca15194dda1901e63f832f38f69a263168f981dfabcd6dfe&",
            5: "https://cdn.discordapp.com/attachments/1519326691095478272/1565621091416936488/Screenshot_20261030_140911_com.android.chrome_edit_18599762266431.jpg?ex=6ae591c4&is=6ae44044&hm=986bc8fb2b75179b986ff30b23e13c6084f3e7ff37d8fef12056d62c48bf4592&",
            6: "https://cdn.discordapp.com/attachments/1519326691095478272/1565621092112924682/Screenshot_20261030_145850_com.android.chrome_edit_21335574459764.jpg?ex=6ae591c4&is=6ae44044&hm=febf4682e117d3a272e81e6f69d3d67e62a3e7463bfcf89f5da1f6c1334035c1&",
            7: "https://cdn.discordapp.com/attachments/1519326691095478272/1565621091794292897/Screenshot_20261030_141147_com.android.chrome_edit_18608049239867.jpg?ex=6ae591c4&is=6ae44044&hm=ed4e4c715810660b8ee0b87030840d141d6592cc5311e95e13e5c335b08814b1&",
        }
    },
    "soup": {
        "type": "step",  # 这个是按步数触发
        "at": 6,         # 25步触发
        "title": "📍 夜光下的热汤",
        "pages": [
            "尤莉：肚子好饿...千户，难得出来我们喝口汤吧。\n"
            "千户：好啦，就当作是纪念我们出来了\n"
            "尤莉：太棒了！",
            
            "于是他们在附近暂时居住喝口汤\n\n"
            "尤莉：千户可以喝了吗？\n"
            "千户：不行，还没煮好\n"
            "尤莉：好吧",
            
            "过了几分钟后...\n\n"
            "尤莉：千户，好了！\n"
            "千户：知道啦。\n"
            "千户为自己跟尤莉倒了杯汤\n\n"
            "尤莉：啊，好好喝！\n"
            "千户：嗯~\n"
            "过后他们简单收拾了后就继续上路了\n\n"
            "—— 饥饿度+40%"
        ],
        "images": {
            2: "https://cdn.discordapp.com/attachments/1519326691095478272/1565373186307260446/Screenshot_20261029_215528_com.android.chrome_edit_193623155043371.jpg?ex=6ae4aae2&is=6ae35962&hm=0024f83146d81b015d7dcaa9759ba93234d4fc565d239e1204641de0c8109436&"
        }
    },
    "hotspring": {
        "type": "km",  # 这个是按公里触发
        "at": 70,      # 100km触发
        "title": "📍 暴风雪中的温泉",
        "pages": [
            "雪越来越大了，什么都看不见只有一个巨大的工厂。\n\n"
            "他们走进去后，四周只有巨大的管道在风里嘎吱响，Kettenkrad的车灯是唯一的光。\n"
            "能见度不到5米。\n\n"
            "尤莉：千户...好冷...\n"
            "千户：再坚持一下！",
            
            "千户：等一下...那个水管有热气？\n"
            "尤莉：诶？真的耶！\n\n"
            "那根水管上面竟然没有雪，顺着蒸汽找过去，废弃的管道上...居然有水声。",
            "尤莉：是温泉！是温泉啊千户！\n"
            "千户：真的是热水...想要洗个澡。\n"
            "尤莉：你等我一下，看我拿枪射爆那个水管。\n\n"
            "砰的一声，水管爆开了，千户赶紧驾Kettenkrad拉来了一个废弃水管",
            
            "两个人把Kettenkrad停好，脱掉厚重的军大衣。\n\n"
            "千户：呜啊~ 活过来了~\n"
            "尤莉：千户你脸好红~\n"
            "千户：是...是被热气熏的啦！\n"
            "雪还在外面下，这里却暖和得像梦一样。",

            "过后他们在工厂里面找了一个地方生火休息\n"
            "千户就提到了日记...\n\n"
            "尤莉：千户，这是什么来的。\n"
            "千户：这是日记，日记可以拿来记起我们会遗忘的东西，像你这种人应该更需要这个东西\n"
            "尤莉：哦。\n"
            "千户：火要没了，填一下火。\n"
            "尤莉：ok。",
            
            "尤莉：那个千户，我可以拿一本来看吗。\n"
            "随后千户拿了一本书给尤莉\n"
            "千户：拿去吧\n"
            "尤莉：ok。",
            
            "过了几分钟后...\n\n"
            "千户：尤莉，火要燃尽了，加一下燃料。\n"
            "尤莉：ok。\n"
            "随后尤莉就把千户的一本日记丢了下去",
            
            "千户：等下！我的日记！\n\n"
            "千户赶紧把被烧了一半的日记出来\n\n"
            "千户：尤莉！\n"
            "尤莉：对不起千户，我不是故意的。\n"
            "千户：baka kuzi gomni！(笨蛋，废物，垃圾！)\n"
            "随后千户就生气的跑去睡觉了\n"
            "尤莉看到千户真的生气了，随后拿了千户的其中一本日记并涂鸦了",
            
            "明天一早，千户醒来就看到尤莉的涂鸦画作\n\n"
            "千户：尤莉，这是不是你涂鸦的。\n"
            "尤莉：我不知道啊。\n"
            "千户：唉，不过还蛮怪可爱的"
        ],
        "images": {
            0: "https://cdn.discordapp.com/attachments/1519326691095478272/1565427726142152754/Screenshot_20261029_232929_com.android.chrome_edit_206629181038261.jpg?ex=6ae4ddae&is=6ae38c2e&hm=2e9a8484279f566021591c4ad556f606a7c9d3b2f4732cf493b7834bca0901cf&",
            2: "https://cdn.discordapp.com/attachments/1519326691095478272/1565427726607847548/Screenshot_20261029_233229_com.android.chrome_edit_206635598435656.jpg?ex=6ae4ddae&is=6ae38c2e&hm=115de438991d62a767b1c40e219e07f92aa3316e14eed2754fcf735dd9fcf9a1&",
            3: "https://cdn.discordapp.com/attachments/1519326691095478272/1565630542106333215/Screenshot_20261030_153628_com.android.chrome_edit_23597795957856.jpg?ex=6ae59a91&is=6ae44911&hm=6f885186dc803e134c3b4b2ced02c26136b64e22ffd5ce59f8cedacfda0296ff&",
            6: "https://cdn.discordapp.com/attachments/1519326691095478272/1565630038219559033/Screenshot_20261030_152903_com.zhiliaoapp.musically_edit_23152539238653.jpg?ex=6ae59a19&is=6ae44899&hm=edd535e68eee9f8ec5a86dd8cb3ff4d2bae50c8d4c580fa75b05f185293449cc&",
            7: "https://cdn.discordapp.com/attachments/1519326691095478272/1565625168645332992/Screenshot_20261030_140159_com.android.chrome_edit_18549156629460.jpg?ex=6ae59590&is=6ae44410&hm=c73327cfcb54e2ad48c0485bb210f081d6b8c59674f4586b7e4210f0a9f3832b&"
        }
    }
}

def roll(npc):
    table = DROP_TABLE.get(npc, [("垃圾", 100)]); r=random.randint(1,100); cur=0
    for item,p in table:
        cur+=p
        if r<=cur: return item
    return table[-1][0]

def get_player(uid):
    if uid not in players:
        players[uid] = {
            "km":0,"hunger":100,"fuel":28,"step":0,"visited_airplane":False,"ended":False,
            "bike_scrapped":False,"bath_to_delete":False,"endless":False,"pause_until":0,
            "met_npcs":set(["千户","尤莉"]),
            "ever_met":set(["千户","尤莉"]),
            "npc_met_km":{"千户":0,"尤莉":0},
            "inventory":["Kettenkrad履带摩托","38式步枪","手枪与一发子弹","千户的日记","毛毯 x2","土豆干 x2","压缩口粮 x1"],
            "fixed_done": []
        }
        save_now()
    p = players[uid]
    if "hunger" not in p or p["hunger"] is None: p["hunger"] = 100
    if "food" in p: del p["food"]
    if "bike_scrapped" not in p: p["bike_scrapped"]=False
    if "bath_to_delete" not in p: p["bath_to_delete"]=False
    if "endless" not in p: p["endless"]=False
    if "pause_until" not in p: p["pause_until"]=0
    if "ever_met" not in p: p["ever_met"]=set(p["met_npcs"])
    if "npc_met_km" not in p: p["npc_met_km"]={}
    if "fixed_done" not in p: p["fixed_done"]=[]
    return p

def is_paused(p):
    return time.time() < p.get("pause_until",0)

class FoodUseSelect(discord.ui.Select):
    def __init__(self, user_id, inventory):
        self.user_id = user_id
        foods = [i for i in inventory if get_food_value(i) > 0]
        unique = []
        for f in foods:
            if f not in unique:
                unique.append(f)
        if not unique:
            options = [discord.SelectOption(label="没有食物", value="none")]
        else:
            _, counter = format_backpack(inventory)
            options = []
            for item in unique[:25]:
                add = get_food_value(item)
                cnt = counter[item]
                label = f"{item} (+{add}%)" + (f" x{cnt}" if cnt>1 else "")
                options.append(discord.SelectOption(label=label[:100], value=item, description=f"恢复 {add}% 饥饿度"))
        super().__init__(placeholder="🍙 选择食物使用", min_values=1, max_values=1, options=options)
    async def callback(self, interaction: discord.Interaction):
        if interaction.user.id != self.user_id:
            await interaction.response.send_message("❌ 不是你的背包", ephemeral=True); return
        if self.values[0] == "none":
            await interaction.response.send_message("❌ 没有食物", ephemeral=True); return
        item_name = self.values[0]
        p = get_player(self.user_id)
        if item_name not in p["inventory"]:
            await interaction.response.send_message("❌ 食物已不在背包", ephemeral=True); return
        add = get_food_value(item_name)
        p["inventory"].remove(item_name)
        p["hunger"] = min(100, p["hunger"] + add)
        save_now()
        embed = discord.Embed(title=f"{p['km']}km 背包 - {p['hunger']}%饥饿 {p['fuel']}燃料 - 刚吃 {item_name} +{add}%", color=0x8b9a7d)
        new_view = WalkView(self.user_id)
        await interaction.response.edit_message(embed=embed, view=new_view)

class FixedStoryView(discord.ui.View):
    def __init__(self, user_id, story_id, page=0):
        super().__init__(timeout=None)
        self.user_id = user_id
        self.story_id = story_id
        self.page = page

    @discord.ui.button(label="▶️ 下一步", style=discord.ButtonStyle.primary)
    async def next_page(self, interaction: discord.Interaction, button: discord.ui.Button):
        if interaction.user.id != self.user_id:
            await interaction.response.send_message("❌ 不是你的旅途", ephemeral=True)
            return
        p = get_player(self.user_id)
        story = FIXED_STORIES[self.story_id]
        self.page += 1
        if self.page >= len(story["pages"]):
            if self.story_id not in p["fixed_done"]:
                p["fixed_done"].append(self.story_id)
                if self.story_id == "fish":
                    p["inventory"].append("鱼")
                    p["hunger"] = min(100, p["hunger"] + 65)
                elif self.story_id == "soup":
                    p["hunger"] = min(100, p["hunger"] + 40)
            save_now()
            await interaction.response.edit_message(embed=discord.Embed(title=f"{story['title']} - End", description="Continue.", color=0x8b9a7d), view=WalkView(self.user_id))
            return
        embed = discord.Embed(title=f"{story['title']} [{self.page+1}/{len(story['pages'])}]", description=story["pages"][self.page], color=0x8b9a7d)
        if "images" in story and self.page in story["images"]:
            embed.set_image(url=story["images"][self.page])
        await interaction.response.edit_message(embed=embed, view=FixedStoryView(self.user_id, self.story_id, self.page))
        
class WalkView(discord.ui.View):
    def __init__(self, user_id):
        super().__init__(timeout=None)
        self.user_id = user_id
        p = get_player(user_id)
        self.add_item(FoodUseSelect(user_id, p["inventory"]))
    @discord.ui.button(label="继续步行 (-5%饥饿)", style=discord.ButtonStyle.primary, emoji="🚶")
    async def continue_walk(self, interaction: discord.Interaction, button: discord.ui.Button):
        if interaction.user.id != self.user_id:
            await interaction.response.send_message("❌ 不是你的旅途", ephemeral=True); return
        p = get_player(interaction.user.id)
        if is_paused(p):
            left = int(p["pause_until"] - time.time())
            await interaction.response.send_message(f"⏸️ 暂停中，还剩 {left}秒", ephemeral=True); return
        if p.get("ended") and not p.get("endless"):
            embed = discord.Embed(title="—— 3000km，终点", description="......嗯。\n\n千户：我们现在这样，是正确的吗？\n尤莉：我们现在是世界上最幸福的人。\n—— 少女终末旅行 完", color=0x000000)
            embed.set_image(url="https://cdn.discordapp.com/attachments/1519326691095478272/1564967119534432256/images_32.jpg?ex=6ae48234&is=6ae330b4&hm=17b4fac59ef27fc216466ce7ee65840a018a7683934c58abbfd69aad81f54753&")
            await interaction.response.send_message(embed=embed, view=RestartView(self.user_id), ephemeral=True)
            return
        await interaction.response.defer()
        await do_walk_logic(interaction)
    @discord.ui.button(label="暂停前进", style=discord.ButtonStyle.secondary, emoji="⏸️")
    async def pause_walk(self, interaction: discord.Interaction, button: discord.ui.Button):
        if interaction.user.id != self.user_id: return
        p = get_player(interaction.user.id)
        p["pause_until"] = time.time() + 300
        save_now()
        await interaction.response.edit_message(embed=discord.Embed(title="⏸️ 已暂停前进 5分钟", color=0x555555), view=ResumeView(self.user_id))

class ResumeView(discord.ui.View):
    def __init__(self, user_id):
        super().__init__(timeout=None)
        self.user_id = user_id
        p = get_player(user_id)
        self.add_item(FoodUseSelect(user_id, p["inventory"]))
    @discord.ui.button(label="恢复前进", style=discord.ButtonStyle.success, emoji="▶️")
    async def resume(self, interaction: discord.Interaction, button: discord.ui.Button):
        if interaction.user.id != self.user_id: return
        p = get_player(interaction.user.id)
        p["pause_until"] = 0
        save_now()
        await interaction.response.edit_message(embed=discord.Embed(title="▶️ 已恢复", color=0x8b9a7d), view=WalkView(self.user_id))

class EndlessConfirmView(discord.ui.View):
    def __init__(self, user_id, to_endless: bool):
        super().__init__(timeout=60)
        self.user_id = user_id; self.to_endless = to_endless
    @discord.ui.button(label="确定", style=discord.ButtonStyle.danger, emoji="⚠️")
    async def confirm(self, interaction: discord.Interaction, button: discord.ui.Button):
        if interaction.user.id != self.user_id: return
        if self.to_endless:
            players[interaction.user.id] = {"km": 0, "hunger": 100, "fuel": 38, "step": 0,"visited_airplane": False, "ended": False,"bike_scrapped": False, "bath_to_delete": False, "endless": True, "pause_until":0,"met_npcs": set(["千户","尤莉","金泽","石像爷爷","石井","管制官","努可"]),"ever_met": set(["千户","尤莉","金泽","石像爷爷","石井","管制官","努可"]),"npc_met_km": {"千户":0,"尤莉":0},"inventory": ["Kettenkrad履带摩托","38式步枪","手枪与一发子弹","毛毯 x2"], "fixed_done": []}
        else:
            players[interaction.user.id] = {"km": 0, "hunger": 100, "fuel": 28, "step": 0,"visited_airplane": False, "ended": False,"bike_scrapped": False, "bath_to_delete": False, "endless": False, "pause_until":0,"met_npcs": set(["千户","尤莉"]),"ever_met": set(["千户","尤莉"]),"npc_met_km": {"千户":0,"尤莉":0},"inventory": ["Kettenkrad履带摩托","38式步枪","手枪与一发子弹","千户的日记","毛毯 x2","土豆干 x2","压缩口粮 x1"], "fixed_done": []}
        save_now()
        await interaction.response.edit_message(embed=discord.Embed(title="已切换", color=0x00ffaa), view=None)

class RestartView(discord.ui.View):
    def __init__(self, user_id):
        super().__init__(timeout=None); self.user_id = user_id
    @discord.ui.button(label="重新开始", style=discord.ButtonStyle.primary, emoji="🔄")
    async def restart(self, interaction: discord.Interaction, button: discord.ui.Button):
        if interaction.user.id != self.user_id: return
        players[interaction.user.id] = {"km": 0, "hunger": 100, "fuel": 28, "step": 0,"visited_airplane": False, "ended": False,"bike_scrapped": False,"bath_to_delete": False,"endless": False, "pause_until":0,"met_npcs": set(["千户","尤莉"]),"ever_met": set(["千户","尤莉"]),"npc_met_km": {"千户":0,"尤莉":0},"inventory": ["Kettenkrad履带摩托","38式步枪","手枪与一发子弹","千户的日记","毛毯 x2","土豆干 x2","压缩口粮 x1"], "fixed_done": []}
        save_now()
        await interaction.response.edit_message(embed=discord.Embed(title="🔄 重新开始 0km 饥饿100%", color=0x8b9a7d), view=None)

class TradeView(discord.ui.View):
    def __init__(self, from_id, to_id=None, npc_name=None, inventory=None):
        super().__init__(timeout=120)
        self.from_id = from_id; self.to_id = to_id; self.npc_name = npc_name; self.offer = None
        inv = inventory or []
        if not inv: return
        _, counter = format_backpack(inv)
        unique = get_unique_for_trade(inv)
        opts = [discord.SelectOption(label=f"{item} (x{counter[item]})"[:100] if counter[item]>1 else item[:100], value=f"{idx}|{item}") for idx, item in enumerate(unique[:25])]
        self.select_give = discord.ui.Select(placeholder=f"选择物品 共{len(inv)}件", min_values=1, max_values=1, options=opts)
        self.select_give.callback = self.select_callback
        self.add_item(self.select_give)
    async def select_callback(self, interaction: discord.Interaction):
        if interaction.user.id != self.from_id: return
        _, item_name = self.select_give.values[0].split("|", 1)
        self.offer = item_name
        await interaction.response.send_message(f"已选择：**{self.offer}**", ephemeral=True)
    @discord.ui.button(label="确认交易", style=discord.ButtonStyle.success, emoji="🤝")
    async def confirm(self, interaction: discord.Interaction, button: discord.ui.Button):
        if interaction.user.id != self.from_id: return
        if not self.offer: return
        p = get_player(self.from_id)
        if self.offer not in p["inventory"]: return
        sync_item(p, self.offer, add=False)
        if self.npc_name:
            reward = roll(self.npc_name)
            p["inventory"].remove(self.offer); p["inventory"].append(reward); sync_item(p, reward, add=True)
            sp = SPECIAL_REWARDS.get(reward)
            if sp:
                if sp["effect"]=="fuel_full": p["fuel"]=999
                if sp["effect"]=="fuel+100": p["fuel"]+=100
                if sp["effect"]=="END": p["ended"]=True
            emb=discord.Embed(title=f"✨ {reward}", description=f"{SPECIAL_REWARDS[reward]['text']}\n\n{self.offer} -> {reward}\n现在 饥饿{p['hunger']}% 燃料{p['fuel']}", color=SPECIAL_REWARDS[reward]["color"] if reward in SPECIAL_REWARDS else ALL_NPCS[self.npc_name]["color"])
            if reward in SPECIAL_REWARDS and SPECIAL_REWARDS[reward].get("image"): emb.set_image(url=SPECIAL_REWARDS[reward]["image"])
            await interaction.response.edit_message(embed=emb, view=None)
        else:
            target = get_player(self.to_id); target["inventory"].append(self.offer); sync_item(target, self.offer, add=True); p["inventory"].remove(self.offer)
            await interaction.response.edit_message(embed=discord.Embed(title="交易完成"), view=None)
        save_now()

class GiveView(discord.ui.View):
    def __init__(self, user_id, inventory):
        super().__init__(timeout=120)
        self.user_id = user_id; self.offer=None
        unique = get_unique_for_trade(inventory)
        opts = [discord.SelectOption(label=item[:100], value=f"{idx}|{item}") for idx, item in enumerate(unique[:25])]
        self.select_give = discord.ui.Select(placeholder="选择要给予的物品", min_values=1, max_values=1, options=opts)
        self.select_give.callback = self.select_callback
        self.add_item(self.select_give)
    async def select_callback(self, interaction: discord.Interaction):
        if interaction.user.id != self.user_id: return
        _, item_name = self.select_give.values[0].split("|", 1)
        self.offer=item_name
        await interaction.response.send_message(f"已选择：**{self.offer}**", ephemeral=True)
    @discord.ui.button(label="确认给予", style=discord.ButtonStyle.success, emoji="🎁")
    async def confirm(self, interaction: discord.Interaction, button: discord.ui.Button):
        if interaction.user.id != self.user_id: return
        p = get_player(self.user_id)
        p["inventory"].append(self.offer); sync_item(p, self.offer, add=True)
        save_now()
        await interaction.response.edit_message(embed=discord.Embed(title="DEV给予成功", description=f"已获得 {self.offer}\n饥饿{p['hunger']}% 燃料{p['fuel']}", color=0xffd700), view=None)

@bot.event
async def on_ready():
    await bot.tree.sync()
    print(f"v27 3000终点 报废2550 | {len(bot.guilds)}服")

@bot.event
async def on_guild_join(guild: discord.Guild):
    me = guild.get_member(bot.user.id) or guild.me
    inviter = None
    try:
        if me and me.guild_permissions.view_audit_log:
            async for entry in guild.audit_logs(limit=10, action=discord.AuditLogAction.bot_add):
                if entry.target and entry.target.id == bot.user.id:
                    inviter = entry.user
                    break
    except:
        pass
    owner = guild.owner
    if owner is None:
        try:
            owner = await guild.fetch_member(guild.owner_id)
        except:
            try:
                owner = await bot.fetch_user(guild.owner_id)
            except:
                owner = None

    embed = discord.Embed(
        title="📮 Kettenkrad 已加入 - 少女终末旅行",
        description=(
            f"Kettenkrad已抵达 **{guild.name}**\n\n"
            f"**邀请者：** {inviter.mention if inviter else '未知'}\n"
            f"**群主：** {owner.mention if owner else f'<@{guild.owner_id}>'}\n\n"
            "**玩法：**\n"
            "`/步行` 开始3000km终末之旅 [每步-5%饥饿]\n"
            "`/背包` 查看物资 + 食物下拉\n"
            "`/交易` 与旅人交换\n"
            "`/无尽模式` 无尽荒野,永无终点\n\n"
            "⚠️ *仅私信邀请者和群主*"
        ),
        color=0x8b9a7d
    )
    embed.set_image(url="https://cdn.discordapp.com/attachments/1519326691095478272/1565415055162347540/images_29.jpg?ex=6ae4d1e1&is=6ae38061&hm=8b61159261b8b6b6bcc5b5e6a4b6097418f8001b6e34e888ba82f9015b0bcbd6&")
    embed.set_thumbnail(url="https://cdn.discordapp.com/attachments/1519326691095478272/1565415055661727785/-9lddQ5-j03nZ2mT3cSzk-k0.png?ex=6ae4d1e1&is=6ae38061&hm=bea045713b45be763978c01f283e2593de4cfd238c7b9cc1fd1036ca7098497e&")
    embed.set_footer(text=f"0km 饥饿度100% | 由 {inviter.display_name if inviter else '旅人'} 邀请")
    
    try:
        send_channel = guild.system_channel
        if not send_channel:
            for ch in guild.text_channels:
                if ch.permissions_for(me).send_messages:
                    send_channel = ch
                    break
        if send_channel:
            await send_channel.send(embed=embed)
    except:
        pass

    seen = set()
    dm_list = []
    for u in [inviter, owner]:
        if u and not u.bot and u.id not in seen:
            seen.add(u.id)
            dm_list.append(u)
    for user in dm_list:
        try:
            await user.send(embed=embed)
        except:
            pass

@bot.tree.command(name="开发者", description="开发者模式[仅限]")
async def 开发者(interaction: discord.Interaction):
    if interaction.user.id not in DEV_IDS: await interaction.response.send_message("❌ 不是开发者", ephemeral=True); return
    if interaction.user.id in dev_mode_users:
        dev_mode_users.remove(interaction.user.id); await interaction.response.send_message(embed=discord.Embed(title="DEV 已关闭", color=0xff0000))
    else:
        dev_mode_users.add(interaction.user.id); d=get_player(interaction.user.id); 
        for k in ALL_NPCS.keys(): d["met_npcs"].add(k); d["ever_met"].add(k); d["npc_met_km"][k]=d["km"]
        await interaction.response.send_message(embed=discord.Embed(title="DEV 已开启", color=0xffd700))
    save_now()

@bot.tree.command(name="跳跃", description="开发者跳跃")
async def 跳跃(interaction: discord.Interaction, km: int):
    if interaction.user.id not in dev_mode_users: await interaction.response.send_message("❌ 需先 /开发者", ephemeral=True); return
    d=get_player(interaction.user.id); d["km"]=km; d["step"]+=1; save_now()
    await interaction.response.send_message(embed=discord.Embed(title="DEV跳跃", description=f"已到 {km}km", color=0xffd700))

@bot.tree.command(name="给予", description="开发者给予")
async def 给予(interaction: discord.Interaction):
    if interaction.user.id not in dev_mode_users: await interaction.response.send_message("❌ 需先 /开发者", ephemeral=True); return
    await interaction.response.send_message(embed=discord.Embed(title="DEV给予"), view=GiveView(interaction.user.id, inventory=ALL_ITEMS_POOL), ephemeral=True)

@bot.tree.command(name="无尽模式", description="开启/关闭无尽模式")
async def 无尽模式(interaction: discord.Interaction):
    d = get_player(interaction.user.id)
    if not d.get("endless", False):
        await interaction.response.send_message(embed=discord.Embed(title="♾️ 开启无尽模式？", description="⚠️ 普通进度会消失\n确定开启无尽模式吗", color=0xff8800), view=EndlessConfirmView(interaction.user.id, True), ephemeral=True)
    else:
        await interaction.response.send_message(embed=discord.Embed(title="返回普通模式？", description="⚠️ 无尽进度会消失\n确定返回普通模式吗", color=0xff8800), view=EndlessConfirmView(interaction.user.id, False), ephemeral=True)

async def do_walk_logic(interaction: discord.Interaction):
    data = get_player(interaction.user.id)
    is_dev_now = interaction.user.id in dev_mode_users
    is_endless = data.get("endless", False)
    prev_km = data["km"]

    if data.get("ended") and not is_endless:
        embed = discord.Embed(title="—— 3000km，终点", description="......嗯。\n\n千户：我们现在这样，是正确的吗？\n尤莉：我们现在是世界上最幸福的人。\n—— 少女终末旅行 完", color=0x000000)
        embed.set_image(url="https://cdn.discordapp.com/attachments/1519326691095478272/1564967119534432256/images_32.jpg?ex=6ae48234&is=6ae330b4&hm=17b4fac59ef27fc216466ce7ee65840a018a7683934c58abbfd69aad81f54753&")
        await interaction.followup.send(embed=embed, view=RestartView(interaction.user.id))
        return

    if not is_endless:
        expired = []
        for npc_name in list(data["met_npcs"]):
            if npc_name in ["千户","尤莉"]: continue
            if data["km"] - data["npc_met_km"].get(npc_name, 0) > 15:
                data["met_npcs"].discard(npc_name); expired.append(npc_name)
        if expired and random.random() < 0.3:
            save_now()
            await interaction.followup.send(embed=discord.Embed(title=f"{expired[0]} 离开了", color=0x555555), view=WalkView(interaction.user.id))
            return

    data["step"] += 1
    has_bike = any(("Kettenkrad" in i or "履带摩托" in i) and "浴缸" not in i for i in data["inventory"])

    if data["step"] == 5 and not is_endless:
        save_now()
        embed = discord.Embed(title="📍 看到了夜晚的月光 ", description="尤莉：哇！是星空耶！\n千户：嗯！\n尤莉：快看那个星星！", color=0x8b9a7d)
        embed.set_image(url="https://cdn.discordapp.com/attachments/1519326691095478272/1565373186659328020/Screenshot_20261029_215400_com.android.chrome_edit_193629864750661.jpg?ex=6ae4aae2&is=6ae35962&hm=9ec2dd36a7f71b4441e19652001fb6827ba9ea8d667913e1f034ca10b3518e55&")
        await interaction.followup.send(embed=embed, view=WalkView(interaction.user.id))
        return

    if data.get("bath_to_delete", False) and not is_endless:
        data["bath_to_delete"] = False
        for i in range(len(data["inventory"])-1, -1, -1):
            if "Kettenkrad浴缸" in data["inventory"][i]:
                del data["inventory"][i]; break
        save_now()
        await interaction.followup.send(embed=discord.Embed(title="留在2550km", description="Kettenkrad浴缸留在了原地", color=0x555555), view=WalkView(interaction.user.id))
        return

    if is_endless:
        if not has_bike or data["fuel"] <= 0:
            move = random.randint(1, 2)
        else:
            move = random.randint(4, 7)
        data["km"] += move
    else:
        if not has_bike:
            if data.get("bike_scrapped"):
                move = random.randint(1, 3)
            else:
                move = random.randint(1, 2)
        elif data["fuel"] <= 0:
            move = random.randint(1, 2)
        else:
            move = random.randint(3, 6)
        data["km"] += move

    # 检查有没有到固定关卡
    prev_step = data["step"] - 1
    for story_id, story in FIXED_STORIES.items():
        if story_id in data.get("fixed_done", []):
            continue
        
        triggered = False
        if story.get("type") == "step":
            if prev_step < story["at"] <= data["step"]:
                triggered = True
        else: # type == "km"
            if prev_km < story["at"] <= data["km"]:
                triggered = True
        
        if triggered:
            embed = discord.Embed(
                title=f"{story['title']} [1/{len(story['pages'])}]",
                description=story["pages"][0],
                color=0x8b9a7d
            )
            if "images" in story and 0 in story["images"]:
                embed.set_image(url=story["images"][0])
            # 注意这里传 story_id，不是数字了
            await interaction.followup.send(embed=embed, view=FixedStoryView(interaction.user.id, story_id, 0))
            save_now()
            return

    if data["step"] <= 4:
        embed = discord.Embed(
            title="🚶‍♀️ 继续前进...",
            description=f"目前走了 {data['step']} 步 / {data['km']}km\n四周很安静，还没有遇到什么事。",
            color=0x8b9a7d
        )
        await interaction.followup.send(embed=embed, view=WalkView(interaction.user.id))
        save_now()
        return
    
    if data["step"] == 11 and not data["visited_airplane"] and not is_endless:
        data["visited_airplane"] = True
        data["inventory"].extend(["压缩口粮 x10", "生锈的仪表盘"]); save_now()
        embed = discord.Embed(title="📍 发现报废战斗机", description="尤莉：是飞机耶！\n千户：那是战斗机\n尤莉：诶...他还能飞吗\n千户：已经不能了....走，我们进去看有没有粮食\n获得：压缩口粮 x10 (+100%)", color=0x8b9a7d)
        embed.set_image(url="https://cdn.discordapp.com/attachments/1519326691095478272/1565001787013079181/Screenshot_20261028_215740.jpg?ex=6ae4a27e&is=6ae350fe&hm=132eeaa5e705c08425bc46743d5d843ada7fc3b882a2a06a4904b097c6ec8cdc&")
        await interaction.followup.send(embed=embed, view=WalkView(interaction.user.id)); return

    if not is_dev_now:
        if data["step"] > 10:
            data["hunger"] = max(0, data["hunger"] - 5)
        if data["fuel"] > 0:
            data["fuel"] = max(0, data["fuel"] - 1)
        if data["hunger"] <= 0:
            players[interaction.user.id] = {"km": 0, "hunger": 100, "fuel": 38 if is_endless else 28, "step": 0,"visited_airplane": False, "ended": False,"bike_scrapped": False, "bath_to_delete": False, "endless": is_endless, "pause_until":0,"met_npcs": set(["千户","尤莉","金泽","石像爷爷","石井","管制官","努可"]) if is_endless else set(["千户","尤莉"]),"ever_met": set(["千户","尤莉","金泽","石像爷爷","石井","管制官","努可"]) if is_endless else set(["千户","尤莉"]),"npc_met_km": {"千户":0,"尤莉":0},"inventory": ["Kettenkrad履带摩托","38式步枪","手枪与一发子弹","毛毯 x2"] if is_endless else ["Kettenkrad履带摩托","38式步枪","手枪与一发子弹","千户的日记","毛毯 x2","土豆干 x2","压缩口粮 x1"], "fixed_done": []}
            save_now()
            await interaction.followup.send(embed=discord.Embed(title="💀 饿死了...", description=f"饥饿度0%倒下... 已重置 饥饿100% / 0km", color=0x000000), view=WalkView(interaction.user.id))
            return

    if not is_endless and prev_km < 1650 <= data["km"]:
        save_now(); await interaction.followup.send(embed=discord.Embed(title="⚠️ 进入中层 - 1650km", description="你已进入中层，接下来食物与燃料不会频繁出现了", color=0xff8800), view=WalkView(interaction.user.id)); return
    if not is_endless and prev_km < 2250 <= data["km"]:
        save_now(); await interaction.followup.send(embed=discord.Embed(title="☠️ 进入上层 - 2250km", description="你已进入上层了，接下来将不会再生成食物与燃料了", color=0x111111), view=WalkView(interaction.user.id)); return

    if not is_endless and not data.get("bike_scrapped", False) and prev_km < 2550 <= data["km"]:
        data["bike_scrapped"] = True; data["bath_to_delete"] = True
        for i in range(len(data["inventory"])-1, -1, -1):
            if ("Kettenkrad" in data["inventory"][i] or "履带摩托" in data["inventory"][i]) and "浴缸" not in data["inventory"][i]:
                del data["inventory"][i]; break
        data["inventory"].append("Kettenkrad浴缸"); save_now()
        embed = discord.Embed(
            title="💥 Kettenkrad 报废 - 2550km",
            description=(
                "嘎吱...碎。\n\n"
                "千户：...不动了。\n"
                "尤莉：修一下就好了吧？\n"
                "千户：...履带断了，引擎也烧死了。修不了了。\n"
                "尤莉：...\n\n"
                "千户：它陪我们走了2550km啊...\n"
                "尤莉：一直以为...它会陪我们到上层的...\n\n"
                "沉默了很久。\n\n"
                "尤莉：千户...我们把它当浴缸吧。\n"
                "尤莉：这样...它还能再陪我们一下。\n"
                "千户：嗯。\n\n"
                "热水倒进Kettenkrad的车斗里。\n"
                "呜啊——\n\n"
                "尤莉：最后的热水澡啊...\n"
                "千户：明明这么暖和...为什么有点想哭。\n\n"
                "—— Kettenkrad报废了\n"
                "获得：Kettenkrad浴缸\n"
                "下一次步行后，浴缸会留在原地。"
            ),
            color=0x555555
        )
        embed.set_image(url="https://cdn.discordapp.com/attachments/1519326691095478272/1565030660282912889/082.jpg.webp?ex=6ae414a2&is=6ae2c322&hm=e31e3f5b77f36334ba75bec96e4e0fa23c0c1057623cb57ee1cf688810f93622&")
        await interaction.followup.send(embed=embed, view=WalkView(interaction.user.id))
        return

    if not is_endless and data["km"] >= 3000 and not data["ended"]:
    # 1% 隐藏结局
    if random.random() < 1.00:
        data["km"] = 3000
        data["ended"] = True
        save_now()
        embed = discord.Embed(
            title="—— 3000km，隐藏结局 - 稻田 ",
            description=(
                "尤莉：千户！这里是......?\n"
                "千户：诶？稻田？\n\n"
                "在望不到头的稻田上，还有一个正方形的石头\n"
                "不是无尽的虚无，也没有寒冷的雪，取而代替的是一个由大量稻米组成的稻田\n\n"
                "千户：竟然是...稻米！太好了！\n"
                "尤莉：千户，我们是不是有吃不完的食物了\n"
                "千户：嗯，是的....\n\n"
                "—— 1% 隐藏结局触发\n\n"
                "(注意：这个隐藏结局是游戏作者自己加入的，跟原作毫无相关。)"
            ),
            color=0xFFD700
        )
        embed.set_image(url="")
        await interaction.followup.send(embed=embed, view=RestartView(interaction.user.id))
        return

    # 原本的普通结局
    data["km"] = 3000
    data["ended"] = True; save_now()
    embed = discord.Embed(
        title="—— 3000km，虚无的上层",
        description="......嗯。\n\n千户：我们现在这样，是正确的吗？\n尤莉：我们现在是世界上最幸福的人。\n—— 少女终末旅行 完",
        color=0x000000
    )
    embed.set_image(url="https://cdn.discordapp.com/attachments/1519326691095478272/1564967119534432256/images_32.jpg?ex=6ae48234&is=6ae330b4&hm=17b4fac59ef27fc216466ce7ee65840a018a7683934c58abbfd69aad81f54753&")
    await interaction.followup.send(embed=embed, view=RestartView(interaction.user.id))
    return

    if is_endless:
        last_150 = (prev_km // 150) * 150
        curr_150 = (data["km"] // 150) * 150
        if curr_150 > last_150 and curr_150 > 0:
            save_now(); await interaction.followup.send(embed=discord.Embed(title=f"♾️ 无尽 {curr_150}km", description=f"饥饿{data['hunger']}% 燃料{data['fuel']} +{move}km", color=0x00ffaa), view=WalkView(interaction.user.id)); return

    if not is_endless:
        force_met = []
        for name, nd in ALL_NPCS.items():
            if name in ["上层的幽灵","千户","尤莉"]: continue
            if name not in data["met_npcs"] and name not in data.get("ever_met", set()) and data["km"] >= nd["km_need"]:
                data["met_npcs"].add(name); data["ever_met"].add(name); data["npc_met_km"][name]=data["km"]; force_met.append(name)
        if force_met:
            name = force_met[0]; save_now()
            await interaction.followup.send(embed=discord.Embed(title=f"📍 遇到了 {name} - {data['km']}km", description=NPC_DIALOGUE.get(name,"") + f"\n15km内可 /交易 {name}", color=ALL_NPCS[name]["color"]), view=WalkView(interaction.user.id)); return

    if data["km"] < 1650:
        roll_type = random.choices(["空空", "食物", "杂物"], weights=[30, 45, 25])[0]
    else:
        roll_type = random.choices(["空空", "食物", "杂物"], weights=[45, 35, 20])[0]

    if roll_type == "空空":
        save_now()
        embed = discord.Embed(title="空空", description=random.choice(["什么都没有...","风声..."]), color=0x555555)
        embed.set_author(name=f"{'♾️' if is_endless else ''}{data['km']}km | 饥饿{data['hunger']}% 燃料{data['fuel']} +{move}km")
        await interaction.followup.send(embed=embed, view=WalkView(interaction.user.id)); return

    if roll_type == "食物":
        if data["km"] >= 2250 and not is_dev_now and not is_endless:
            save_now(); await interaction.followup.send(embed=discord.Embed(title="空空", description="上层什么都没有...", color=0x555555), view=WalkView(interaction.user.id)); return
        food_item = random.choice(["压缩口粮 x1", "土豆干 x2", "压缩口粮 x10", "军用口粮 x10"]) if random.random() < 0.6 else random.choice(["燃料桶(半满)", "燃料桶 x20"])
        data["inventory"].append(food_item)
        if get_fuel_value(food_item): data["fuel"] += get_fuel_value(food_item)
        save_now()
        embed = discord.Embed(title="🍙 找到食物！" if get_food_value(food_item) else "⛽ 找到燃料！", description=f"获得 {food_item}\n饥饿{data['hunger']}% 燃料{data['fuel']}", color=0x8b9a7d)
        embed.set_author(name=f"{'♾️' if is_endless else ''}{data['km']}km | 饥饿{data['hunger']}% 燃料{data['fuel']} +{move}km")
        await interaction.followup.send(embed=embed, view=WalkView(interaction.user.id)); return

    if roll_type == "杂物":
        item, weight, dialogue = random.choice(RANDOM_LOOT)
        data["inventory"].append(item); save_now()
        embed = discord.Embed(title="🔧 找到杂物", description=f"获得 {item}\n\n{dialogue}", color=0x666666)
        embed.set_author(name=f"{'♾️' if is_endless else ''}{data['km']}km | 饥饿{data['hunger']}% 燃料{data['fuel']} +{move}km")
        await interaction.followup.send(embed=embed, view=WalkView(interaction.user.id)); return

@bot.tree.command(name="步行", description="步行3000km到上层")
async def 步行(interaction: discord.Interaction):
    await interaction.response.defer(ephemeral=False)
    await do_walk_logic(interaction)

@bot.tree.command(name="背包", description="查看背包")
async def 背包(interaction: discord.Interaction):
    d=get_player(interaction.user.id)
    lines, _ = format_backpack(d["inventory"])
    text = "\n".join(lines) if lines else "空空如也"
    embed = discord.Embed(title=f"{'♾️ 无尽 ' if d.get('endless') else ''}{d['km']}km 背包 - {d['hunger']}%饥饿 {d['fuel']}燃料", description=text, color=0x00ffaa if d.get('endless') else 0x8b9a7d)
    await interaction.response.send_message(embed=embed, view=WalkView(interaction.user.id))

@bot.tree.command(name="交易", description="与NPC或玩家交易")
@discord.app_commands.choices(npc=[discord.app_commands.Choice(name=k, value=k) for k in ALL_NPCS.keys()])
async def 交易(interaction: discord.Interaction, 用户: discord.Member=None, npc: str=None):
    await interaction.response.defer(ephemeral=True)
    d=get_player(interaction.user.id)
    if npc:
        if interaction.user.id not in dev_mode_users and npc not in d["met_npcs"]:
            await interaction.followup.send(f"❌ 还没遇到 {npc}", ephemeral=True); return
        view = TradeView(interaction.user.id, npc_name=npc, inventory=d["inventory"])
        await interaction.followup.send(embed=discord.Embed(title=f"与 {npc} 交易"), view=view, ephemeral=True)
    else:
        if not 用户: await interaction.followup.send("❌ 请@玩家或选NPC", ephemeral=True); return
        view = TradeView(interaction.user.id, to_id=用户.id, inventory=d["inventory"])
        await interaction.followup.send(embed=discord.Embed(title=f"与 {用户.display_name} 交易"), view=view, ephemeral=True)

threading.Thread(target=run_flask, daemon=True).start()
bot.run(os.getenv("DISCORD_TOKEN"))
