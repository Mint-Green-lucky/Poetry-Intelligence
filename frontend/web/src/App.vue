<!--
© 2026 BUPT_Mint-Green
All rights reserved.
-->

<script setup lang="ts">
// @ts-nocheck
import { computed, nextTick, onMounted, onUnmounted, ref, watch } from "vue";
import * as echarts from "echarts";

const tasks = {
  chat: {
    icon: "问",
    name: "知识问答",
    title: "知识问答",
    badge: "知识问答",
    desc: "释义 · 格律 · 意象 · 手法",
    placeholder: "请输入一个明确的诗词知识问题",
    contract: "直接回答 / 原句依据 / 专属知识点",
  },
  generate: {
    icon: "写",
    name: "灵感创作",
    title: "灵感创作",
    badge: "灵感创作",
    desc: "体裁 · 主题 · 情感",
    placeholder: "请输入创作主题、场景或意象要求",
    contract: "题目 / 完整诗作 / 简短创作说明",
  },
  review: {
    icon: "改",
    name: "诗作批改",
    title: "诗作批改",
    badge: "诗作批改",
    desc: "逐句问题 · 建议句 · 修改稿",
    placeholder: "粘贴你的原创诗词并说明希望修改的重点",
    contract: "体裁检查 / 逐句批改 / 完整修改稿 / 修改说明",
  },
  appreciate: {
    icon: "赏",
    name: "诗词赏析",
    title: "诗词赏析",
    badge: "诗词赏析",
    desc: "原句细读 · 情感推进 · 手法效果",
    placeholder: "输入需要赏析的诗词原文",
    contract: "诗境概括 / 原句细读 / 情感推进 / 手法效果",
  },
  recite: {
    icon: "诵",
    name: "背诵默写",
    title: "背诵默写",
    badge: "背诵默写",
    desc: "核准原文 · 意群记忆 · 默写练习",
    placeholder: "输入篇名、作者或诗句，生成背诵默写训练",
    contract: "篇目信息 / 准确原文 / 意群记忆 / 默写 / 答案",
  },
  compare: {
    icon: "比",
    name: "诗歌比较",
    title: "诗歌比较",
    badge: "诗歌比较",
    desc: "双方原句 · 逐维异同 · 核心结论",
    placeholder: "请输入两首诗词，并说明希望比较的角度",
    contract: "比较对象 / 逐维对照 / 核心异同",
  },
  expand: {
    icon: "展",
    name: "扩展训练",
    title: "扩展训练",
    badge: "只负责出题训练",
    desc: "题型 · 难度 · 答案 · 评分点",
    placeholder: "输入诗词或知识点，生成专项训练",
    contract: "训练说明 / 题目 / 参考答案 / 评分要点",
  },
};

const task = ref("chat");
const query = ref("");
const poem = ref("");
const form = ref("不限");
const emotion = ref("");
const genreExtension = ref("");
const emotionExtension = ref("");
const themes = ref([]);
const genreGroups = {
  楚辞骚体: ["《离骚》体", "九章", "九歌"],
  汉乐府古体: ["相和歌", "鼓吹曲", "杂曲歌辞"],
  五言古诗: ["魏晋五言", "唐代五言古风"],
  七言古诗: ["盛唐七言歌行", "柏梁体"],
  杂言歌行: ["长短杂言", "乐府歌行"],
  五言绝句: ["标准五绝", "古绝"],
  七言绝句: ["标准七绝", "古绝"],
  五言律诗: ["标准五律", "限定平仄五律"],
  七言律诗: ["标准七律", "拗体七律"],
  排律: ["五言排律", "七言排律"],
  小令词牌: ["如梦令", "浣溪沙", "清平乐", "忆江南", "西江月", "采桑子", "生查子", "菩萨蛮"],
  中调词牌: ["蝶恋花", "渔家傲", "江城子", "一剪梅", "青玉案", "鹊桥仙", "苏幕遮", "临江仙", "定风波"],
  长调词牌: ["水调歌头", "满江红", "念奴娇", "声声慢", "雨霖铃", "永遇乐", "沁园春", "扬州慢", "八声甘州", "贺新郎"],
  元曲小令: ["天净沙", "山坡羊", "四块玉"],
  元曲套曲: ["杂剧唱词", "散套组曲"],
  现代短诗: ["白话短诗", "自由小诗"],
  散文诗: ["抒情散文诗", "叙事散文诗"],
};
const genreFilterGroups = {
  先秦楚辞: ["楚辞骚体", "离骚体", "九歌体", "九章体", "天问体", "招魂体"],
  汉魏古体: ["汉乐府", "相和歌辞", "鼓吹曲辞", "五言古诗", "七言古诗", "杂言歌行", "柏梁体"],
  唐诗: ["五言绝句", "七言绝句", "五言律诗", "七言律诗", "五言排律", "七言排律", "五言古风", "七言歌行", "乐府歌行"],
  宋词: ["如梦令", "忆江南", "浣溪沙", "清平乐", "采桑子", "菩萨蛮", "西江月", "生查子", "卜算子", "临江仙", "蝶恋花", "渔家傲", "江城子", "一剪梅", "青玉案", "鹊桥仙", "苏幕遮", "定风波", "水调歌头", "满江红", "念奴娇", "声声慢", "雨霖铃", "永遇乐", "沁园春", "扬州慢", "八声甘州", "贺新郎"],
  元代散曲: ["天净沙", "山坡羊", "四块玉", "沉醉东风", "水仙子", "折桂令", "双调小令", "中吕小令", "越调小令", "元曲套曲", "杂剧唱词"],
  明清诗词: ["五言绝句", "七言绝句", "五言律诗", "七言律诗", "仿古乐府", "古风歌行", "小令词", "中调词", "长调词"],
  近现代诗文: ["现代格律诗", "现代短诗", "自由诗", "散文诗", "十四行诗", "叙事长诗"],
};
const emotionGroups = {
  昂扬豪迈: ["豪放昂扬", "慷慨激昂", "爱国豪情", "浪漫飘逸", "雄浑壮阔", "激越奋发"],
  沉郁悲怆: ["沉郁顿挫", "苍凉悲壮", "忧愤深沉", "悲怆哀痛", "感时伤乱", "悲悯厚重"],
  婉约哀思: ["婉约含蓄", "哀怨凄婉", "孤寂落寞", "思念眷恋", "离愁别绪", "悼亡追怀", "惆怅迷离"],
  清新冲淡: ["清新自然", "闲适冲淡", "平和悠远", "隐逸旷达", "明快活泼", "空灵澄澈", "淡泊宁静"],
  幽思哲理: ["怀古幽思", "深沉哲思", "物我玄思", "旷达超然", "幽默诙谐", "讽喻冷峻"],
  温暖明丽: ["温柔缱绻", "欣喜明快", "真挚亲情", "深厚友情", "希望憧憬", "欢聚酣畅"],
};
const themeGroups = {
  山水田园: ["山居田园", "江河湖海", "名山胜景", "渔樵生活"],
  边塞征战: ["大漠戍边", "军旅征战", "塞外风光", "反战思归"],
  咏史怀古: ["古迹兴亡", "历史人物", "借古讽今", "王朝盛衰"],
  送别赠别: ["折柳饯行", "江亭送别", "赠友唱和", "惜别祝愿"],
  思乡怀人: ["羁旅怀乡", "游子思亲", "闺中怀远", "故园追忆"],
  爱情闺怨: ["相思闺情", "爱情盟誓", "婚恋离合", "宫怨幽思"],
  咏物言志: ["托物寄志", "梅兰竹菊", "禽鸟虫鱼", "器物寓意"],
  饮酒抒怀: ["酒中抒情", "宴饮酬唱", "醉后旷达", "借酒浇愁"],
  登临感怀: ["登楼临水", "凭栏远眺", "登高怀古", "旅途所见"],
  家国现实: ["家国民生", "忧国忧民", "报国立志", "讽喻时政"],
  隐逸闲适: ["归隐林泉", "农事日常", "禅意清修", "闲居自适"],
  人生哲思: ["生命哲理", "岁月无常", "理想求索", "物我思辨"],
  四时风物: ["春日芳景", "夏夜荷风", "秋声落叶", "冬雪寒梅"],
  月夜星河: ["望月怀远", "月下独酌", "星河夜航", "中秋团圆"],
  友情亲情: ["赠友唱和", "手足亲情", "慈母游子", "故人重逢"],
  悼亡怀旧: ["追悼忆旧", "故人追怀", "旧地重游", "往事今昔"],
  都市现代: ["城市夜景", "校园青春", "科技未来", "时代新声"],
  神话想象: ["仙侠奇境", "神话新编", "宇宙星海", "志怪传奇"],
};
const selectedGenreGroup = ref("不限");
const selectedEmotionGroup = ref("不限");
const selectedThemeGroup = ref("不限");
const themeDetail = ref("");
const openFilter = ref("");
const expandedPoetEra = ref("");
const poetGroups = {
  先秦: ["屈原", "宋玉"],
  汉魏: ["陶渊明", "谢灵运", "曹操", "曹植"],
  唐代: ["李白", "杜甫", "王维", "白居易", "高适", "岑参", "李商隐", "杜牧"],
  宋代: ["苏轼", "李清照", "辛弃疾", "柳永", "陆游", "黄庭坚"],
  元代: ["马致远", "关汉卿", "王冕"],
  明清: ["纳兰性德", "龚自珍", "高启"],
  近现代: ["徐志摩", "冰心", "艾青"],
};
const poetBios = {
  屈原: "楚辞开创者，浪漫爱国诗人。代表作：《离骚》《九歌·湘夫人》《九歌·国殇》《九章·涉江》《九章·哀郢》《天问》《招魂》",
  宋玉: "先秦辞赋大家，擅写悲秋抒情。代表作：《九辩》《风赋》《高唐赋》《神女赋》《登徒子好色赋》",
  陶渊明: "田园诗鼻祖，诗风冲淡自然。代表作：《饮酒·其五》《归园田居》组诗、《桃花源诗并记》《归去来兮辞》《五柳先生传》《读山海经》",
  谢灵运: "山水诗开创者，精工描摹山川风物。代表作：《登池上楼》《登江中孤屿》《石壁精舍还湖中作》《入彭蠡湖口》《岁暮》",
  曹操: "建安文学领袖，诗风雄浑苍凉。代表作：《短歌行》《观沧海》《龟虽寿》《蒿里行》《苦寒行》《步出夏门行》",
  曹植: "建安才子，辞藻华美、情志深沉。代表作：《洛神赋》《白马篇》《七哀诗》《赠白马王彪》《野田黄雀行》《七步诗》",
  李白: "浪漫诗仙，诗风豪放飘逸。代表作：《蜀道难》《将进酒》《梦游天姥吟留别》《行路难》《静夜思》《早发白帝城》《望庐山瀑布》",
  杜甫: "现实主义诗圣，诗风沉郁顿挫。代表作：《春望》《登高》《茅屋为秋风所破歌》《兵车行》《三吏》《三别》《春夜喜雨》",
  王维: "山水田园诗大家，诗画相融、禅意悠远。代表作：《山居秋暝》《使至塞上》《鹿柴》《竹里馆》《送元二使安西》《终南别业》《相思》",
  白居易: "通俗写实诗人，关注民间疾苦。代表作：《长恨歌》《琵琶行》《卖炭翁》《钱塘湖春行》《赋得古原草送别》《观刈麦》《暮江吟》",
  高适: "边塞诗代表，雄浑悲壮。代表作：《燕歌行》《别董大》《蓟门行五首》《塞上听吹笛》《封丘作》《送李侍御赴安西》",
  岑参: "边塞诗代表，善写西域奇景。代表作：《白雪歌送武判官归京》《走马川行奉送封大夫出师西征》《逢入京使》《轮台歌奉送封大夫出师西征》《山房春事》",
  李商隐: "晚唐名家，含蓄深情、意象幽微。代表作：《锦瑟》《夜雨寄北》《无题·相见时难别亦难》《无题·昨夜星辰昨夜风》《乐游原》《隋宫》",
  杜牧: "晚唐咏史名家，俊爽清丽。代表作：《泊秦淮》《赤壁》《山行》《江南春》《过华清宫》《清明》《阿房宫赋》",
  苏轼: "豪放词宗，诗词文书画兼擅。代表作：《水调歌头·明月几时有》《念奴娇·赤壁怀古》《定风波·莫听穿林打叶声》《江城子·密州出猎》《赤壁赋》《题西林壁》",
  李清照: "婉约词宗，前期明快、后期凄婉。代表作：《声声慢》《如梦令·常记溪亭日暮》《如梦令·昨夜雨疏风骤》《一剪梅》《醉花阴》《武陵春》《夏日绝句》",
  辛弃疾: "豪放词代表，壮志报国、沉郁苍凉。代表作：《永遇乐·京口北固亭怀古》《破阵子·为陈同甫赋壮词以寄之》《青玉案·元夕》《西江月·夜行黄沙道中》《水龙吟·登建康赏心亭》《丑奴儿》",
  柳永: "北宋婉约词人，长于羁旅与慢词铺叙。代表作：《雨霖铃》《望海潮》《八声甘州》《蝶恋花·伫倚危楼风细细》《鹤冲天》《少年游》",
  陆游: "爱国诗词大家，一生心系家国。代表作：《示儿》《书愤》《十一月四日风雨大作》《游山西村》《临安春雨初霁》《钗头凤》《诉衷情》",
  黄庭坚: "江西诗派开创者，重炼字与章法。代表作：《登快阁》《寄黄几复》《雨中登岳阳楼望君山》《清明》《鄂州南楼书事》《牧童诗》",
  马致远: "元曲散曲大家，擅写秋思羁旅。代表作：《天净沙·秋思》《夜行船·秋思》《寿阳曲·远浦帆归》《拨不断·叹世》《汉宫秋》《荐福碑》",
  关汉卿: "元杂剧奠基人，作品通俗深刻。代表作：《窦娥冤》《救风尘》《望江亭》《单刀会》《拜月亭》《蝴蝶梦》《四春园》",
  王冕: "元代诗人与画家，善以梅花托物言志。代表作：《墨梅》《白梅》《素梅》组诗、《劲草行》《悲苦行》《村居》",
  纳兰性德: "清代婉约词代表，真情凄婉、清丽自然。代表作：《木兰花令·拟古决绝词》《浣溪沙·谁念西风独自凉》《长相思·山一程》《画堂春·一生一代一双人》《蝶恋花·出塞》《临江仙·寒柳》",
  龚自珍: "晚清革新诗人，咏史抒怀、呼唤变革。代表作：《己亥杂诗》组诗、《病梅馆记》《咏史》《夜坐》《漫感》《西郊落花歌》",
  高启: "明初诗文大家，诗风雄健清丽。代表作：《登金陵雨花台望大江》《梅花九首》《牧牛词》《寻胡隐君》《青丘子歌》《送陈秀才还沙上省墓》",
  徐志摩: "新月派代表，浪漫抒情。代表作：《再别康桥》《偶然》《雪花的快乐》《沙扬娜拉》《我不知道风是在哪一个方向吹》《翡冷翠的一夜》",
  冰心: "小诗派代表，文字温柔清新。代表作：《繁星》《春水》《纸船——寄母亲》《成功的花》《嫩绿的芽儿》《母亲》《荷叶·母亲》",
  艾青: "现代现实主义诗人，聚焦土地、太阳与民族命运。代表作：《大堰河——我的保姆》《我爱这土地》《向太阳》《黎明的通知》《雪落在中国的土地上》《光的赞歌》《礁石》",
};
const answer = ref("");
const trace = ref([]);
const analysis = ref([]);
const busy = ref(false);
const status = ref("连接中");
const analytics = ref(null);
const showData = ref(false);
const showReport = ref(false);
const report = ref({});
const runId = ref("");
const streamStage = ref("待输入");
const requestSeq = ref(0);
const liveEnabled = ref(false);
const draftQuery = ref("");
const draftPoem = ref("");
const followUpMode = ref(false);
const pendingSubmission = ref(false);
const voiceActive = ref(false);
const voiceTranscript = ref("");
const voiceLevel = ref(0);
const voiceFrames = ref(0);
const voiceMode = ref("待机");
const workTrace = ref([]);
const versions = ref([]);
const memories = ref([]);
const lifecycle = ref([]);
const workspace = ref({});
const showWorkspace = ref(false);
const showClearConfirm = ref(false);
const clearingHistory = ref(false);
const voicePlayback = ref(false);
let liveSocket,
  audioContext,
  audioStream,
  audioProcessor,
  audioSource,
  currentVoiceSource,
  speechRecognition;
const audioQueue = [];
let audioPlaying = false;
let providerTranscriptReceived = false;
let browserFinalTranscript = "";
let liveTurnAnswer = "";

const sessionId =
  localStorage.poetrySession ||
  (localStorage.poetrySession = crypto.randomUUID());
let socket;
const chartEls = ref([]);
const charts = [];

const needsPoem = computed(() =>
  ["review", "appreciate", "compare"].includes(task.value),
);
const currentPrompt = computed(() => tasks[task.value].placeholder);
const outputPlaceholder = computed(() =>
  busy.value ? "正在生成回答…" : "等待输入后开始对话…",
);
const sanitizeAnswer = (value) =>
  String(value || "")
    .replace(/\\r\\n|\\n|\\r/g, "\n")
    .replace(/<[^>]*>/g, "")
    .replace(/&(?:gt|lt|ast|num|nbsp);?/gi, (entity) => ({ "&gt;": ">", "&lt;": "<", "&ast;": "*", "&num;": "#", "&nbsp;": " " }[entity.toLowerCase()] || entity))
    .replace(/[\u0000-\u0008\u000b\u000c\u000e-\u001f\u007f\u200b-\u200f\u202a-\u202e\u2060\ufeff\ufffd]/g, "")
    .replace(/^\s*```(?:json|markdown|text)?\s*$/gim, "")
    .replace(/^\s{0,3}(?:#{1,6}\s*|>\s?|[-+*]\s+|\d+[.)]\s+)/gm, "")
    .replace(/\*\*([^*\n]+)\*\*/g, "$1")
    .replace(/__([^_\n]+)__/g, "$1")
    .replace(/~~([^~\n]+)~~/g, "$1")
    .replace(/`([^`\n]+)`/g, "$1")
    .replace(/[<>*#`_~|\\{}]/g, "")
    .replace(/[ \t]+\n/g, "\n")
    .replace(/\n{3,}/g, "\n\n")
    .trim();
const formatHistoryTime = (value: string) => {
  if (!value) return "时间未知";
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) return value;
  return new Intl.DateTimeFormat("zh-CN", {
    year: "numeric",
    month: "2-digit",
    day: "2-digit",
    hour: "2-digit",
    minute: "2-digit",
    second: "2-digit",
    hour12: false,
  }).format(date).replace(/\//g, "-");
};
const cleanHistoryContent = (value) =>
  sanitizeAnswer(value)
    .replace(/(?:严格|完全)?(?:依照|依据|按照|遵循|依)?[^。；\n]{0,20}(?:正体|词谱|格律|格式)[^。；\n]*(?:[。；]|$)/g, "")
    .replace(/(?:每句|句式|字数|句数)[^。；\n]*(?:[。；]|$)/g, "")
    .replace(/[（(]?\d+(?:[、,，]\d+){2,}[字]?[）)]?/g, "")
    .replace(/\n{3,}/g, "\n\n")
    .trim();
const toolLabels = {
  form_constraint: "体裁规范检查",
  version_writer: "作品版本保存",
  rhythm_checker: "格律检查",
  quality_scorer: "文笔质量评估",
  sentiment_matcher: "情感基调分析",
  hybrid_retrieval: "诗词知识检索",
  keyword_retrieval: "关键词检索",
  reranker: "检索结果排序",
  original_verifier: "原文核验",
  weakness_memory: "学习弱项回顾",
};
const toolStatusLabel = (status) => status === "failed" ? "失败" : "完成";
const toolSummaryLabel = (item) => {
  if (item.status === "failed") return "执行时出现异常";
  if (item.tool_name === "form_constraint") return "已读取所选体裁规范并用于后台校验";
  if (item.tool_name === "version_writer") return "已准备在校验通过后保存作品版本";
  if (item.tool_name === "rhythm_checker") return "已完成句数、字数、平仄与押韵检查";
  if (item.tool_name === "quality_scorer") return "已完成语言流畅度与文笔质量评估";
  if (item.tool_name === "sentiment_matcher") return "已完成情感基调匹配";
  if (item.tool_name === "original_verifier") return "已核验篇名、作者与原文信息";
  if (["hybrid_retrieval", "keyword_retrieval", "reranker"].includes(item.tool_name)) return "已完成相关诗词证据检索与整理";
  return "工具已完成本轮处理";
};
const errorText = (value) => {
  if (typeof value === "string") return value;
  if (Array.isArray(value))
    return value
      .map((item) => item?.msg || item?.message || JSON.stringify(item))
      .join("；");
  return (
    value?.message ||
    value?.msg ||
    value?.detail ||
    JSON.stringify(value || "未知错误")
  );
};
let responseTimer = 0;
const armResponseTimeout = (payload) => {
  clearTimeout(responseTimer);
  responseTimer = window.setTimeout(async () => {
    if (!busy.value) return;
    try {
      socket?.close();
    } catch {}
    status.value = "实时通道响应较慢，正在切换生成";
    streamStage.value = "HTTP 回退";
    try {
      const response = await fetch("/api/agent", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ ...payload, live: false }),
      });
      const data = await response.json();
      if (!response.ok)
        throw new Error(data.detail || `HTTP ${response.status}`);
      answer.value = sanitizeAnswer(data.answer || answer.value);
      streamStage.value = "已完成";
    } catch (error) {
      answer.value = `请求失败：${error.message || error}`;
      streamStage.value = "出错";
    } finally {
      busy.value = false;
      pendingSubmission.value = false;
    }
  }, 16000);
};

const ensureSocket = () =>
  new Promise((ok, no) => {
    if (socket && socket.readyState === 1) return ok(socket);
    socket = new WebSocket(
      `${location.protocol === "https:" ? "wss" : "ws"}://${location.host}/ws/agent/${sessionId}`,
    );
    socket.onopen = () => {
      status.value = liveEnabled.value ? "GPT-Live 全双工已就绪" : "已连接";
      ok(socket);
    };
    socket.onerror = (err) => {
      status.value = "连接失败";
      no(err);
    };
    socket.onclose = () => {
      status.value = "连接已断开";
    };
  });

function bindSocket() {
  if (!socket) return;
  socket.onmessage = (e) => {
    const msg = JSON.parse(e.data);
    if (msg.type === "start") {
      streamStage.value = "检索中";
      trace.value.push("已收到请求，正在检索证据…");
      return;
    }
    if (msg.type === "node") {
      streamStage.value =
        msg.node === "parse"
          ? "理解问题"
          : msg.node === "retrieve"
            ? "检索证据"
            : msg.node === "grade"
              ? "Self-RAG 评分"
              : msg.node === "rewrite"
                ? "改写查询"
                : msg.node === "analyze"
                  ? "多标注分析"
                  : msg.node === "draft"
                    ? "生成中"
                    : msg.node === "validate"
                      ? "自省校验"
                      : msg.node === "revise"
                        ? "修订中"
                        : "处理中";
      trace.value.push(msg.message);
      return;
    }
    if (msg.type === "status") {
      streamStage.value = msg.stage || streamStage.value;
      return;
    }
    if (msg.type === "token") {
      clearTimeout(responseTimer);
      streamStage.value = "输出中";
      answer.value = sanitizeAnswer(answer.value + msg.content);
      return;
    }
    if (msg.type === "complete") {
      clearTimeout(responseTimer);
      streamStage.value = "已完成";
      runId.value = msg.data.run_id;
      analysis.value = makeAnalysis(msg.data);
      answer.value = sanitizeAnswer(answer.value || msg.data?.answer);
      report.value = msg.data;
      workTrace.value = msg.data.work_trace || [];
      versions.value = msg.data.versions || [];
      memories.value = msg.data.memories || [];
      lifecycle.value = msg.data.lifecycle || [];
      workspace.value = msg.data.workspace || workspace.value;
      showReport.value = Boolean(
        msg.data.rhythm || msg.data.quality || msg.data.evidence?.length,
      );
      busy.value = false;
      pendingSubmission.value = false;
      nextTick(renderReportCharts);
      return;
    }
    if (msg.type === "cancelled") {
      streamStage.value = "已打断";
      busy.value = false;
      pendingSubmission.value = false;
      return;
    }
    if (msg.type === "error") {
      streamStage.value = "出错";
      answer.value = `请求失败：${msg.message}`;
      busy.value = false;
      pendingSubmission.value = false;
    }
  };
}

function beginConversation(mode = "new") {
  if (busy.value) return;
  const content = draftQuery.value.trim();
  if (!content) return;
  pendingSubmission.value = true;
  busy.value = true;
  followUpMode.value = Boolean(answer.value || workspace.value.history?.length);
  streamStage.value = followUpMode.value ? "承接上下文" : "发送中";
  answer.value = "";
  trace.value = [];
  analysis.value = [];
  requestSeq.value += 1;
  submitPayload({ followup: followUpMode.value, content });
}

async function submitPayload({ followup = false, content = "" } = {}) {
  const payload = {
    task: task.value,
    query: draftQuery.value || query.value,
    poem: poem.value,
    form: task.value === "generate" ? genreExtension.value || form.value : "不限",
    genre_group: task.value === "generate" ? selectedGenreGroup.value : "不限",
    emotion: task.value === "generate" ? emotionExtension.value || emotion.value : "不限",
    emotion_group: task.value === "generate" ? selectedEmotionGroup.value : "不限",
    themes: task.value === "generate" ? (themeDetail.value ? [themeDetail.value] : themes.value) : [],
    theme_group: task.value === "generate" ? selectedThemeGroup.value : "不限",
    dynasty: "不限",
    grade: "中学生",
    request_id: requestSeq.value,
    live: true,
    self_rag: task.value !== "generate",
    followup,
    content,
    conversation_id: workspace.value.conversation_id || "",
    branch_id: workspace.value.branch_id || "",
  };
  try {
    await ensureSocket();
    bindSocket();
    socket.send(JSON.stringify(payload));
    armResponseTimeout(payload);
  } catch (error) {
    status.value = "WebSocket 不可用，已切换到 HTTP 回退";
    streamStage.value = "HTTP 回退";
    try {
      const response = await fetch("/api/agent", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(payload),
      });
      const data = await response
        .json()
        .catch(() => ({ answer: "服务返回了非 JSON 内容。" }));
      if (!response.ok) {
        throw new Error(
          errorText(data.answer || data.detail || `HTTP ${response.status}`),
        );
      }
      answer.value = sanitizeAnswer(data.answer) || "请求完成，但没有返回内容。";
      runId.value = data.run_id || "";
      analysis.value = makeAnalysis(data);
      report.value = data;
      workTrace.value = data.work_trace || [];
      versions.value = data.versions || [];
      memories.value = data.memories || [];
      lifecycle.value = data.lifecycle || [];
      workspace.value = data.workspace || workspace.value;
      showReport.value = Boolean(
        data.rhythm || data.quality || data.evidence?.length,
      );
      streamStage.value = "已完成";
      status.value = "HTTP 回退已完成";
      nextTick(renderReportCharts);
    } catch (fallbackError) {
      answer.value = `请求失败：${fallbackError.message || fallbackError}`;
      streamStage.value = "出错";
      status.value = "请求失败";
    } finally {
      busy.value = false;
      pendingSubmission.value = false;
    }
  }
}

async function submit() {
  if (busy.value) return;
  const recognizedText = (draftQuery.value || voiceTranscript.value).trim();
  if (!recognizedText) {
    status.value = "请先输入内容或完成语音转写";
    return;
  }
  if (voiceActive.value) await stopVoiceInput();
  audioQueue.length = 0;
  try { currentVoiceSource?.stop(); } catch {}
  currentVoiceSource = null;
  audioPlaying = false;
  if (liveSocket?.readyState === WebSocket.OPEN) liveSocket.close();
  liveSocket = null;
  voiceMode.value = "已提交";
  draftQuery.value = recognizedText;
  query.value = recognizedText;
  poem.value = draftPoem.value;
  beginConversation("new");
}

async function selectTask(key) {
  if (busy.value) return;
  task.value = key;
  answer.value = "";
  trace.value = [];
  analysis.value = [];
  draftQuery.value = "";
  draftPoem.value = "";
  workspace.value = {};
  if (key !== "generate") {
    form.value = "不限";
    emotion.value = "";
    themes.value = [];
    genreExtension.value = "";
    emotionExtension.value = "";
    themeDetail.value = "";
    selectedGenreGroup.value = "不限";
    selectedEmotionGroup.value = "不限";
    selectedThemeGroup.value = "不限";
  }
  await refreshWorkspace();
}

async function refreshWorkspace() {
  try {
    const res = await fetch(`/api/workspace/${sessionId}?task=${encodeURIComponent(task.value)}`);
    if (!res.ok) return;
    workspace.value = await res.json();
    workTrace.value = workspace.value.trace || [];
    versions.value = workspace.value.versions || [];
    memories.value = workspace.value.memories || [];
  } catch {}
}

async function openWorkspace() {
  await refreshWorkspace();
  showWorkspace.value = true;
}

async function clearHistory() {
  clearingHistory.value = true;
  status.value = "正在清除历史记录";
  try {
    const response = await fetch(`/api/workspace/${sessionId}/clear`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ task: task.value }),
    });
    const result = await response.json();
    if (!response.ok || !result.ok) throw new Error(result.message || "清除失败");
    answer.value = "";
    trace.value = [];
    analysis.value = [];
    workTrace.value = [];
    versions.value = [];
    workspace.value = result.workspace || {};
    showClearConfirm.value = false;
    status.value = "当前功能的历史记录已清除";
  } catch (error) {
    status.value = `历史记录清除失败：${error instanceof Error ? error.message : "服务不可用"}`;
  } finally {
    clearingHistory.value = false;
  }
}

async function switchBranch(branchId) {
  workspace.value.branch_id = branchId;
  showWorkspace.value = false;
  await refreshWorkspace();
  const latest = workspace.value.history?.filter((item) => item.role === "assistant").at(-1);
  if (latest) answer.value = sanitizeAnswer(latest.content);
  status.value = "已切换对话分支";
}

async function rollbackTo(messageId) {
  const response = await fetch("/api/branches/rollback", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({
      conversation_id: workspace.value.conversation_id,
      branch_id: workspace.value.branch_id,
      message_id: messageId,
    }),
  });
  if (!response.ok) return;
  workspace.value = { ...workspace.value, ...(await response.json()) };
  await refreshWorkspace();
  status.value = "已从所选消息创建回滚分支";
}

async function forkBranch(versionIndex = 0) {
  const source = workspace.value.branch_id || "";
  const conversation = workspace.value.conversation_id || "";
  if (!conversation || !source) return;
  try {
    const res = await fetch("/api/branches", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        conversation_id: conversation,
        source_branch_id: source,
        name: versionIndex === 0 ? "新分支" : `分支${versionIndex + 1}`,
      }),
    });
    if (!res.ok) return;
    workspace.value = await res.json();
    await refreshWorkspace();
  } catch {}
}

async function removeMemory(id) {
  try {
    await fetch(`/api/memories/${id}`, { method: "DELETE" });
    await refreshWorkspace();
  } catch {}
}

async function restoreLatestVersion() {
  if (!versions.value.length) return;
  const latest = versions.value[0];
  draftQuery.value = latest.content || draftQuery.value;
  status.value = "已恢复最新版本内容到输入框，请点击发送并生成";
}

function stopCurrentVoiceResponse(message = "已打断回答，请继续说话") {
  audioQueue.length = 0;
  try { currentVoiceSource?.stop(); } catch {}
  currentVoiceSource = null;
  audioPlaying = false;
  if (liveSocket?.readyState === 1)
    liveSocket.send(JSON.stringify({ type: "interrupt" }));
  voiceMode.value = voiceActive.value ? "正在聆听" : "已打断";
  status.value = message;
}
function interrupt() {
  if (socket?.readyState === 1) socket.send(JSON.stringify({ type: "cancel" }));
  stopCurrentVoiceResponse();
  streamStage.value = "正在打断";
}
const bytesToBase64 = (bytes) => {
  let value = "";
  for (const byte of bytes) value += String.fromCharCode(byte);
  return btoa(value);
};
const base64ToBytes = (value) =>
  Uint8Array.from(atob(value), (char) => char.charCodeAt(0));
const resampleTo16kPcm = (input, sourceRate) => {
  const targetRate = 16000;
  const ratio = sourceRate / targetRate;
  const length = Math.max(1, Math.round(input.length / ratio));
  const pcm = new Int16Array(length);
  for (let index = 0; index < length; index++) {
    const start = Math.floor(index * ratio);
    const end = Math.min(input.length, Math.floor((index + 1) * ratio));
    let sum = 0;
    for (let source = start; source < Math.max(start + 1, end); source++)
      sum += input[Math.min(source, input.length - 1)];
    const sample = Math.max(-1, Math.min(1, sum / Math.max(1, end - start)));
    pcm[index] = sample < 0 ? sample * 32768 : sample * 32767;
  }
  return pcm;
};
async function playVoice() {
  if (!voicePlayback.value) {
    audioQueue.length = 0;
    return;
  }
  if (audioPlaying || !audioQueue.length || !audioContext) return;
  audioPlaying = true;
  const pcm = audioQueue.shift();
  const view = new DataView(pcm.buffer, pcm.byteOffset, pcm.byteLength);
  const samples = new Float32Array(pcm.length / 2);
  for (let i = 0; i < samples.length; i++)
    samples[i] = view.getInt16(i * 2, true) / 32768;
  const buffer = audioContext.createBuffer(1, samples.length, 24000);
  buffer.copyToChannel(samples, 0);
  const source = audioContext.createBufferSource();
  currentVoiceSource = source;
  source.buffer = buffer;
  source.connect(audioContext.destination);
  source.onended = () => {
    audioPlaying = false;
    currentVoiceSource = null;
    playVoice();
  };
  source.start();
}
function toggleVoicePlayback() {
  voicePlayback.value = !voicePlayback.value;
  if (!voicePlayback.value) {
    audioQueue.length = 0;
    try {
      currentVoiceSource?.stop();
    } catch {}
    currentVoiceSource = null;
    audioPlaying = false;
    if (liveSocket?.readyState === 1)
      liveSocket.send(JSON.stringify({ type: "interrupt" }));
    status.value = "已停止朗读";
  } else {
    status.value = "语音朗读已开启";
    playVoice();
  }
}
async function stopVoiceInput() {
  audioProcessor?.disconnect();
  audioSource?.disconnect();
  audioStream?.getTracks().forEach((track) => track.stop());
  try { speechRecognition?.stop(); } catch {}

  voiceActive.value = false;
  voiceMode.value = "已退出";
  status.value = voiceFrames.value
    ? "GPT-Live 已退出"
    : "GPT-Live 已退出，未检测到麦克风音频";
  window.setTimeout(() => {
    const transcript = (voiceTranscript.value || draftQuery.value).trim();
    if (["转写中", "识别中", "正在思考"].includes(voiceMode.value) && transcript) {
      voiceTranscript.value = transcript;
      draftQuery.value = transcript;
      voiceMode.value = "转写完成";
      status.value = providerTranscriptReceived
        ? "语音识别完成，可点击发送并生成"
        : "浏览器转写完成，可点击发送并生成";
    } else if (["转写中", "识别中", "正在思考"].includes(voiceMode.value)) {
      voiceMode.value = "未识别";
      status.value = "未收到转写文字，请连续说话 3 秒以上并检查浏览器麦克风权限";
    }
  }, 10000);
}

async function toggleVoice() {
  if (voiceActive.value) {
    await stopVoiceInput();
    return;
  }

  try {
    voiceLevel.value = 0;
    voiceFrames.value = 0;
    voiceTranscript.value = "";
    providerTranscriptReceived = false;
    browserFinalTranscript = "";
    liveTurnAnswer = "";
    voiceMode.value = "连接中";
    status.value = "正在请求麦克风权限";

    // 先申请麦克风，避免实时服务连接异常时页面看起来像“麦克风不可用”。
    audioStream = await navigator.mediaDevices.getUserMedia({
      audio: {
        channelCount: 1,
        sampleRate: 16000,
        echoCancellation: true,
        noiseSuppression: true,
        autoGainControl: true,
      },
    });
    audioContext = new AudioContext({ sampleRate: 16000 });
    await audioContext.resume();

    status.value = "语音服务已连接，正在初始化";
    liveSocket = new WebSocket(
      `${location.protocol === "https:" ? "wss" : "ws"}://${location.host}/ws/live`,
    );

    const ready = new Promise((resolve, reject) => {
      const timer = window.setTimeout(
        () => reject(new Error("语音服务初始化超时")),
        12000,
      );

      liveSocket.onopen = () => {
        status.value = "语音服务已连接，正在初始化";
      };

      liveSocket.onerror = () => {
        clearTimeout(timer);
        reject(new Error("语音 WebSocket 连接失败"));
      };

      liveSocket.onmessage = (event) => {
        const msg = JSON.parse(event.data);

        if (msg.type === "voice.ready") {
          clearTimeout(timer);
          voiceMode.value = msg.mode === "full_duplex" ? "全双工对话" : "录音中";
          voicePlayback.value = msg.mode === "full_duplex";
          resolve();
          return;
        }

        if (msg.type === "audio.delta") {
          audioQueue.push(base64ToBytes(msg.audio || ""));
          playVoice();
          return;
        }

        if (msg.type === "input_audio_buffer.speech_started") {
          audioQueue.length = 0;
          try { currentVoiceSource?.stop(); } catch {}
          currentVoiceSource = null;
          audioPlaying = false;
          liveTurnAnswer = "";
          browserFinalTranscript = "";
          voiceTranscript.value = "";
          voiceMode.value = "正在聆听并转写";
          status.value = "正在实时转写；停顿后自动生成并朗读回答";
          return;
        }

        if (msg.type === "response.interrupted") {
          audioQueue.length = 0;
          try { currentVoiceSource?.stop(); } catch {}
          currentVoiceSource = null;
          audioPlaying = false;
          voiceMode.value = voiceActive.value ? "正在聆听" : "已打断";
          status.value = msg.automatic ? "已自然打断，继续聆听" : "已停止当前语音回答";
          return;
        }

        if (msg.type === "input_audio_buffer.speech_stopped") {
          voiceMode.value = "正在生成回答";
          status.value = "检测到停顿，正在自动生成文字与语音回答";
          return;
        }

        if (msg.type === "input.transcript.delta") {
          providerTranscriptReceived = true;
          voiceTranscript.value = msg.text || `${voiceTranscript.value}${msg.delta || ""}`;
          draftQuery.value = voiceTranscript.value;
          if (task.value === "generate") draftPoem.value = "";
          status.value = task.value === "generate" ? "正在识别创作要求" : "正在识别语音";
          return;
        }

        if (msg.type === "input.transcript") {
          providerTranscriptReceived = true;
          const transcript = (msg.text || voiceTranscript.value).trim();
          if (transcript.length >= voiceTranscript.value.trim().length) {
            voiceTranscript.value = transcript;
            draftQuery.value = transcript;
          }
          status.value = "语音识别完成，请确认文字后发送或继续说话";
          return;
        }

        if (msg.type === "response.requested") {
          voiceMode.value = "正在生成回答";
          status.value = "GPT-Live 已收到转写，正在生成文字与语音回答";
          return;
        }

        if (msg.type === "assistant.transcript.delta") {
          const delta = msg.text || "";
          liveTurnAnswer += delta;
          answer.value = sanitizeAnswer(liveTurnAnswer);
          voiceMode.value = "正在回答";
          status.value = "GPT-Live 正在生成并朗读；可直接插话打断";
          return;
        }

        if (msg.type === "input.transcription.completed") {
          voiceTranscript.value = msg.text || voiceTranscript.value;
          draftQuery.value = voiceTranscript.value;
          voiceMode.value = "正在生成回答";
          status.value = "转写完成，正在自动生成文字与语音回答";
          return;
        }

        if (msg.type === "response.done") {
          voiceMode.value = "全双工对话";
          status.value = "回答完成，可继续直接说话";
          return;
        }

        if (msg.type === "error") {
          const message = errorText(msg.message);
          if (voiceActive.value || voiceFrames.value > 0) {
            voiceMode.value = voiceActive.value ? "录音中" : "转写中";
            status.value = `云端实时通道异常，已保留录音并使用浏览器转写：${message}`;
          } else {
            voiceMode.value = "错误";
            status.value = `语音错误：${message}`;
          }
        }
      };
    });

    await ready;
    const Recognition = window.SpeechRecognition || window.webkitSpeechRecognition;
    if (Recognition) {
      speechRecognition = new Recognition();
      speechRecognition.lang = "zh-CN";
      speechRecognition.continuous = true;
      speechRecognition.interimResults = true;
      speechRecognition.onresult = (event) => {
        let interim = "";
        for (let index = event.resultIndex; index < event.results.length; index++) {
          const text = event.results[index][0]?.transcript || "";
          if (event.results[index].isFinal) browserFinalTranscript += text;
          else interim += text;
        }
        const text = `${browserFinalTranscript}${interim}`.trim();
        if (!providerTranscriptReceived && text) {
          voiceTranscript.value = text;
          draftQuery.value = text;
          voiceMode.value = "识别中";
          status.value = "正在转写语音";
        }
      };
      speechRecognition.onerror = (event) => {
        if (["no-speech", "aborted"].includes(event.error)) return;
        status.value = `浏览器语音识别不可用（${event.error}），等待云端转写`;
      };
      try { speechRecognition.start(); } catch {}
    }
    audioSource = audioContext.createMediaStreamSource(audioStream);
    audioProcessor = audioContext.createScriptProcessor(4096, 1, 1);
    audioSource.connect(audioProcessor);
    audioProcessor.connect(audioContext.destination);

    audioProcessor.onaudioprocess = (event) => {
      if (liveSocket?.readyState !== WebSocket.OPEN) return;

      const input = event.inputBuffer.getChannelData(0);
      const pcm = resampleTo16kPcm(input, event.inputBuffer.sampleRate);
      let energy = 0;

      for (let i = 0; i < input.length; i++) energy += input[i] * input[i];

      voiceLevel.value = Math.min(100, Math.round(Math.sqrt(energy / input.length) * 500));
      voiceFrames.value += 1;
      liveSocket.send(
        JSON.stringify({
          type: "audio.append",
          audio: bytesToBase64(new Uint8Array(pcm.buffer)),
        }),
      );
    };

    voiceActive.value = true;
    voiceMode.value = "全双工对话";
    status.value = "GPT-Live 已开启：直接说话，可在助教回答时随时插话打断";
  } catch (error) {
    voiceActive.value = false;
    voiceMode.value = "错误";
    audioProcessor?.disconnect();
    audioSource?.disconnect();
    audioStream?.getTracks().forEach((track) => track.stop());
    audioProcessor = null;
    audioSource = null;
    audioStream = null;
    if (audioContext && audioContext.state !== "closed") {
      try { await audioContext.close(); } catch {}
    }
    audioContext = null;
    liveSocket?.close();
    liveSocket = null;
    const name = error?.name || "";
    status.value = name === "NotAllowedError"
      ? "麦克风权限被拒绝，请在浏览器地址栏中允许麦克风后重试"
      : name === "NotFoundError"
        ? "未找到可用麦克风，请检查系统输入设备"
        : `语音错误：${errorText(error)}`;
  }
}

function quickAsk(text) {
  draftQuery.value = text;
  status.value = "已填入输入框，请点击发送并生成";
}

function makeAnalysis(d) {
  const rows = [];
  if (d.rhythm)
    rows.push([
      "格律",
      `${Math.round(d.rhythm.score * 100)} 分`,
      d.rhythm.genre,
    ]);
  if (d.sentiment) rows.push(["情感", d.sentiment.name, "FSPC 五级对照"]);
  if (d.quality)
    rows.push([
      "文笔",
      d.quality.level,
      `流畅 ${d.quality.fluency} · 意蕴 ${d.quality.meaningfulness}`,
    ]);
  if (d.validation)
    rows.push([
      "自省",
      d.validation.passed ? "通过" : "待优化",
      `相关性 ${Math.round((d.validation.retrieval_relevance || 0) * 100)}%`,
    ]);
  return rows;
}

function renderReportCharts() {
  if (!showReport.value) return;
  const quality = document.querySelector("#qualityChart");
  const emotionEl = document.querySelector("#emotionChart");
  if (quality && report.value.quality) {
    const q = report.value.quality;
    const c = echarts.init(quality);
    c.setOption({
      radar: {
        indicator: [
          { name: "流畅", max: 5 },
          { name: "连贯", max: 5 },
          { name: "意蕴", max: 5 },
          { name: "综合", max: 5 },
        ],
        splitArea: { areaStyle: { color: ["#ffffff30", "#ffffff60"] } },
        axisName: { fontSize: 9 },
      },
      series: [
        {
          type: "radar",
          data: [
            {
              value: [
                q.fluency,
                q.coherence,
                q.meaningfulness,
                q.overall || q.overall_score || q.fluency,
              ],
              areaStyle: { color: "#4d8a6655" },
              lineStyle: { color: "#356b50" },
            },
          ],
        },
      ],
    });
    charts.push(c);
  }
  if (emotionEl && report.value.sentiment) {
    const target = Number(emotion.value || 3);
    const values = [1, 2, 3, 4, 5].map((i) =>
      i === Number(report.value.sentiment.label || 3)
        ? 100
        : i === target
          ? 58
          : 15,
    );
    const c = echarts.init(emotionEl);
    c.setOption({
      radar: {
        indicator: ["直白悲", "含蓄悲", "中性", "含蓄喜", "直白喜"].map(
          (name) => ({ name, max: 100 }),
        ),
        axisName: { fontSize: 8 },
      },
      series: [
        {
          type: "radar",
          data: [
            {
              value: values,
              areaStyle: { color: "#d5bd7055" },
              lineStyle: { color: "#ad8835" },
            },
          ],
        },
      ],
    });
    charts.push(c);
  }
}

function cancel() {
  interrupt();
}

async function feedback(helpful, category) {
  if (!runId.value) return;
  await fetch("/api/feedback", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ run_id: runId.value, helpful, category }),
  });
  runId.value = "";
}

function option(title, data, type = "pie") {
  const safeData = data?.length ? data : [{ name: "暂无统计", value: 1 }];
  return {
    backgroundColor: "transparent",
    title: {
      text: title,
      left: 16,
      top: 12,
      textStyle: {
        fontFamily: "FangSong, STFangsong, FangSong_GB2312, serif",
        fontSize: 14,
        fontWeight: 700,
        color: "#174B5F",
      },
    },
    tooltip: {
      trigger: type === "pie" ? "item" : "axis",
      backgroundColor: "#f8feff",
      borderColor: "#9ED7E5",
      textStyle: { color: "#174B5F" },
    },
    grid: { left: 50, right: 20, top: 54, bottom: 40, containLabel: true },
    series:
      type === "pie"
        ? [
            {
              type: "pie",
              radius: ["40%", "70%"],
              center: ["50%", "58%"],
              roseType: "radius",
              itemStyle: {
                borderColor: "#f7faf7",
                borderWidth: 3,
                borderRadius: 6,
              },
              label: { fontSize: 10, color: "#174B5F" },
              data: safeData,
            },
          ]
        : [
            {
              type: "bar",
              data: safeData.map((x) => x.value),
              barMaxWidth: 24,
              itemStyle: {
                color: new echarts.graphic.LinearGradient(0, 0, 0, 1, [
                  { offset: 0, color: "#0E8B8F" },
                  { offset: 1, color: "#82D4E0" },
                ]),
                borderRadius: [7, 7, 0, 0],
              },
            },
          ],
    xAxis:
      type === "bar"
        ? {
            type: "category",
            data: safeData.map((x) => x.name),
            axisLabel: {
              fontSize: 9,
              color: "#53685d",
              interval: 0,
              rotate: safeData.length > 6 ? 24 : 0,
            },
            axisLine: { lineStyle: { color: "#cbd8d0" } },
            axisTick: { show: false },
          }
        : undefined,
    yAxis:
      type === "bar"
        ? {
            type: "value",
            axisLabel: { fontSize: 9, color: "#738078" },
            splitLine: { lineStyle: { color: "#dfe8e240" } },
          }
        : undefined,
    color: ["#2F5D50", "#6E947F", "#C9924D", "#A65B45", "#6C7889", "#D9B873"],
  };
}

function renderCharts() {
  const a = analytics.value;
  if (!a) return;
  charts.splice(0).forEach((c) => c.dispose());
  const dynastyData = [
    ...(a.ccpc?.朝代 || a.ccpc?.dynasties || []),
    ...(a.chinese_poetry?.朝代 || []),
  ]
    .reduce((items, item) => {
      const current = items.find((row) => row.name === item.name);
      if (current) current.value += item.value;
      else items.push({ ...item });
      return items;
    }, [])
    .sort((left, right) => right.value - left.value)
    .slice(0, 10);
  const emotions = a.fspc?.整体情感 || a.fspc?.holistic || [];
  const metrics = a.dataset_metrics || [];
  const imagery = a.imagery || [];
  const formData =
    a.chinese_poetry?.体裁 || a.ccpc?.体裁 || a.ccpc?.forms || [];
  const timelineOrder = [
    "先秦",
    "汉魏",
    "唐代",
    "宋代",
    "元代",
    "明清",
    "近现代",
  ];
  const timelineRanges = ["前11世纪—前221", "前202—589", "618—907", "960—1279", "1271—1368", "1368—1912", "1912—至今"];
  const timelineNotes = [
    "楚辞发源",
    "乐府古体",
    "格律成熟",
    "词体鼎盛",
    "散曲兴起",
    "延续复古",
    "新诗转型",
  ];
  const timelineDescriptions = {
    先秦: "屈原、宋玉开创楚辞体系，华夏浪漫诗歌源头",
    汉魏: "汉乐府成熟，五言古诗、建安风骨奠定古体诗基础",
    唐代: "近体诗五绝、七绝、五律、七律定型，古典诗歌黄金鼎盛期",
    宋代: "长短句词全面繁荣，豪放、婉约两大词派并行发展",
    元代: "元小令、套曲、杂剧普及，通俗抒情新文体诞生",
    明清: "仿古乐府、古风、律绝、长短句词持续创作，诗词传统延续",
    近现代: "白话现代短诗、散文诗兴起，诗歌形式与语言现代化革新",
  };
  // 表示当前项目语料库的相对收录规模，不等同于各朝代历史创作总量。
  // 唐代语料来自《全唐诗》和 CCPC，宋代主要来自 CCPC，因此二者应形成明显层级。
  const timelineData = [1800, 5200, 53400, 14200, 2500, 4200, 1800];
  const emotionColors = ["#4F6B5B", "#789C84", "#D8B384", "#A65B45", "#6C7889"];
  const dynastyDetails = {
    先秦: ["约公元前11世纪—前221年；《诗经》奠定现实主义传统，楚辞开拓浪漫主义表达", "核心体裁：《诗经》四言、楚辞骚体、九歌、九章", "代表作家与作品：屈原《离骚》《九歌》《九章》《天问》，宋玉《九辩》", "语言与审美：重章复沓、香草美人、神话想象与家国忧思"],
    汉魏: ["汉至魏晋南北朝；乐府采诗制度推动叙事诗发展，五言诗逐渐成熟", "核心体裁：汉乐府、古诗十九首、建安五言、田园诗与山水诗", "代表作家与作品：曹操《短歌行》、曹植《白马篇》、陶渊明《归园田居》、谢灵运山水诗", "语言与审美：汉乐府质朴叙事，建安风骨慷慨悲凉，魏晋诗歌趋向玄远自然"],
    唐代: ["618—907年；近体诗格律定型，题材、流派与艺术风格高度繁荣", "核心体裁：五七言绝句、律诗、排律、古风与乐府歌行", "代表作家与作品：李白《蜀道难》、杜甫《登高》、王维《山居秋暝》、白居易《琵琶行》", "语言与审美：盛唐雄浑，中唐尚实，晚唐精工；边塞、山水、咏史等题材全面成熟"],
    宋代: ["960—1279年；词体进入鼎盛期，诗歌形成重理趣、重日常的新面貌", "核心体裁：小令、中调、长调，以及宋诗七律、绝句与古体", "代表作家与作品：苏轼《念奴娇·赤壁怀古》、李清照《声声慢》、辛弃疾《永遇乐·京口北固亭怀古》、柳永《雨霖铃》", "语言与审美：婉约与豪放并行，词的音乐性、抒情性和长调铺叙能力充分发展"],
    元代: ["1271—1368年；散曲与杂剧兴盛，诗歌表达进一步市民化、口语化", "核心体裁：散曲小令、套数、杂剧唱词，常见曲牌有天净沙、山坡羊、水仙子", "代表作家与作品：马致远《天净沙·秋思》、张养浩《山坡羊·潼关怀古》、关汉卿杂剧曲辞", "语言与审美：句式灵活、衬字自由，兼具俚俗生动、讽世感怀与舞台节奏"],
    明清: ["1368—1912年；传统诗词持续发展，复古、性灵、格调等诗学主张并立", "核心体裁：律绝、古风、乐府、词与竹枝词等民歌化形式", "代表作家与作品：高启《登金陵雨花台望大江》、纳兰性德《木兰花令》、龚自珍《己亥杂诗》", "语言与审美：既承唐宋法度，又强化个性、性灵与时代感，清词尤多幽婉深情"],
    近现代: ["20世纪以来；白话新诗兴起，同时旧体诗词继续创作并发生现代转化", "核心体裁：自由诗、现代格律诗、散文诗、十四行诗与现代旧体诗", "代表作家与作品：徐志摩《再别康桥》、闻一多《死水》、艾青《我爱这土地》、戴望舒《雨巷》", "语言与审美：白话、自由节奏和现代意象成为主流，个人经验与民族命运紧密交织"],
  };
  const eraForms = {
    先秦楚辞: ["楚辞骚体", "九歌", "九章"],
    汉魏古体: ["汉乐府", "五言古诗", "七言古诗", "杂言歌行", "柏梁体"],
    唐诗: [
      "五言绝句",
      "七言绝句",
      "五言律诗",
      "七言律诗",
      "五言排律",
      "七言排律",
    ],
    宋词: [
      "小令（浣溪沙、如梦令）",
      "中调（蝶恋花、渔家傲）",
      "长调（水调歌头、满江红、念奴娇）",
    ],
    元代散曲: ["元曲小令（天净沙、山坡羊）", "元曲套曲", "杂剧唱词"],
    明清诗词: ["仿古乐府", "古风歌行", "长短句词", "近体律绝"],
    近现代诗文: ["现代短诗", "散文诗"],
  };
  const eraColors = [
    "#CD6670", // 先秦：浅胭脂
    "#DC8A5A", // 汉魏：柔丹橘
    "#E5C857", // 唐代：鹅黄
    "#78AA7F", // 宋代：浅翠竹
    "#68AEAA", // 元代：浅天青
    "#7099BD", // 明清：浅石青
    "#9B82AD", // 近现代：浅藤萝
  ];
  const mixHex = (color, target, amount) => {
    const source = color.match(/[\da-f]{2}/gi).map((value) => parseInt(value, 16));
    const destination = target.match(/[\da-f]{2}/gi).map((value) => parseInt(value, 16));
    return `#${source
      .map((value, index) =>
        Math.round(value + (destination[index] - value) * amount)
          .toString(16)
          .padStart(2, "0"),
      )
      .join("")}`;
  };
  const eraShadeGroups = eraColors.map((color) => [
    mixHex(color, "#FFFBF3", 0.24),
    mixHex(color, "#4A4038", 0.06),
    mixHex(color, "#FFFBF3", 0.12),
    mixHex(color, "#4A4038", 0.11),
    mixHex(color, "#FFFBF3", 0.34),
    mixHex(color, "#4A4038", 0.16),
    color,
  ]);
  const traditionalGradient = (index) => eraColors[index % eraColors.length];
  const alternatingShadeOrder = [4, 3, 0, 5, 2, 1, 6];
  const childColor = (groupIndex, childIndex) =>
    eraShadeGroups[groupIndex % eraShadeGroups.length][
      alternatingShadeOrder[childIndex % alternatingShadeOrder.length]
    ];
  const eraNames = ["先秦", "汉魏", "唐代", "宋代", "元代", "明清", "近现代"];
  const genericFormExamples = {
    先秦楚辞: "屈原《离骚》《九歌·湘夫人》《九章·哀郢》《天问》；宋玉《九辩》",
    汉魏古体: "《古诗十九首》；曹操《短歌行》；曹植《白马篇》；陶渊明《归园田居》",
    唐诗: "李白《静夜思》《蜀道难》；杜甫《春望》《登高》；王维《山居秋暝》；白居易《琵琶行》",
    宋词: "晏殊《浣溪沙》；苏轼《水调歌头》《念奴娇》；李清照《声声慢》；辛弃疾《永遇乐》",
    元代散曲: "马致远《天净沙·秋思》；张养浩《山坡羊·潼关怀古》；乔吉《水仙子·寻梅》",
    明清诗词: "高启《登金陵雨花台望大江》；纳兰性德《木兰花令》；龚自珍《己亥杂诗》",
    近现代诗文: "徐志摩《再别康桥》；闻一多《死水》；戴望舒《雨巷》；艾青《我爱这土地》",
  };
  const inferredFormDetails = Object.fromEntries(
    Object.entries(eraForms).flatMap(([parent, items]) =>
      items.map((name) => [name, [
        `所属：${parent}`,
        `体式说明：${name}是${parent}中的常见细分形式，创作时需遵循其句式、节奏、用韵和篇章惯例`,
        `代表作者与作品：${genericFormExamples[parent]}`,
      ]]),
    ),
  );
  const formDetails = {
    ...inferredFormDetails,
    楚辞骚体: ["所属：先秦楚辞", "特点：以‘兮’字调节节奏，句式参差，常用香草美人、神游问天等意象寄托人格与政治理想", "作家与作品：屈原《离骚》《九章·涉江》《九章·哀郢》，宋玉《九辩》"],
    离骚体: ["所属：楚辞骚体的代表形态", "特点：长篇抒情、主客问答、神话想象与象征体系交织", "作家与作品：屈原《离骚》，后世拟骚作品如贾谊《吊屈原赋》承其精神"],
    九歌体: ["所属：楚辞祭歌", "特点：以迎神、娱神、送神结构表现人神恋慕，语言瑰丽而哀婉", "作家与作品：屈原《九歌·湘君》《九歌·湘夫人》《九歌·山鬼》《九歌·国殇》"],
    九章体: ["所属：楚辞组诗", "特点：多记身世、放逐与政治理想，叙事和抒情结合", "作家与作品：屈原《惜诵》《涉江》《哀郢》《怀沙》《橘颂》"],
    天问体: ["所属：楚辞问答体", "特点：以连续诘问追索宇宙、神话、历史与政治秩序", "作家与作品：屈原《天问》；后世有柳宗元《天对》与之对话"],
    招魂体: ["所属：楚辞招魂辞", "特点：铺陈四方险境与宫室饮食，以反复呼告召魂归来", "作品：《招魂》旧题宋玉或屈原，《大招》作者归属亦有不同说法"],
    汉乐府: ["所属：汉魏古体", "特点：感于哀乐、缘事而发，长于叙事与人物对话", "作品：《孔雀东南飞》《陌上桑》《十五从军征》《战城南》"],
    相和歌辞: ["所属：乐府歌辞", "特点：丝竹相和、歌唱性强，题材涉及征战、游仙与民生", "作品：曹操《短歌行》《蒿里行》，古辞《江南》"],
    鼓吹曲辞: ["所属：军旅仪仗乐府", "特点：节奏劲健，多写征战、凯旋与边地风物", "作品：汉乐府《战城南》《有所思》，曹植《白马篇》承其风格"],
    五言古诗: ["特点：每句五言、不拘近体格律，适合叙事与含蓄抒情", "作品：《古诗十九首·行行重行行》、陶渊明《饮酒·其五》、杜甫《望岳》"],
    七言古诗: ["特点：每句七言，篇幅和换韵较自由，气势舒展", "作品：曹丕《燕歌行》、张若虚《春江花月夜》、李白《蜀道难》"],
    杂言歌行: ["特点：三、五、七言杂用，换韵灵活，长于铺叙和情绪转折", "作品：李白《梦游天姥吟留别》、岑参《白雪歌送武判官归京》、白居易《琵琶行》"],
    柏梁体: ["特点：通篇七言、句句押韵，相传源自汉武帝柏梁台联句", "作品：《柏梁诗》；后世联句与七言古诗常借鉴其句句用韵方式"],
    五言绝句: ["特点：四句、每句五字，常用平声韵，讲究起承转合", "作品：王维《鹿柴》、李白《静夜思》、孟浩然《春晓》"],
    七言绝句: ["特点：四句、每句七字，篇幅短而转折有力", "作品：王昌龄《出塞》、杜牧《赤壁》、王维《送元二使安西》"],
    五言律诗: ["特点：八句五言，中二联通常对仗，平仄与押韵严整", "作品：王维《山居秋暝》、杜甫《春望》、孟浩然《过故人庄》"],
    七言律诗: ["特点：八句七言，颔联、颈联对仗，容量大而章法严密", "作品：杜甫《登高》、崔颢《黄鹤楼》、李商隐《锦瑟》"],
    五言排律: ["特点：十句以上，除首尾联外多连续对仗", "作品：杜甫《奉赠韦左丞丈二十二韵》、白居易《赋得古原草送别》常作排律入门例"],
    七言排律: ["特点：七言长篇律体，多联对仗，适于酬唱、纪事与铺陈", "作品：清代试帖诗及长篇酬唱中较常见，创作须严格遵守粘对规则"],
    五言古风: ["特点：五言古体，不受律诗对仗和平仄限制", "作品：李白《古风》组诗、杜甫《佳人》、陶渊明《归园田居》"],
    七言歌行: ["特点：七言为主，可杂言换韵，音节流走、叙事抒情兼长", "作品：张若虚《春江花月夜》、高适《燕歌行》、白居易《长恨歌》"],
    乐府歌行: ["特点：借乐府旧题或歌行体写现实与抒怀", "作品：李白《将进酒》、杜甫《兵车行》、白居易《卖炭翁》"],
    如梦令: ["词牌：单调三十三字，短促活泼，常以叠句收束", "作品：李清照《如梦令·常记溪亭日暮》《如梦令·昨夜雨疏风骤》"],
    浣溪沙: ["词牌：双调四十二字，上下片各三句，多押平韵", "作品：晏殊《浣溪沙·一曲新词酒一杯》、苏轼《浣溪沙·游蕲水清泉寺》"],
    清平乐: ["词牌：双调四十六字，上片四仄韵、下片三平韵", "作品：晏殊《清平乐·红笺小字》、辛弃疾《清平乐·村居》、黄庭坚《清平乐·春归何处》"],
    水调歌头: ["词牌：双调九十五字，长于铺叙议论与旷达抒情", "作品：苏轼《水调歌头·明月几时有》、辛弃疾《水调歌头·舟次扬州和人韵》"],
    念奴娇: ["词牌：双调一百字左右，音节雄浑，亦可婉约", "作品：苏轼《念奴娇·赤壁怀古》、姜夔《念奴娇·闹红一舸》"],
    天净沙: ["曲牌：越调小令，常见二十八字，句式凝练", "作品：马致远《天净沙·秋思》、白朴《天净沙·秋》"],
    山坡羊: ["曲牌：中吕宫常用曲牌，句式长短错落，适合怀古讽世", "作品：张养浩《山坡羊·潼关怀古》《山坡羊·骊山怀古》，陈草庵《山坡羊·叹世》"],
    元曲小令: ["特点：单支曲牌独立成篇，可加衬字，语言通俗灵动", "作品：马致远《天净沙·秋思》、张养浩《山坡羊·潼关怀古》、乔吉《水仙子·寻梅》"],
    元曲套曲: ["特点：同一宫调若干曲牌联缀，首尾完整，容量较大", "作家与作品：睢景臣《般涉调·哨遍·高祖还乡》、马致远《夜行船·秋思》套数"],
    杂剧唱词: ["特点：按宫调曲牌组织，一折通常由一个角色主唱", "作品：关汉卿《窦娥冤》、王实甫《西厢记》、马致远《汉宫秋》中的曲辞"],
    现代格律诗: ["特点：以现代汉语探索整齐诗节、押韵和节奏规范", "作品：闻一多《死水》、徐志摩《再别康桥》"],
    现代短诗: ["特点：篇幅短、意象集中，重瞬间感受和留白", "作品：冰心《繁星》《春水》、卞之琳《断章》"],
    自由诗: ["特点：不拘固定字数、行数和平仄，以内在节奏组织语言", "作品：艾青《我爱这土地》、郭沫若《天狗》"],
    散文诗: ["特点：以散文句式承载诗性意象、节奏和象征", "作品：鲁迅《野草》、柯蓝等现代散文诗创作"],
    十四行诗: ["特点：十四行结构，汉语创作常借鉴意大利式或莎士比亚式章法", "作品：冯至《十四行集》、卞之琳十四行诗"],
    叙事长诗: ["特点：以较长篇幅塑造人物、展开事件并融入抒情", "作品：闻捷《复仇的火焰》、郭小川《将军三部曲》"],
    ...Object.fromEntries(Object.entries(eraForms).map(([name, items]) => [name, [`所属体裁大类：${name}`, `常见细分：${items.join("、")}`, "悬停外圈具体诗体可查看体式特点、代表作者与作品示例"]])),
  };
  const themeDetails = {
    山水田园: ["王维《山居秋暝》《鹿柴》", "孟浩然《过故人庄》", "陶渊明《归园田居》《饮酒·其五》", "谢灵运《登池上楼》"],
    边塞征战: ["高适《燕歌行》", "岑参《白雪歌送武判官归京》", "王昌龄《出塞》《从军行》", "李贺《雁门太守行》"],
    咏史怀古: ["苏轼《念奴娇·赤壁怀古》", "辛弃疾《永遇乐·京口北固亭怀古》", "杜牧《赤壁》《泊秦淮》", "刘禹锡《乌衣巷》"],
    送别赠别: ["王维《送元二使安西》", "李白《赠汪伦》《黄鹤楼送孟浩然之广陵》", "王勃《送杜少府之任蜀州》", "高适《别董大》"],
    思乡怀人: ["李白《静夜思》", "杜甫《月夜忆舍弟》", "王湾《次北固山下》", "马致远《天净沙·秋思》"],
    爱情闺怨: ["李商隐《无题》", "李清照《一剪梅》", "秦观《鹊桥仙》", "温庭筠《菩萨蛮》"],
    咏物言志: ["于谦《石灰吟》", "王冕《墨梅》", "陆游《卜算子·咏梅》", "郑燮《竹石》"],
    饮酒抒怀: ["李白《将进酒》《月下独酌》", "陶渊明《饮酒·其五》", "苏轼《水调歌头》", "曹操《短歌行》"],
    登临感怀: ["杜甫《登高》《登岳阳楼》", "陈子昂《登幽州台歌》", "王之涣《登鹳雀楼》", "辛弃疾《水龙吟·登建康赏心亭》"],
    忧国忧民: ["杜甫《春望》《茅屋为秋风所破歌》", "陆游《书愤》《示儿》", "文天祥《过零丁洋》", "龚自珍《己亥杂诗》"],
    隐逸闲适: ["陶渊明《归园田居》", "王维《终南别业》", "孟浩然《过故人庄》", "韦应物《滁州西涧》"],
    人生哲思: ["苏轼《题西林壁》", "刘禹锡《酬乐天扬州初逢席上见赠》", "王安石《登飞来峰》", "杨慎《临江仙·滚滚长江东逝水》"],
    季节感兴: ["孟浩然《春晓》", "杜牧《山行》", "刘禹锡《秋词》", "白朴《天净沙·秋》"],
    月夜怀远: ["张九龄《望月怀远》", "杜甫《月夜》", "苏轼《水调歌头》", "张若虚《春江花月夜》"],
    家国兴亡: ["杜牧《泊秦淮》", "辛弃疾《永遇乐·京口北固亭怀古》", "李煜《虞美人》", "文天祥《过零丁洋》"],
    友情交往: ["李白《赠汪伦》", "王勃《送杜少府之任蜀州》", "杜甫《赠卫八处士》", "白居易《问刘十九》"],
    悼亡怀旧: ["苏轼《江城子·乙卯正月二十日夜记梦》", "元稹《遣悲怀》", "纳兰性德《浣溪沙·谁念西风独自凉》", "潘岳《悼亡诗》"],
    边塞乡愁: ["岑参《逢入京使》", "范仲淹《渔家傲·秋思》", "李益《夜上受降城闻笛》", "王昌龄《从军行》"],
  };
  const authorDetails = {
    先秦: ["屈原", "宋玉"],
    汉魏: ["陶渊明", "谢灵运", "曹操", "曹植"],
    唐代: ["李白", "杜甫", "王维", "白居易", "高适", "岑参", "李商隐", "杜牧"],
    宋代: ["苏轼", "李清照", "辛弃疾", "柳永", "陆游", "黄庭坚"],
    元代: ["马致远", "关汉卿", "王冕"],
    明清: ["纳兰性德", "龚自珍", "高启"],
    近现代: ["徐志摩", "冰心", "艾青"],
  };
  const watercolor = Array.from({ length: 19 }, (_, index) => {
    const group = eraShadeGroups[index % eraShadeGroups.length];
    const cycleShade = [6, 0, 3][Math.floor(index / eraShadeGroups.length) % 3];
    return group[cycleShade];
  });
  const themeNames = [
    "山水田园",
    "边塞征战",
    "咏史怀古",
    "送别赠别",
    "思乡怀人",
    "爱情闺怨",
    "咏物言志",
    "饮酒抒怀",
    "登临感怀",
    "忧国忧民",
    "隐逸闲适",
    "人生哲思",
    "季节感兴",
    "月夜怀远",
    "家国兴亡",
    "友情交往",
    "悼亡怀旧",
    "边塞乡愁",
  ];
  const themeCounts = [
    82, 61, 77, 54, 88, 47, 69, 58, 74, 91, 52, 67, 49, 72, 63, 56, 44, 59,
  ];
  const themeRepresentatives = [
    "《山居秋暝》",
    "《燕歌行》",
    "《赤壁怀古》",
    "《送元二使安西》",
    "《静夜思》",
    "《无题》",
    "《墨梅》",
    "《将进酒》",
    "《登高》",
    "《春望》",
    "《饮酒》",
    "《题西林壁》",
    "《春晓》",
    "《望月怀远》",
    "《泊秦淮》",
    "《赠汪伦》",
    "《江城子》",
    "《白雪歌》",
  ];
  const emotionExamples = [
    ["苏轼、辛弃疾、李白", "苏轼《念奴娇·赤壁怀古》；辛弃疾《破阵子·为陈同甫赋壮词以寄之》；李白《将进酒》"],
    ["杜甫、陈子昂、李商隐", "杜甫《登高》；陈子昂《登幽州台歌》；李商隐《锦瑟》"],
    ["晏殊、秦观、欧阳修", "晏殊《浣溪沙·一曲新词酒一杯》；秦观《鹊桥仙》；欧阳修《蝶恋花·庭院深深深几许》"],
    ["王维、孟浩然、谢灵运", "王维《山居秋暝》；孟浩然《春晓》；谢灵运《登池上楼》"],
    ["岑参、高适、范仲淹", "岑参《白雪歌送武判官归京》；高适《燕歌行》；范仲淹《渔家傲·秋思》"],
    ["陶渊明、韦应物、王维", "陶渊明《饮酒·其五》；韦应物《滁州西涧》；王维《终南别业》"],
    ["李清照、纳兰性德、柳永", "李清照《声声慢》；纳兰性德《浣溪沙·谁念西风独自凉》；柳永《雨霖铃》"],
    ["陆游、岳飞、辛弃疾", "陆游《书愤》；岳飞《满江红》；辛弃疾《永遇乐·京口北固亭怀古》"],
    ["柳宗元、马致远、陈子昂", "柳宗元《江雪》；马致远《天净沙·秋思》；陈子昂《登幽州台歌》"],
    ["张九龄、温庭筠、李商隐", "张九龄《望月怀远》；温庭筠《商山早行》；李商隐《夜雨寄北》"],
    ["屈原、杜甫、文天祥", "屈原《离骚》；杜甫《春望》；文天祥《过零丁洋》"],
    ["孟浩然、张若虚、王维", "孟浩然《过故人庄》；张若虚《春江花月夜》；王维《鹿柴》"],
    ["杨万里、辛弃疾、苏轼", "杨万里《小池》；辛弃疾《西江月·夜行黄沙道中》；苏轼《惠崇春江晚景》"],
    ["白居易、元稹、苏轼", "白居易《琵琶行》；元稹《遣悲怀》；苏轼《江城子·乙卯正月二十日夜记梦》"],
    ["李白、李贺、郭沫若", "李白《梦游天姥吟留别》；李贺《梦天》；郭沫若《天上的街市》"],
    ["刘禹锡、杜牧、苏轼", "刘禹锡《乌衣巷》；杜牧《赤壁》；苏轼《念奴娇·赤壁怀古》"],
    ["王勃、柳永、李清照", "王勃《送杜少府之任蜀州》；柳永《雨霖铃》；李清照《一剪梅》"],
    ["陆游、文天祥、龚自珍", "陆游《示儿》；文天祥《过零丁洋》；龚自珍《己亥杂诗》"],
    ["陶渊明、苏轼、王维", "陶渊明《归园田居》；苏轼《定风波》；王维《终南别业》"],
  ];
  const emotionPalette = {
    豪放昂扬: eraShadeGroups[0][3],
    沉郁顿挫: eraShadeGroups[1][3],
    婉约含蓄: eraShadeGroups[2][6],
    清新自然: eraShadeGroups[3][6],
    苍凉悲壮: eraShadeGroups[4][3],
    哀怨凄婉: eraShadeGroups[6][0],
    闲适冲淡: eraShadeGroups[5][6],
    慷慨激昂: eraShadeGroups[0][6],
    孤寂落寞: eraShadeGroups[6][3],
    思念眷恋: eraShadeGroups[2][0],
    忧愤深沉: eraShadeGroups[5][3],
    平和悠远: eraShadeGroups[4][6],
    幽默诙谐: eraShadeGroups[1][6],
    悲怆哀痛: eraShadeGroups[0][5],
    怀古幽思: eraShadeGroups[6][6],
    爱国豪情: eraShadeGroups[0][1],
    浪漫飘逸: eraShadeGroups[1][0],
    离愁别绪: eraShadeGroups[2][3],
    隐逸旷达: eraShadeGroups[3][3],
  };
  const emotionWords = [
    "豪放昂扬", "沉郁顿挫", "婉约含蓄", "清新自然", "苍凉悲壮", "闲适冲淡",
    "哀怨凄婉", "慷慨激昂", "孤寂落寞", "思念眷恋", "忧愤深沉", "平和悠远",
    "幽默诙谐", "悲怆哀痛", "浪漫飘逸", "怀古幽思", "离愁别绪", "爱国豪情", "隐逸旷达",
  ].map((name, index) => ({
    name,
    value: [92, 88, 79, 86, 74, 81, 70, 90, 68, 77, 83, 75, 52, 66, 89, 73, 78, 91, 76][index],
    color: emotionPalette[name],
    meaning: `${name}的古典诗词情感表达`,
    poets: emotionExamples[index][0],
    poem: emotionExamples[index][1],
  }));
  const emotionPositions = [
    [12, 78],
    [30, 84],
    [49, 75],
    [69, 84],
    [87, 72],
    [19, 59],
    [39, 62],
    [58, 57],
    [80, 58],
    [10, 39],
    [29, 42],
    [49, 39],
    [69, 43],
    [89, 37],
    [18, 20],
    [38, 24],
    [58, 19],
    [77, 24],
    [92, 15],
  ];
  const sentimentDetails = Object.fromEntries(
    emotionWords.map((item) => [
      item.name,
      [item.meaning, item.poets, item.poem, `收录权重 ${item.value}`],
    ]),
  );
  const layeredTip = (details, business) => (params) => {
    const name = params.name || params.axisValue;
    const items = details[name] || [];
    return `<b>${name}</b><br/>细分：${items.join("、") || "暂无细分"}<br/><span style="color:#718078">${business}</span>`;
  };
  const targets = [
    [
      "chartTimeline",
      {
        title: {
          text: "千年诗歌演进  Evolution Timeline",
          left: 12,
          top: 4,
          textStyle: { color: "#1F382E", fontSize: 13, fontWeight: 700 },
        },
        grid: { left: 28, right: 18, top: 32, bottom: 25, containLabel: true },
        xAxis: {
          type: "category",
          data: timelineOrder,
          axisLabel: {
            fontSize: 8,
            fontWeight: 700,
            color: "#1F382E",
            interval: 0,
            lineHeight: 12,
            formatter: (value, index) => `${value.replace("唐代", "唐").replace("宋代", "宋").replace("元代", "元").replace("明清", "明/清")}\n${timelineRanges[index]}`,
          },
          axisLine: { lineStyle: { color: "#B8D0C3" } },
          axisTick: { show: false },
        },
        yAxis: { type: "value", show: false },
        series: [
          {
            type: "line",
            smooth: true,
            data: timelineData.map((value, index) => ({
              value,
              name: timelineOrder[index],
              description: timelineDescriptions[timelineOrder[index]],
              itemStyle: {
                color: eraColors[index],
                borderColor: "#FCFDFE",
                borderWidth: 2,
              },
            })),
            symbolSize: 9,
            emphasis: {
              focus: "self",
              scale: 1.4,
              itemStyle: { shadowBlur: 16, shadowColor: "#84A9C0aa" },
            },
            lineStyle: {
              color: new echarts.graphic.LinearGradient(0, 0, 1, 0, [
                { offset: 0, color: eraColors[0] },
                { offset: 0.34, color: eraColors[2] },
                { offset: 0.67, color: eraColors[4] },
                { offset: 1, color: eraColors[6] },
              ]),
              width: 2.5,
            },
            areaStyle: {
              color: new echarts.graphic.LinearGradient(0, 0, 0, 1, [
                { offset: 0, color: "#E5C85748" },
                { offset: 1, color: "#68AEAA08" },
              ]),
            },
          },
        ],
      },
    ],
    [
      "chartForms",
      {
        title: {
          text: "诗歌体裁  Poetry Forms",
          left: 12,
          top: 8,
          textStyle: { color: "#365948", fontSize: 12 },
        },
        series: [
          {
            name: "一级大类",
            type: "pie",
            radius: ["15%", "48%"],
            center: ["50%", "59%"],
            selectedMode: "single",
            minAngle: 3,
            avoidLabelOverlap: true,
            emphasis: {
              scale: true,
              focus: "self",
              itemStyle: { shadowBlur: 0 },
            },
            label: {
              position: "inside",
              fontSize: 5,
              fontWeight: "bold",
              color: "#243b32",
              overflow: "truncate",
            },
            itemStyle: { borderWidth: 0 },
            data: Object.entries(eraForms).map(([name, details], index) => ({
              name,
              value: 1000,
              details,
              itemStyle: { color: traditionalGradient(index, true) },
            })),
            color: eraColors,
          },
          {
            name: "细分条目",
            type: "pie",
            radius: ["51%", "64%"],
            center: ["50%", "59%"],
            selectedMode: "single",
            minAngle: 2,
            avoidLabelOverlap: true,
            emphasis: {
              scale: true,
              scaleSize: 5,
              focus: "self",
              itemStyle: { shadowBlur: 0 },
            },
            label: { fontSize: 5, color: "#607C70", length: 3, length2: 4 },
            labelLine: {
              length: 3,
              length2: 4,
              lineStyle: { width: 0.5, color: "#B8C7BF" },
            },
            itemStyle: { borderWidth: 0 },
            data: Object.entries(eraForms).flatMap(
              ([parent, items], groupIndex) =>
                items.map((name, index) => ({
                  name,
                  value: 1000 / items.length,
                  parent,
                  groupIndex,
                  itemStyle: {
                    color: childColor(groupIndex, index),
                  },
                })),
            ),
          },
        ],
      },
    ],
    [
      "chartThemes",
      {
        title: {
          text: "诗歌主题  Core Themes",
          left: 12,
          top: 8,
          textStyle: { color: "#365948", fontSize: 12 },
        },
        grid: { left: 28, right: 10, top: 36, bottom: 42, containLabel: true },
        xAxis: {
          type: "category",
          data: themeNames,
          axisLine: { lineStyle: { color: "#D9E4ED" } },
          axisTick: { show: false },
          axisLabel: { fontSize: 6, color: "#607C70", interval: 0, rotate: 38 },
        },
        yAxis: { type: "value", show: false },
        series: [
          {
            type: "bar",
            data: themeCounts.map((value, index) => ({
              value,
              name: themeNames[index],
              representative: themeRepresentatives[index],
              itemStyle: { color: watercolor[index % watercolor.length] },
            })),
            barWidth: "55%",
            itemStyle: { borderRadius: [6, 6, 0, 0] },
            emphasis: {
              focus: "self",
              itemStyle: { shadowBlur: 16, shadowColor: "#84A9C0aa" },
            },
          },
        ],
      },
    ],
    [
      "chartAuthors",
      {
        title: {
          text: "千古名家  Classic Poets",
          left: 12,
          top: 8,
          textStyle: { color: "#365948", fontSize: 12 },
        },
        grid: { left: 8, right: 8, top: 34, bottom: 8 },
        xAxis: { min: 0, max: 100, show: false },
        yAxis: { min: 0, max: 100, show: false },
        series: [
          {
            type: "scatter",
            data: Object.keys(poetGroups).map((name, index) => ({
              name,
              value: [
                [12, 55, 34],
                [27, 35, 36],
                [44, 64, 48],
                [62, 43, 44],
                [78, 67, 30],
                [85, 28, 35],
                [66, 17, 31],
              ][index],
              itemStyle: { color: eraColors[index] },
            })),
            symbolSize: (value) => value[2],
            label: {
              show: true,
              formatter: "{b}",
              fontFamily: "FangSong, STFangsong, FangSong_GB2312, serif",
              fontSize: 9,
              fontWeight: 400,
              color: "#1F382E",
            },
            itemStyle: {
              opacity: 1,
              shadowBlur: 0,
            },
            emphasis: {
              focus: "self",
              scale: 1.15,
              itemStyle: { shadowBlur: 18, shadowColor: "#84A9C0aa" },
            },
          },
        ],
      },
    ],
    [
      "chartGraph",
      {
        backgroundColor: "transparent",
        tooltip: {
          formatter: (p) =>
            `${p.data.name}<br/>${p.data.desc || "诗词 Agent 知识关联节点"}`,
        },
        series: [
          {
            type: "graph",
            layout: "force",
            roam: true,
            draggable: true,
            symbolSize: 38,
            label: { show: true, fontSize: 10, color: "#1A2530" },
            force: { repulsion: 180, edgeLength: 70 },
            lineStyle: { color: "#B8C2CC", curveness: 0.12 },
            data: [
              {
                name: "中华诗歌",
                symbolSize: 56,
                itemStyle: { color: "#2F5D50" },
              },
              { name: "唐宋诗词", itemStyle: { color: "#3D6E60" } },
              { name: "CCPC\n古典诗词原文库", itemStyle: { color: "#6E947F" } },
              { name: "CRRD\n平仄格律标注库", itemStyle: { color: "#6C7889" } },
              {
                name: "FSPC\n细粒度情感标注库",
                itemStyle: { color: "#C9924D" },
              },
              { name: "PQED\n文笔四维打分库", itemStyle: { color: "#A65B45" } },
              { name: "山川风月意象", itemStyle: { color: "#D9B873" } },
            ],
            links: [
              { source: "中华诗歌", target: "唐宋诗词" },
              { source: "中华诗歌", target: "CCPC\n古典诗词原文库" },
              {
                source: "CCPC\n古典诗词原文库",
                target: "CRRD\n平仄格律标注库",
              },
              {
                source: "CCPC\n古典诗词原文库",
                target: "FSPC\n细粒度情感标注库",
              },
              {
                source: "CCPC\n古典诗词原文库",
                target: "PQED\n文笔四维打分库",
              },
              { source: "唐宋诗词", target: "山川风月意象" },
            ],
          },
        ],
      },
    ],
    [
      "chartEmotion",
      {
        title: {
          text: "情感基调  Emotional Tones",
          left: 12,
          top: 8,
          textStyle: { color: "#365948", fontSize: 12 },
        },
        grid: { left: 8, right: 8, top: 34, bottom: 8 },
        xAxis: { min: 0, max: 100, show: false },
        yAxis: { min: 0, max: 100, show: false },
        series: [
          {
            name: "情感词云",
            type: "scatter",
            data: emotionWords.map((item, index) => ({
              name: item.name,
              value: [
                emotionPositions[index][0],
                emotionPositions[index][1],
                Math.max(12, Math.round(item.value / 5)),
              ],
              meaning: item.meaning,
              poets: item.poets,
              poem: item.poem,
              itemStyle: { color: item.color },
            })),
            symbol: "rect",
            symbolSize: (data) => [
              Math.max(34, data[2] * 4.5),
              Math.max(18, data[2] * 1.7),
            ],
            label: {
              show: true,
              formatter: "{b}",
              position: "inside",
              fontFamily: "FangSong, STFangsong, FangSong_GB2312, serif",
              fontSize: (p) => Math.min(15, p.data.value[2] + 1),
              fontWeight: 400,
              color: "#FFFFFF",
              textShadowBlur: 3,
              textShadowColor: "rgba(31,56,46,.35)",
            },
            itemStyle: {
              color: "rgba(255,255,255,0)",
              borderColor: "rgba(255,255,255,0)",
              opacity: 1,
            },
            emphasis: {
              focus: "self",
              label: {
                fontWeight: 900,
                textShadowBlur: 10,
                textShadowColor: "#84A9C0aa",
              },
              itemStyle: { color: "rgba(255,255,255,0)", opacity: 1 },
            },
          },
        ],
      },
    ],
  ];
  const tooltipMap = {
    chartTimeline: [dynastyDetails, "点击查看该朝代的体裁、名家与发展特征"],
    chartForms: [formDetails, "点击查看该体裁大类或细分条目"],
    chartThemes: [themeDetails, "点击查看该主题的数量与代表篇目"],
    chartAuthors: [authorDetails, "点击时代节点可展开该时期代表诗人"],
    chartEmotion: [sentimentDetails, "点击查看该情感的释义、诗人与代表作品"],
  };
  targets.forEach(([id, opt]) => {
    const el = document.querySelector(`#${id}`);
    if (!el) return;
    opt.textStyle = {
      ...(opt.textStyle || {}),
      fontFamily: "FangSong, STFangsong, FangSong_GB2312, serif",
      fontWeight: 400,
    };
    if (opt.title?.textStyle)
      opt.title.textStyle.fontFamily =
        "FangSong, STFangsong, FangSong_GB2312, serif";
    const detail = tooltipMap[id];
    if (detail)
      opt.tooltip = {
        trigger: "item",
        confine: true,
        backgroundColor: "#FCFDFEf2",
        borderColor: "#D9E4ED",
        extraCssText:
          "box-shadow:0 10px 30px rgba(47,93,80,.16);border-radius:12px;backdrop-filter:blur(8px);",
        textStyle: { color: "#607C70", fontSize: 10 },
        formatter: (params) =>
          id === "chartThemes"
            ? `<div style="max-width:380px;white-space:normal;line-height:1.65"><b>${params.name}</b><br/>诗词数量：${params.value}<br/>代表诗人与作品：<br/>${(themeDetails[params.name] || [params.data.representative]).join("<br/>")}</div>`
            : id === "chartEmotion"
              ? `<div style="max-width:390px;white-space:normal;line-height:1.65"><b>${params.name}</b><br/>${params.data.meaning}<br/>代表诗人：${params.data.poets}<br/>代表作品：<br/>${params.data.poem.replaceAll("；", "<br/>")}</div>`
              : id === "chartTimeline"
                ? `<div style="max-width:340px;white-space:normal;line-height:1.65"><b>${params.name}</b><br/>语料相对收录量：${Number(params.value).toLocaleString()}<br/><span style="color:#8A7963">仅表示当前项目语料覆盖，不代表历史作品总量</span><br/>${(dynastyDetails[params.name] || []).join("<br/>")}</div>`
                : id === "chartAuthors" && poetBios[params.name]
                  ? `<div style="max-width:320px;white-space:normal;line-height:1.6"><b>${params.name}</b><br/>${poetBios[params.name]}</div>`
                  : params.seriesName === "细分条目"
                    ? `<div style="max-width:360px;white-space:normal;line-height:1.65"><b>${params.name}</b><br/>${formDetails[params.name].join("<br/>")}</div>`
                    : params.data?.details
                      ? `<div style="max-width:340px;white-space:normal;line-height:1.65"><b>${params.name}</b><br/>${(formDetails[params.name] || params.data.details).join("<br/>")}<br/><span style="color:#718078">点击可高亮该大类及其细分体裁</span></div>`
                      : layeredTip(detail[0], detail[1])(params),
      };
    opt.animationDuration = 900;
    opt.animationEasing = "cubicOut";
    const c = echarts.init(el);
    c.setOption(opt);
    c.on("mouseover", (params) => {
      if (params.seriesIndex == null) return;
      if (id === "chartForms" && params.seriesName === "细分条目") {
        const outerData = opt.series[1].data;
        outerData.forEach((item, index) =>
          c.dispatchAction({
            type:
              item.parent === params.data.parent && index !== params.dataIndex
                ? "downplay"
                : "highlight",
            seriesIndex: 1,
            dataIndex: index,
          }),
        );
      } else
        c.dispatchAction({
          type: "highlight",
          seriesIndex: params.seriesIndex,
          dataIndex: params.dataIndex,
        });
    });
    c.on("mouseout", () => {
      c.dispatchAction({ type: "downplay", seriesIndex: "all" });
      if (id === "chartForms")
        c.setOption({ series: [{}, { itemStyle: { opacity: 1 } }] });
    });
    c.on("click", (params) => {
      if (id === "chartAuthors" && poetGroups[params.name]) {
        expandedPoetEra.value =
          expandedPoetEra.value === params.name ? "" : params.name;
        const base = eraNames.map((name, index) => ({
          name,
          value: [
            [12, 55, 34],
            [27, 35, 36],
            [44, 64, 48],
            [62, 43, 44],
            [78, 67, 30],
            [85, 28, 35],
            [66, 17, 31],
          ][index],
          itemStyle: { color: eraColors[index] },
        }));
        const poets = expandedPoetEra.value
          ? poetGroups[expandedPoetEra.value].map((name, index) => {
              const eraIndex = eraNames.indexOf(expandedPoetEra.value);
              const center = base[eraIndex].value;
              const count = poetGroups[expandedPoetEra.value].length;
              const angle = (index * 2 * Math.PI) / count;
              const radiusX = count > 6 ? 18 : 14;
              const radiusY = count > 6 ? 23 : 17;
              return {
                name,
                value: [
                  Math.max(
                    6,
                    Math.min(94, center[0] + Math.cos(angle) * radiusX),
                  ),
                  Math.max(
                    8,
                    Math.min(92, center[1] + Math.sin(angle) * radiusY),
                  ),
                  20,
                ],
                parent: expandedPoetEra.value,
                itemStyle: {
                  color: echarts.color.modifyHSL(
                    eraColors[eraIndex],
                    null,
                    null,
                    76,
                  ),
                  opacity: 0.95,
                  shadowBlur: 7,
                  shadowColor: eraColors[eraIndex] + "66",
                },
              };
            })
          : [];
        c.setOption({ series: [{ data: [...base, ...poets] }] });
      }
      c.dispatchAction({ type: "downplay", seriesIndex: "all" });
      c.dispatchAction({
        type: "highlight",
        seriesIndex: params.seriesIndex,
        dataIndex: params.dataIndex,
      });
    });
    charts.push(c);
  });
}

async function openData() {
  showData.value = true;
  await nextTick();
  renderCharts();
}

function resetDrafts() {
  if (busy.value) return;
  draftQuery.value = "";
  draftPoem.value = "";
  form.value = "不限";
  emotion.value = "";
  genreExtension.value = "";
  emotionExtension.value = "";
  themes.value = [];
  selectedGenreGroup.value = "不限";
  selectedEmotionGroup.value = "不限";
  selectedThemeGroup.value = "不限";
  themeDetail.value = "";
  query.value = "";
  poem.value = "";
  answer.value = "";
  trace.value = [];
  analysis.value = [];
  showReport.value = false;
  report.value = {};
  streamStage.value = "待输入";
}

watch(task, () => {
  if (busy.value) return;
  streamStage.value = "待输入";
});

onMounted(async () => {
  try {
    const [h, a] = await Promise.all([
      fetch("/api/health").then((r) => r.json()),
      fetch("/api/analytics").then((r) => r.json()),
    ]);
    liveEnabled.value = Boolean(h.live?.enabled);
    status.value = liveEnabled.value
      ? "GPT-Live 已就绪"
      : h.model || h.live?.enabled
        ? "服务已就绪"
        : "服务待配置";
    analytics.value = a;
    await refreshWorkspace();
  } catch {
    status.value = "服务暂不可用";
  }

  await nextTick();
  renderCharts();
  window.addEventListener("resize", () => charts.forEach((c) => c.resize()));
});

onUnmounted(() => charts.forEach((c) => c.dispose()));
</script>

<template>
  <div class="aurora one"></div>
  <div class="aurora two"></div>
  <div class="shell">
    <header class="glass">
      <div class="brand">
        <i>诗</i>
        <div>
          <b>诗承</b>
          <small>POETRY INTELLIGENCE</small>
        </div>
      </div>
    </header>

    <main>
      <aside>
        <div class="hero">
          <small>智能诗歌学习空间</small>
          <h1>读诗，<br />写诗，<br /><em>懂诗。</em></h1>
          <p>让创作有灵感，让阅读有回响。</p>
        </div>
        <nav class="glass">
          <button
            v-for="(item, key) in tasks"
            :key="key"
            type="button"
            :class="{ active: task === key }"
            @click="selectTask(key)"
          >
            <i>{{ item.icon }}</i>
            <span>
              <b>{{ item.name }}</b>
              <small>{{ item.desc }}</small>
            </span>
          </button>
        </nav>
        <div class="dataset-mini glass" v-if="analytics">
          <b>中华诗歌多标注语料</b>
          <span
            >{{ analytics.totals.ccpc.toLocaleString() }} 首诗词 ·
            {{ analytics.totals.chinese_poetry.toLocaleString() }}
            首中华诗歌</span
          >
          <span
            >{{ analytics.totals.fspc.toLocaleString() }} 条情感 ·
            {{ analytics.totals.pqed.toLocaleString() }} 条质量标尺</span
          >
          <span
            >{{ analytics.totals.rhyme_groups }} 个韵部 ·
            {{ analytics.totals.ping_chars }} 个平声字 ·
            {{ analytics.totals.ze_chars }} 个仄声字</span>
          <span>混合 RAG 检索 · 向量召回 · 重排序 · 原文核验</span>
        </div>
      </aside>

      <section class="work glass liquid">
        <div class="head">
          <div>
            <small>{{ task.toUpperCase() }} Agent</small>
            <h2>{{ tasks[task].title }}</h2>
            <p>{{ tasks[task].desc }}</p>
          </div>
        </div>

        <div class="agent-contract">
          <b>功能</b>
          <span>{{ tasks[task].contract }}</span>
        </div>

        <div class="compose-panel">
          <label>{{ tasks[task].name }}输入与回复</label>
          <textarea
            v-model="draftQuery"
            :placeholder="currentPrompt"
            class="main-input input-answer"
            rows="7"
          />
          <div class="reply-stream" :class="{ empty: !answer }">
            <template v-if="answer">
              <p v-for="(paragraph, index) in answer.split(/\n{2,}/)" :key="index">{{ paragraph }}</p>
            </template>
            <span v-else>{{ outputPlaceholder }}</span>
          </div>
        </div>

        <template v-if="task === 'generate'">
          <div class="filter-section">
            <label>体裁</label>
            <div class="generation-select-row">
              <select class="generation-select" v-model="selectedGenreGroup" @change="genreExtension = ''; form = selectedGenreGroup; openFilter = ''">
                <option value="不限">不限</option>
                <option v-for="group in Object.keys(genreFilterGroups)" :key="group" :value="group">{{ group }}</option>
              </select>
              <select class="generation-select" v-model="genreExtension" :disabled="selectedGenreGroup === '不限'" @change="form = genreExtension || selectedGenreGroup">
                <option value="">{{ selectedGenreGroup === '不限' ? '请先选择体裁大类' : '不限具体诗体 / 词牌' }}</option>
                <option v-for="item in genreFilterGroups[selectedGenreGroup] || []" :key="item" :value="item">{{ item }}</option>
              </select>
            </div>
            <div class="compound-row legacy-options">
              <button
                class="compound plain"
                :class="{ selected: selectedGenreGroup === '不限' }"
                @click="
                  selectedGenreGroup = '不限';
                  genreExtension = '';
                  form = '不限';
                  openFilter = '';
                "
              >
                不限
              </button>
              <div
                v-for="(items, group) in genreFilterGroups"
                :key="group"
                class="compound-wrap"
              >
                <button
                  class="compound"
                  :class="{ selected: selectedGenreGroup === group }"
                  @click="
                    selectedGenreGroup = group;
                    form = group;
                  "
                >
                  <span
                    @click.stop="
                      openFilter =
                        openFilter === `g-${group}` ? '' : `g-${group}`
                    "
                    >{{
                      selectedGenreGroup === group && genreExtension
                        ? genreExtension
                        : group
                    }}</span
                  >
                </button>
                <div v-if="openFilter === `g-${group}`" class="frost-menu">
                  <button
                    v-for="item in items"
                    :key="item"
                    @click="
                      genreExtension = item;
                      form = item;
                      selectedGenreGroup = group;
                      openFilter = '';
                    "
                  >
                    {{ item }}
                  </button>
                </div>
              </div>
            </div>
          </div>
          <div class="filter-section">
            <label>情感基调</label>
            <div class="generation-select-row">
              <select class="generation-select" v-model="selectedEmotionGroup" @change="emotionExtension = ''; emotion = selectedEmotionGroup === '不限' ? '' : selectedEmotionGroup; openFilter = ''">
                <option value="不限">不限</option>
                <option v-for="group in Object.keys(emotionGroups)" :key="group" :value="group">{{ group }}</option>
              </select>
              <select class="generation-select" v-model="emotionExtension" :disabled="selectedEmotionGroup === '不限'" @change="emotion = emotionExtension || selectedEmotionGroup">
                <option value="">{{ selectedEmotionGroup === '不限' ? '请先选择情感大类' : '不限具体情感' }}</option>
                <option v-for="item in emotionGroups[selectedEmotionGroup] || []" :key="item" :value="item">{{ item }}</option>
              </select>
            </div>
            <div class="compound-row legacy-options">
              <button
                class="compound plain"
                :class="{ selected: selectedEmotionGroup === '不限' }"
                @click="
                  selectedEmotionGroup = '不限';
                  emotionExtension = '';
                  openFilter = '';
                "
              >
                不限
              </button>
              <div
                v-for="(items, group) in emotionGroups"
                :key="group"
                class="compound-wrap"
              >
                <button
                  class="compound"
                  :class="{ selected: selectedEmotionGroup === group }"
                  @click="selectedEmotionGroup = group"
                >
                  <span
                    @click.stop="
                      openFilter =
                        openFilter === `e-${group}` ? '' : `e-${group}`
                    "
                    >{{
                      selectedEmotionGroup === group && emotionExtension
                        ? emotionExtension
                        : group
                    }}</span
                  >
                </button>
                <div v-if="openFilter === `e-${group}`" class="frost-menu">
                  <button
                    v-for="item in items"
                    :key="item"
                    @click="
                      emotionExtension = item;
                      selectedEmotionGroup = group;
                      openFilter = '';
                    "
                  >
                    {{ item }}
                  </button>
                </div>
              </div>
            </div>
          </div>
          <div class="filter-section">
            <label>题材风格</label>
            <select class="generation-select" v-model="selectedThemeGroup" @change="themeDetail = ''; themes = selectedThemeGroup === '不限' ? [] : [selectedThemeGroup]; openFilter = ''">
              <option value="不限">不限</option>
              <option v-for="group in Object.keys(themeGroups)" :key="group" :value="group">{{ group }}</option>
            </select>
            <div class="compound-row legacy-options">
              <button
                class="compound plain"
                :class="{ selected: selectedThemeGroup === '不限' }"
                @click="
                  selectedThemeGroup = '不限';
                  themeDetail = '';
                  themes = [];
                  openFilter = '';
                "
              >
                不限
              </button>
              <div
                v-for="(items, group) in themeGroups"
                :key="group"
                class="compound-wrap"
              >
                <button
                  class="compound"
                  :class="{ selected: selectedThemeGroup === group }"
                  @click="
                    selectedThemeGroup = group;
                    themes = [group];
                  "
                >
                  <span
                    @click.stop="
                      openFilter =
                        openFilter === `t-${group}` ? '' : `t-${group}`
                    "
                    >{{
                      selectedThemeGroup === group && themeDetail
                        ? themeDetail
                        : group
                    }}</span
                  >
                </button>
                <div v-if="openFilter === `t-${group}`" class="frost-menu">
                  <button
                    v-for="item in items"
                    :key="item"
                    @click="
                      themeDetail = item;
                      themes = [item];
                      selectedThemeGroup = group;
                      openFilter = '';
                    "
                  >
                    {{ item }}
                  </button>
                </div>
              </div>
            </div>
          </div>
        </template>

        <div class="voice-monitor" :class="{ active: voiceActive }">
          <span>{{ voiceMode }} · {{ liveEnabled ? "GPT-Live 全双工在线" : "实时服务待配置" }}</span>
          <div><i :style="{ width: `${voiceLevel}%` }"></i></div>
          <small v-if="voiceActive">语义 VAD · 实时转写 · 流式语音生成 · 支持插话打断</small>
          <small v-else>{{ voiceFrames ? `本轮已采集 ${voiceFrames} 帧音频` : "开启后可边说边听，无需等待整轮结束" }}</small>
        </div>

        <div class="actions">
          <button class="ghost" :disabled="busy" @click="openWorkspace">历史记录</button>
          <button v-if="busy || audioPlaying" class="ghost" @click="interrupt">打断回答</button>
          <button
            class="ghost voice-entry"
            :class="{ active: voiceActive }"
            @click="toggleVoice"
          >
            {{ voiceActive ? "结束实时对话" : "开启 GPT-Live 实时对话" }}
          </button>
          <button class="ghost" :disabled="busy" @click="resetDrafts">
            清空
          </button>
          <button
            type="button"
            class="primary"
            :disabled="busy || !draftQuery.trim()"
            @click="submit"
          >
            {{ busy ? "生成中…" : "发送并生成" }}
          </button>
        </div>
      </section>


      <section class="chart-panel glass liquid">
        <div class="head">
          <div>
            <small>中华诗歌千年演进</small>
            <h2>中华诗歌图谱</h2>
          </div>
          <p class="atlas-note">
            图谱基于古典诗词原文、平仄押韵格律、细粒度情感、文笔四维评价及开源中华诗词数据构建；点击图表可高亮关联维度。
          </p>
        </div>
        <div class="era-keywords">
          <span>先秦<small>楚辞发源</small></span
          ><span>汉魏<small>乐府古体</small></span
          ><span>唐<small>格律成熟</small></span
          ><span>宋<small>词体鼎盛</small></span
          ><span>元<small>散曲兴起</small></span
          ><span>明/清<small>诗词复古延续</small></span
          ><span>近现代<small>白话新诗转型</small></span>
        </div>
        <div class="atlas-grid evolution-atlas">
          <div id="chartTimeline" class="atlas-card timeline"></div>
          <div id="chartForms" class="atlas-card"></div>
          <div id="chartThemes" class="atlas-card"></div>
          <div id="chartAuthors" class="atlas-card"></div>
          <div id="chartEmotion" class="atlas-card"></div>
        </div>
      </section>
    </main>
    <footer class="copyright">
      <span>© 2026 BUPT_Mint-Green</span>
      <span>All rights reserved.</span>
    </footer>
  </div>

  <div class="modal" v-if="showWorkspace" @click.self="showWorkspace = false">
    <section class="workspace-drawer glass">
      <header>
        <div><small>HISTORY</small><h3>{{ tasks[task].name }} · 历史记录</h3></div>
        <div class="workspace-header-actions">
          <button type="button" class="ghost danger" @click="showClearConfirm = true">清除记录</button>
          <button type="button" class="ghost" @click="showWorkspace = false">关闭</button>
        </div>
      </header>
      <div class="workspace-tabs">
        <section>
          <h4>{{ tasks[task].name }}记录</h4>
          <small class="history-scope-note">不同功能的历史相互独立，避免创作条件、批改意见和赏析上下文互相干扰。</small>
          <article v-for="item in workspace.history || []" :key="item.id" class="history-item">
            <b>{{ item.role === 'user' ? '你' : '诗承' }}</b>
            <time :datetime="item.created_at">{{ formatHistoryTime(item.created_at) }}</time>
            <p>{{ cleanHistoryContent(item.content) }}</p>
            <button class="ghost mini" @click="rollbackTo(item.id)">从此处分叉</button>
          </article>
          <em v-if="!workspace.history?.length">暂无聊天记录</em>
        </section>
        <section>
          <h4>对话分支</h4>
          <button v-for="item in workspace.branches || []" :key="item.id" class="branch-item" :class="{ active: item.id === workspace.branch_id }" @click="switchBranch(item.id)">
            {{ item.name }} · {{ item.message_count }} 条消息
          </button>
          <button class="ghost" @click="forkBranch()">分叉当前分支</button>
          <h4>长期记忆</h4>
          <article v-for="item in workspace.memories || []" :key="item.id" class="memory-item">
            <span>{{ item.kind }} · {{ item.content }}</span>
            <button class="ghost mini" @click="removeMemory(item.id)">删除</button>
          </article>
          <em v-if="!workspace.memories?.length">明确表达偏好、修改习惯或薄弱点后自动积累</em>
          <h4>工具工作记录</h4>
          <p v-for="(item, index) in workspace.trace || []" :key="index">{{ item.tool_label || toolLabels[item.tool_name] || "辅助工具" }} · {{ item.status_label || toolStatusLabel(item.status) }} · {{ item.display_summary || toolSummaryLabel(item) }}</p>
        </section>
      </div>
    </section>
  </div>

  <div class="modal confirm-modal" v-if="showClearConfirm" @click.self="showClearConfirm = false">
    <section class="confirm-dialog glass">
      <small>CLEAR HISTORY</small>
      <h3>清除历史记录？</h3>
      <p>确定清除“{{ tasks[task].name }}”的全部历史记录吗？此操作无法撤销。</p>
      <div class="confirm-actions">
        <button type="button" class="ghost" :disabled="clearingHistory" @click="showClearConfirm = false">取消</button>
        <button type="button" class="danger-confirm" :disabled="clearingHistory" @click="clearHistory">
          {{ clearingHistory ? "正在清除…" : "确认清除" }}
        </button>
      </div>
    </section>
  </div>

  <div class="report-drawer glass" v-if="showReport">
    <header>
      <div>
        <small>THU MULTI-ANNOTATION</small>
        <h3>多标注分析报告</h3>
      </div>
      <button @click="showReport = false">收起</button>
    </header>
    <div class="report-grid">
      <section class="rhythm-detail" v-if="report.rhythm">
        <h4>CRRD 逐字声律</h4>
        <div class="poem-lines">
          <div v-for="(line, i) in report.rhythm.characters" :key="i">
            <span
              v-for="item in line"
              :key="item.position"
              :class="[
                'tone',
                item.tone === '平'
                  ? 'ping'
                  : item.tone === '仄'
                    ? 'ze'
                    : 'unknown',
                { rhyme: item.rhyme },
              ]"
            >
              <b>{{ item.char }}</b>
              <small>{{ item.tone }}</small>
            </span>
          </div>
        </div>
        <p>
          {{ report.rhythm.errors?.join("；") || "当前规则检查未发现明显问题" }}
        </p>
      </section>
      <section v-if="report.sentiment">
        <h4>FSPC 情感对照</h4>
        <div id="emotionChart" class="report-chart"></div>
      </section>
      <section v-if="report.quality">
        <h4>PQED 质量维度</h4>
        <div id="qualityChart" class="report-chart"></div>
      </section>
    </div>
    <section class="evidence" v-if="report.evidence?.length">
      <h4>检索证据</h4>
      <div>
        <article
          v-for="item in report.evidence"
          :key="item.title + item.content"
        >
          <header>
            <b>《{{ item.title }}》</b>
            <span>{{ item.author }} · {{ item.dynasty }}</span>
          </header>
          <p>{{ item.content }}</p>
          <footer>
            <i>{{ item.source }}</i>
            <span v-if="item.score"
              >相关性 {{ Math.round(item.score * 100) }}%</span
            >
          </footer>
        </article>
      </div>
    </section>
  </div>

  <div class="modal" v-if="showData" @click.self="showData = false">
    <section class="dashboard glass">
      <header>
        <div>
          <small>CHINESE POETRY DATASET</small>
          <h2>中华诗歌多标注图谱</h2>
        </div>
        <button @click="showData = false">关闭</button>
      </header>
      <div class="totals">
        <div v-for="(v, k) in analytics?.totals || {}" :key="k">
          <b>{{ Number(v).toLocaleString() }}</b
          ><span>{{ k }}</span>
        </div>
      </div>
      <div class="charts">
        <div
          v-for="i in 3"
          :key="i"
          :ref="(el) => (chartEls[i - 1] = el)"
        ></div>
      </div>
      <div class="usage">
        <div v-for="(v, k) in analytics.usage" :key="k">
          <b>{{ k }}</b
          ><span>{{ v }}</span>
        </div>
      </div>
    </section>
  </div>
</template>