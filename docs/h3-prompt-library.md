# MiniMax H3 提示词参考库

> 适用面板:H3 Studio( http://127.0.0.1:8188/h3-studio )
> 模型:FL2VA pruned INT8 | 采样:双时钟 8 步(抽卡)/ 20 步(精修)
> 提示词语言:英文效果最佳;中文可用但偶有嘴瓢,对白建议英文(`<d>[English]...</d>`)

---

## 0. I2VA 提示词黄金法则(图生视频)

1. **开头固定引用首帧**:`For the target video, at 0.00 seconds into the target video, <Picture 1> (from [Shot 1]) is fully referenced.` —— 官方复现案例的标准写法,锁死首帧画面。
2. **锁身份**:明确写 `Keep the person's appearance/identity exactly as in <Picture 1>`(发型/服装/五官不改变),否则 2-3 秒后可能漂移。
3. **三段式结构**:动作时序 → 运镜 → 声音(环境声/动作声/对白/音乐)。
4. **首帧图选图建议**:中近景、顺光或侧逆光、表情明确、背景不过于杂乱 → 出片可控性最高;全身远景人脸信息少,后续会糊。
5. **时长建议**:单动作 5s;多拍子叙事 10s;循环/转场 15s。

---

## 1. I2VA 人物写实 · 动作与场景库(16 条)

### A. 单人基础动作(5 秒)

**A1 回头微笑(街角逆光)**
- 首帧建议:女/男中近景,侧身,表情平静,背景虚化街景
- 中文:首帧中的人物保持长相与服装不变,身体缓缓转向镜头,目光从远处收回,嘴角浮现自然的微笑,发丝在逆光中泛光,镜头轻微推近。声音:街道远处车流、微风、极轻的脚步,无音乐。
- EN: `For the target video, at 0.00 seconds into the target video, <Picture 1> (from [Shot 1]) is fully referenced. Keep the person's appearance and clothing exactly as in <Picture 1>. The person slowly turns the body toward the camera, eyes refocusing from the distance, a natural smile forming, hair glowing in the backlight, camera gently pushing in. Sound: distant traffic, light wind, faint footsteps, no music.`

**A2 挥手告别(月台/街边)**
- 首帧建议:人物正面中景,手臂自然下垂,背景开阔
- 中文:人物保持首帧外貌,抬手向镜头方向轻轻挥动两次,嘴唇微动仿佛在说"再见",随后转身缓步走远,镜头固定。声音:远处列车声/城市底噪,一声短促的 "Goodbye",无音乐。
- EN: `... The person raises a hand and waves twice gently toward the camera, lips moving as if saying goodbye, then turns and walks slowly away, camera static. Sound: distant train/city ambience, one soft "Goodbye", no music.`

**A3 喝咖啡(咖啡馆窗边)**
- 首帧建议:人物坐在窗边,面前有咖啡杯,侧光
- 中文:人物保持首帧外貌与坐姿,端起咖啡杯小口啜饮,放下杯子望向窗外,指尖轻敲桌面,镜头缓慢横移。声音:咖啡馆环境人声低语、杯碟轻碰、蒸汽声,无音乐。
- EN: `... The person picks up the coffee cup, takes a small sip, sets it down, gazes out the window, fingers tapping the table lightly, camera slowly panning. Sound: soft cafe murmur, cups and saucers clinking, gentle steam, no music.`

**A4 看书抬眸(暖光卧室)**
- 首帧建议:人物侧坐持书,暖色台灯光
- 中文:人物保持首帧姿态,翻过一页书,忽然抬眸看向镜头方向,眼神微动,书页在指间停住,镜头缓慢推近至面部特写。声音:翻页声、窗外细雨,无音乐。
- EN: `... The person turns a page, then suddenly looks up toward the camera, a subtle expression shift, the page pausing between fingers, camera slowly pushing to a close-up. Sound: page turning, soft rain outside, no music.`

**A5 撑伞行走(雨中街)**
- 首帧建议:人物持伞全身/中景,雨天背景
- 中文:人物保持首帧外貌与伞,在雨中沿街道缓步前行,雨滴在伞面弹落,路过积水时倒影晃动,镜头跟拍平移。声音:雨声、脚步踩水声、远处车流,无音乐。
- EN: `... The person walks slowly along the rainy street, raindrops bouncing off the umbrella, reflections rippling in puddles, camera tracking sideways. Sound: rain, footsteps splashing, distant traffic, no music.`

### B. 单人场景叙事(10 秒)

**B1 海边日落回眸**
- 首帧建议:海边人物背影或侧影,夕阳暖光
- 中文:人物站在浅滩,海浪轻拍脚踝,她/他抬手拢了拢被风吹乱的头发,回眸看向镜头,眼神温柔,身后夕阳沉入海平线,镜头缓慢环绕半圈。声音:海浪声、海风、远处海鸥,无音乐。
- EN: `... The person stands at the waterline, waves lapping at the ankles, tucks wind-blown hair behind the ear, looks back toward the camera with a gentle gaze as the sun sets behind, camera slowly orbiting halfway around. Sound: waves, sea wind, distant seagulls, no music.`

**B2 雪中哈气搓手**
- 首帧建议:人物冬季着装中景,雪景背景
- 中文:人物站在飘雪的街道,呵出一口白气,双手合拢搓了搓,跺了跺脚,雪花落在肩头与睫毛上,镜头缓慢推近。声音:雪地脚步咯吱声、寒风、极轻的呼气声,无音乐。
- EN: `... The person exhales a visible breath, rubs the gloved hands together, stamps the feet lightly, snowflakes settling on the shoulders and lashes, camera slowly pushing in. Sound: crunching snow footsteps, cold wind, a soft exhale, no music.`

**B3 霓虹夜街漫步**
- 首帧建议:人物夜景中景,身后霓虹招牌虚化
- 中文:人物在霓虹闪烁的夜街缓步前行,路过橱窗时停步看了一眼倒影,又继续走,彩色灯光在脸上流转,镜头跟随平移。声音:城市夜噪、远处音乐片段、脚步,无对白。
- EN: `... The person walks through the neon-lit night street, pauses at a shop window to glance at the reflection, then continues, colored lights drifting across the face, camera tracking. Sound: city night ambience, distant music snippets, footsteps, no dialogue.`

**B4 办公室窗前发呆**
- 首帧建议:人物坐窗边,电脑/办公桌元素,窗外黄昏
- 中文:人物坐在窗边,视线从电脑屏幕移向窗外黄昏,指尖无意识转笔,轻轻叹气,拿起水杯喝了一口,镜头缓慢推近侧脸。声音:键盘敲击声渐弱、空调低鸣、窗外城市底噪,无音乐。
- EN: `... The person shifts gaze from the screen to the dusk outside, idly spinning a pen, a soft sigh, takes a sip of water, camera slowly pushing toward the profile. Sound: fading keyboard clicks, low AC hum, distant city ambience, no music.`

**B5 花园浇花**
- 首帧建议:人物花园中景,手持水壶,绿植环绕,晨光
- 中文:人物在晨光花园中给花浇水,水珠在叶片上滚动,俯身闻了闻花,直起身对镜头方向浅浅一笑,镜头缓慢横移。声音:水洒细响、鸟鸣、微风,无音乐。
- EN: `... The person waters the flowers in the morning garden, droplets rolling on leaves, bends to smell a bloom, straightens and gives a faint smile toward the camera, camera slowly panning. Sound: gentle watering, birdsong, breeze, no music.`

**B6 街边等车**
- 首帧建议:人物站路边中景,公交站/街景,白天或黄昏
- 中文:人物在站台等车,低头看了看手机,抬头望向来车方向,风掀起衣角,车辆从身边驶过带起气流,镜头固定。声音:车流声、风声、手机提示音,无音乐。
- EN: `... The person waits at the stop, glances at the phone, looks up toward the incoming traffic, wind lifting the hem of the coat, a bus passing with a gust, camera static. Sound: traffic, wind, a phone chime, no music.`

### C. 双人互动(10 秒)

**C1 咖啡馆对谈**
- 首帧建议:两人对坐中景,桌面有咖啡,暖光
- 中文:保持首帧两人外貌不变,右侧人物说话时双手比划,左侧人物认真倾听并点头微笑,偶尔插话,窗外光线随时间微变,镜头缓慢推近。声音:两人低语对话、咖啡馆环境声、杯碟轻响,配轻柔爵士乐。
- EN: `... Keep both persons' appearance as in <Picture 1>. The person on the right speaks with expressive gestures, the person on the left listens and nods with a smile, occasionally replying; the light outside shifts subtly, camera slowly pushing in. Sound: soft conversation, cafe ambience, gentle jazz.`

**C2 公园牵手散步**
- 首帧建议:两人并排背影/侧面,林荫道,秋季或春季
- 中文:两人牵手沿林荫道缓步而行,其中一人侧头看向另一人说了句话,两人相视而笑,落叶从镜头前飘过,镜头跟拍。声音:脚步、落叶沙沙、鸟鸣、两人轻笑,轻快木吉他。
- EN: `... The two walk hand in hand along the tree-lined path; one turns the head to say something, both laugh softly as leaves drift past the lens, camera tracking. Sound: footsteps, rustling leaves, birdsong, soft laughter, light acoustic guitar.`

**C3 机场重逢拥抱**
- 首帧建议:两人距离数米对视,行李/到达口背景
- 中文:保持两人外貌不变,其中一人快步上前,另一人张开双臂,两人在镜头前相拥,情绪激动,行李车停在旁边,镜头缓慢推近。声音:机场广播底噪、脚步加快、拥抱时衣物摩擦与哽咽,弦乐渐起。
- EN: `... One person walks up quickly, the other opens the arms wide, they embrace in front of the camera, emotional; luggage cart beside them, camera slowly pushing in. Sound: airport PA ambience, quickening footsteps, fabric rustle and a choked voice, strings swelling.`

### D. 特殊拍法(5-10 秒)

**D1 自拍 vlog 对镜说话**
- 首帧建议:人物手持手机自拍视角,面部清晰居中
- 中文:保持首帧自拍视角与人物外貌,人物对镜头自然说话,语速适中,偶尔抬手整理头发,背景轻微晃动体现手持感,镜头即手机视角。声音:人物清晰对白 <d>[English] Hi everyone, today I want to share something special with you.</d> 与轻微环境声。
- EN: `... Keep the selfie perspective and appearance from <Picture 1>; the person talks naturally to the camera at a moderate pace, occasionally fixing the hair, subtle handheld shake. Sound: clear dialogue <d>[English] Hi everyone, today I want to share something special with you.</d> with light ambience.`

**D2 慢动作回眸甩发**
- 首帧建议:人物侧面中近景,发丝清晰,逆光或自然光
- 中文:慢动作镜头,人物猛地回眸,发丝在空中划过弧线,眼神直视镜头,背景虚化成光斑,时间流速放慢,镜头固定。声音:慢动作下放慢的环境声,风声,无音乐。
- EN: `... Slow-motion shot: the person turns the head sharply, hair arcing through the air, eyes locking on the camera, background blurring into bokeh, time slowed, camera static. Sound: slowed ambience, wind, no music.`

**D3 特写微表情变化(表演向)**
- 首帧建议:面部特写,表情平静,眼神有光,顺光
- 中文:保持首帧面部特写构图,人物眼神从平静到湿润,嘴角轻微颤抖,一滴泪滑落,又努力挤出一个微笑,睫毛颤动,镜头极缓推近。声音:极轻的呼吸声、环境静默,钢琴单音,无对白。
- EN: `... Keep the close-up composition; the eyes grow moist, the lips tremble slightly, a single tear rolls down, then a forced smile forms, lashes quivering, camera pushing in extremely slowly. Sound: faint breathing, silence, a lone piano note, no dialogue.`

**D4 镜头前递物(互动向)**
- 首帧建议:人物手持一件物品(花/信封/杯子)中景,看向镜头
- 中文:人物保持首帧外貌与手持物品,将物品缓缓递向镜头方向,仿佛要交到观众手里,另一只手轻轻推出,镜头配合前移,画面在物品特写处结束。声音:衣物摩擦、轻微呼吸,温暖弦乐。
- EN: `... The person slowly extends the object toward the camera as if handing it to the viewer, the other hand pushing gently forward, camera moving in with the gesture, ending on a close-up of the object. Sound: fabric rustle, soft breathing, warm strings.`

---

## 2. 基础场景库(其他 7 大类,每类 1 条示例)

**产品展示(商业)** — 适用 I2VA(传商品图)
- 中:保持 <Picture 1> 中产品形状与材质,镜头环绕 180 度,金属高光流转,背景虚化渐变。声音:轻快产品氛围音乐,柔和节拍,无对白。
- EN: `Keep the exact product from <Picture 1> unchanged in shape and material; the camera orbits 180 degrees, metallic highlights gliding, blurred gradient background. Sound: light upbeat product ambience, soft beat, no dialogue.`

**自然风景(星空延时)** — 适用 T2VA,推荐 10s
- 中:广角固定机位,银河缓缓旋转,流星划过,前景山脊剪影,薄云流动,延时感。声音:夜风、远处虫鸣、极轻弦乐。
- EN: `Wide static shot, the Milky Way slowly rotates, a meteor streaks across, foreground mountain ridge silhouetted, thin clouds drifting, timelapse feel. Sound: night wind, faint insects, very light strings.`

**城市空间(霓虹雨夜)** — 适用 T2VA
- 中:雨夜霓虹街道,湿润路面倒映彩色灯光,行人撑伞穿行,镜头低机位跟随,汽车驶过溅起水花。声音:雨声、车流、远处城市嗡鸣,电子氛围乐。
- EN: `Rainy neon street at night, wet pavement mirroring colored lights, pedestrians with umbrellas crossing, low-angle tracking shot, a car splashing by. Sound: rain, traffic, distant city hum, electronic ambience.`

**风格化(水墨)** — 适用 T2VA/I2VA
- 中:水墨风格动画,墨色在宣纸上晕开,山峦与飞鸟由淡转浓,笔触流动,留白构图。声音:古琴拨弦、毛笔落纸声,极简。
- EN: `Ink-wash animation style, ink blooming on rice paper, mountains and birds emerging from faint to bold, flowing brushstrokes, negative space composition. Sound: guqin plucks, brush on paper, minimal.`

**电影叙事(太空)** — 适用 T2VA,推荐 10s
- 中:太空船舰桥,女舰长背对镜头立于观景窗前,窗外舰队引擎逐渐亮起蓝光,她缓缓转身,表情凝重,镜头缓慢推近。声音:舰桥低频嗡鸣、引擎蓄能渐强、金属结构微响,太空歌剧配乐。
- EN: `Starship bridge, the female captain standing with her back to the camera before the observation window, the fleet's engines glowing brighter blue outside, she turns slowly with a grave expression, camera pushing in. Sound: low bridge hum, engines charging, faint metal creaks, space-opera score.`

**动物(猫)** — 适用 I2VA(传猫图)
- 中:保持首帧中猫咪的外貌,猫咪从窗台缓缓站起,伸了个懒腰,跳下窗台,落地后回头看了一眼,镜头跟随。声音:轻巧落地声、呼噜声、窗外鸟鸣,无音乐。
- EN: `Keep the cat's appearance as in <Picture 1>; the cat stands up slowly on the windowsill, stretches, jumps down, lands softly, glances back once, camera following. Sound: soft landing, purring, birds outside, no music.`

**技法专项(循环动画)** — 适用 FL2VA(首尾同图)
- 中:<Picture 1> 与 <Picture 2> 为同一画面,生成无缝循环:人物挥手动作在 5 秒内完成并精确回到起始姿态,边界无跳变。声音:循环的环境风与极轻旋律。
- EN: `<Picture 1> and <Picture 2> are identical; generate a seamless loop: the waving motion completes and returns exactly to the start pose within the clip, no boundary jump. Sound: looping wind ambience with a faint motif.`

---

## 3. 声音与对白速查

| 需求 | 写法 |
|---|---|
| 环境声 | `Sound: street ambience, distant traffic, light wind, no music.` |
| 对白(英文,最稳) | `<d>[English] Hi everyone, ...</d>` 放在画面描述后 |
| 对白(中文,偶有嘴瓢) | `<d>[Chinese] 大家好,今天...</d>` 或直接写中文对白,多试几次 |
| 音乐 | `non-diegetic music: 风格+节奏,如 soft acoustic guitar, slow tempo` |
| 完全静音 | `Sound: silent, no audio.`(或面板音频选"静音") |

## 4. 参数建议

| 场景 | 时长 | 步数 |
|---|---|---|
| 单动作(回头/挥手) | 5s | 8(抽卡)/20(精修) |
| 场景叙事(海边/雪中) | 10s | 12-20 |
| 双人互动/对白 | 10s | 20(对白质量最稳) |
| 循环/转场 | 15s | 20 |
