"""
A-Share (China Stock) Scanner for FinClaw
==========================================
Scans major A-share stocks and recommends buys based on technical indicators.
Uses yfinance with .SS (Shanghai) and .SZ (Shenzhen) suffixes.
"""

from __future__ import annotations

import sys
import numpy as np
from typing import Optional

from src.ta import rsi, macd, bollinger_bands, sma, adx_full


# ── Stock Universe ───────────────────────────────────────────────────

# Legacy alias – kept for backward compatibility
TOP50 = [
    ('600519.SS', '贵州茅台', 'consumer'),
    ('300750.SZ', '宁德时代', 'manufacturing'),
    ('002594.SZ', '比亚迪', 'manufacturing'),
    ('600036.SS', '招商银行', 'bank'),
    ('601318.SS', '中国平安', 'bank'),
    ('000858.SZ', '五粮液', 'consumer'),
    ('601899.SS', '紫金矿业', 'energy'),
    ('600900.SS', '长江电力', 'energy'),
    ('000333.SZ', '美的集团', 'manufacturing'),
    ('300059.SZ', '东方财富', 'tech'),
    ('002230.SZ', '科大讯飞', 'tech'),
    ('002415.SZ', '海康威视', 'tech'),
    ('600276.SS', '恒瑞医药', 'pharma'),
    ('300760.SZ', '迈瑞医疗', 'pharma'),
    ('601012.SS', '隆基绿能', 'energy'),
    ('600031.SS', '三一重工', 'manufacturing'),
    ('601888.SS', '中国中免', 'consumer'),
    ('000725.SZ', '京东方A', 'tech'),
    ('002475.SZ', '立讯精密', 'tech'),
    ('688981.SS', '中芯国际', 'tech'),
    ('002714.SZ', '牧原股份', 'consumer'),
    ('601633.SS', '长城汽车', 'manufacturing'),
    ('600809.SS', '山西汾酒', 'consumer'),
    ('002352.SZ', '顺丰控股', 'manufacturing'),
    ('600030.SS', '中信证券', 'bank'),
    ('601668.SS', '中国建筑', 'manufacturing'),
    ('601398.SS', '工商银行', 'bank'),
    ('601288.SS', '农业银行', 'bank'),
    ('000002.SZ', '万科A', 'manufacturing'),
    ('603288.SS', '海天味业', 'consumer'),
    ('600887.SS', '伊利股份', 'consumer'),
    ('000651.SZ', '格力电器', 'manufacturing'),
    ('601166.SS', '兴业银行', 'bank'),
    ('600585.SS', '海螺水泥', 'manufacturing'),
    ('601857.SS', '中国石油', 'energy'),
    ('600050.SS', '中国联通', 'tech'),
    ('000568.SZ', '泸州老窖', 'consumer'),
    ('601088.SS', '中国神华', 'energy'),
    ('600309.SS', '万华化学', 'manufacturing'),
    ('002304.SZ', '洋河股份', 'consumer'),
]

# ── Expanded Universe (~310 stocks) ──────────────────────────────────
# Sectors: ai, chip, optical, storage, software, robot, tech, ev,
#          consumer, energy, pharma, manufacturing, solar, military,
#          liquor, real_estate, telecom, bank

CN_UNIVERSE: list[tuple[str, str, str]] = [
    # ══════════════════════════════════════════════════════════════
    # bank / 金融 (17)
    # ══════════════════════════════════════════════════════════════
    ('600036.SS', '招商银行', 'bank'),
    ('601318.SS', '中国平安', 'bank'),
    ('600030.SS', '中信证券', 'bank'),
    ('601398.SS', '工商银行', 'bank'),
    ('601288.SS', '农业银行', 'bank'),
    ('601166.SS', '兴业银行', 'bank'),
    ('601939.SS', '建设银行', 'bank'),
    ('600000.SS', '浦发银行', 'bank'),
    ('601328.SS', '交通银行', 'bank'),
    ('600016.SS', '民生银行', 'bank'),
    ('600015.SS', '华夏银行', 'bank'),
    ('601818.SS', '光大银行', 'bank'),
    ('601788.SS', '光大证券', 'bank'),
    ('600837.SS', '海通证券', 'bank'),
    ('601211.SS', '国泰君安', 'bank'),
    ('601601.SS', '中国太保', 'bank'),
    ('601628.SS', '中国人寿', 'bank'),

    # ══════════════════════════════════════════════════════════════
    # ai / AI概念 (25)
    # ══════════════════════════════════════════════════════════════
    ('002230.SZ', '科大讯飞', 'ai'),
    ('688041.SS', '海光信息', 'ai'),
    ('688256.SS', '寒武纪', 'ai'),
    ('603019.SS', '中科曙光', 'ai'),
    ('000977.SZ', '浪潮信息', 'ai'),
    ('300229.SZ', '拓尔思', 'ai'),
    ('688111.SS', '金山办公', 'ai'),
    ('300418.SZ', '昆仑万维', 'ai'),
    ('601360.SS', '三六零', 'ai'),
    ('688327.SS', '云从科技', 'ai'),
    ('300459.SZ', '汤姆猫', 'ai'),
    ('688618.SS', '三旺通信', 'ai'),
    ('300515.SZ', '三德科技', 'ai'),
    ('300364.SZ', '中文在线', 'ai'),
    ('688088.SS', '虹软科技', 'ai'),
    ('0302.HK', '中手游', 'ai'),
    ('9698.HK', '万国数据', 'ai'),
    ('2400.HK', '心动公司', 'ai'),
    ('688168.SS', '安博通', 'ai'),
    ('300188.SZ', '美亚柏科', 'ai'),
    ('688158.SS', '优刻得', 'ai'),
    ('9888.HK', '百度集团', 'ai'),
    ('1024.HK', '快手', 'ai'),
    ('6185.HK', '商汤', 'ai'),
    ('688680.SS', '海天瑞声', 'ai'),

    # ══════════════════════════════════════════════════════════════
    # chip / 芯片 (29)
    # ══════════════════════════════════════════════════════════════
    ('603501.SS', '韦尔股份', 'chip'),
    ('002371.SZ', '北方华创', 'chip'),
    ('688012.SS', '中微公司', 'chip'),
    ('300782.SZ', '卓胜微', 'chip'),
    ('300661.SZ', '圣邦股份', 'chip'),
    ('600584.SS', '长电科技', 'chip'),
    ('688347.SS', '华虹公司', 'chip'),
    ('688099.SS', '晶晨股份', 'chip'),
    ('603160.SS', '汇顶科技', 'chip'),
    ('688536.SS', '思瑞浦', 'chip'),
    ('300327.SZ', '中颖电子', 'chip'),
    ('688521.SS', '芯原股份', 'chip'),
    ('688120.SS', '华海清科', 'chip'),
    ('688048.SS', '长光华芯', 'chip'),
    ('688072.SS', '拓荆科技', 'chip'),
    ('300474.SZ', '景嘉微', 'chip'),
    ('688047.SS', '龙芯中科', 'chip'),
    ('688126.SS', '沪硅产业', 'chip'),
    ('300346.SZ', '南大光电', 'chip'),
    ('688037.SS', '芯源微', 'chip'),
    ('1347.HK', '华虹半导体', 'chip'),
    ('688135.SS', '利扬芯片', 'chip'),
    ('688052.SS', '纳芯微', 'chip'),
    ('002049.SZ', '紫光国微', 'chip'),
    ('688981.SS', '中芯国际', 'chip'),
    ('300672.SZ', '国科微', 'chip'),
    ('688018.SS', '乐鑫科技', 'chip'),
    ('002156.SZ', '通富微电', 'chip'),
    ('0981.HK', '中芯国际H', 'chip'),

    # ══════════════════════════════════════════════════════════════
    # optical / 光模块光通信 (13)
    # ══════════════════════════════════════════════════════════════
    ('300308.SZ', '中际旭创', 'optical'),
    ('300394.SZ', '天孚通信', 'optical'),
    ('300502.SZ', '新易盛', 'optical'),
    ('002281.SZ', '光迅科技', 'optical'),
    ('300570.SZ', '太辰光', 'optical'),
    ('688498.SS', '源杰科技', 'optical'),
    ('000988.SZ', '华工科技', 'optical'),
    ('603083.SS', '剑桥科技', 'optical'),
    ('300602.SZ', '飞荣达', 'optical'),
    ('300548.SZ', '博创科技', 'optical'),
    ('688629.SS', '华丰科技', 'optical'),
    ('002456.SZ', '欧菲光', 'optical'),
    ('2382.HK', '舜宇光学', 'optical'),

    # ══════════════════════════════════════════════════════════════
    # storage / 存储半导体 (11)
    # ══════════════════════════════════════════════════════════════
    ('603986.SS', '兆易创新', 'storage'),
    ('300223.SZ', '北京君正', 'storage'),
    ('688008.SS', '澜起科技', 'storage'),
    ('688002.SS', '睿创微纳', 'storage'),
    ('688525.SS', '佰维存储', 'storage'),
    ('301308.SZ', '江波龙', 'storage'),
    ('300042.SZ', '朗科科技', 'storage'),
    ('000021.SZ', '深科技', 'storage'),
    ('688396.SS', '华润微', 'storage'),
    ('300101.SZ', '振芯科技', 'storage'),
    ('002185.SZ', '华天科技', 'storage'),

    # ══════════════════════════════════════════════════════════════
    # software / 软件 (20) — NEW SECTOR
    # ══════════════════════════════════════════════════════════════
    ('688083.SS', '中望软件', 'software'),
    ('688023.SS', '安恒信息', 'software'),
    ('300624.SZ', '万兴科技', 'software'),
    ('688588.SS', '凌志软件', 'software'),
    ('300579.SZ', '数字认证', 'software'),
    ('603039.SS', '泛微网络', 'software'),
    ('688078.SS', '龙软科技', 'software'),
    ('300768.SZ', '迪普科技', 'software'),
    ('688232.SS', '新点软件', 'software'),
    ('0268.HK', '金蝶国际', 'software'),
    ('300369.SZ', '绿盟科技', 'software'),
    ('688561.SS', '奇安信', 'software'),
    ('300454.SZ', '深信服', 'software'),
    ('002212.SZ', '天融信', 'software'),
    ('2013.HK', '微盟集团', 'software'),
    ('300033.SZ', '同花顺', 'software'),
    ('300044.SZ', '赛为智能', 'software'),
    ('300378.SZ', '鼎捷软件', 'software'),
    ('300253.SZ', '卫宁健康', 'software'),
    ('300075.SZ', '数字政通', 'software'),

    # ══════════════════════════════════════════════════════════════
    # robot / 机器人自动化 (12) — NEW SECTOR
    # ══════════════════════════════════════════════════════════════
    ('688169.SS', '石头科技', 'robot'),
    ('300024.SZ', '机器人', 'robot'),
    ('688108.SS', '赛诺医疗', 'robot'),
    ('002527.SZ', '新时达', 'robot'),
    ('300450.SZ', '先导智能', 'robot'),
    ('9996.HK', '达闼机器人', 'robot'),
    ('002747.SZ', '埃斯顿', 'robot'),
    ('688007.SS', '光峰科技', 'robot'),
    ('300607.SZ', '拓斯达', 'robot'),
    ('603486.SS', '科沃斯', 'robot'),
    ('300073.SZ', '当升科技', 'robot'),
    ('002097.SZ', '山河智能', 'robot'),

    # ══════════════════════════════════════════════════════════════
    # tech / 科技 (20)
    # ══════════════════════════════════════════════════════════════
    ('300059.SZ', '东方财富', 'tech'),
    ('002415.SZ', '海康威视', 'tech'),
    ('000725.SZ', '京东方A', 'tech'),
    ('002475.SZ', '立讯精密', 'tech'),
    ('600050.SS', '中国联通', 'tech'),
    ('002236.SZ', '大华股份', 'tech'),
    ('300496.SZ', '中科创达', 'tech'),
    ('1337.HK', '雷蛇', 'tech'),
    ('002241.SZ', '歌尔股份', 'tech'),
    ('300433.SZ', '蓝思科技', 'tech'),
    ('300136.SZ', '信维通信', 'tech'),
    ('002600.SZ', '领益智造', 'tech'),
    ('9999.HK', '网易', 'tech'),
    ('0700.HK', '腾讯控股', 'tech'),
    ('9988.HK', '阿里巴巴', 'tech'),
    ('3690.HK', '美团', 'tech'),
    ('9618.HK', '京东集团', 'tech'),
    ('6060.HK', '众安在线', 'tech'),
    ('0285.HK', '比亚迪电子', 'tech'),
    ('1810.HK', '小米集团', 'tech'),

    # ══════════════════════════════════════════════════════════════
    # ev / 新能源车 (16)
    # ══════════════════════════════════════════════════════════════
    ('002594.SZ', '比亚迪', 'ev'),
    ('000625.SZ', '长安汽车', 'ev'),
    ('601127.SS', '赛力斯', 'ev'),
    ('600104.SS', '上汽集团', 'ev'),
    ('601238.SS', '广汽集团', 'ev'),
    ('600733.SS', '北汽蓝谷', 'ev'),
    ('002074.SZ', '国轩高科', 'ev'),
    ('300014.SZ', '亿纬锂能', 'ev'),
    ('002405.SZ', '四维图新', 'ev'),
    ('300750.SZ', '宁德时代', 'ev'),
    ('002812.SZ', '恩捷股份', 'ev'),
    ('601689.SS', '拓普集团', 'ev'),
    ('002920.SZ', '德赛西威', 'ev'),
    ('603659.SS', '璞泰来', 'ev'),
    ('002709.SZ', '天赐材料', 'ev'),
    ('002850.SZ', '科达利', 'ev'),

    # ══════════════════════════════════════════════════════════════
    # consumer / 大消费 (16)
    # ══════════════════════════════════════════════════════════════
    ('600519.SS', '贵州茅台', 'consumer'),
    ('000858.SZ', '五粮液', 'consumer'),
    ('601888.SS', '中国中免', 'consumer'),
    ('002714.SZ', '牧原股份', 'consumer'),
    ('600809.SS', '山西汾酒', 'consumer'),
    ('603288.SS', '海天味业', 'consumer'),
    ('600887.SS', '伊利股份', 'consumer'),
    ('000568.SZ', '泸州老窖', 'consumer'),
    ('002304.SZ', '洋河股份', 'consumer'),
    ('600600.SS', '青岛啤酒', 'consumer'),
    ('000895.SZ', '双汇发展', 'consumer'),
    ('603369.SS', '今世缘', 'consumer'),
    ('002557.SZ', '洽洽食品', 'consumer'),
    ('300146.SZ', '汤臣倍健', 'consumer'),
    ('603517.SS', '绝味食品', 'consumer'),
    ('002271.SZ', '东方雨虹', 'consumer'),

    # ══════════════════════════════════════════════════════════════
    # energy / 能源 (9)
    # ══════════════════════════════════════════════════════════════
    ('601899.SS', '紫金矿业', 'energy'),
    ('600900.SS', '长江电力', 'energy'),
    ('601857.SS', '中国石油', 'energy'),
    ('601088.SS', '中国神华', 'energy'),
    ('600028.SS', '中国石化', 'energy'),
    ('601225.SS', '陕西煤业', 'energy'),
    ('600188.SS', '兖矿能源', 'energy'),
    ('600011.SS', '华能国际', 'energy'),
    ('600886.SS', '国投电力', 'energy'),

    # ══════════════════════════════════════════════════════════════
    # pharma / 医药 (15)
    # ══════════════════════════════════════════════════════════════
    ('600276.SS', '恒瑞医药', 'pharma'),
    ('300760.SZ', '迈瑞医疗', 'pharma'),
    ('000538.SZ', '云南白药', 'pharma'),
    ('600196.SS', '复星医药', 'pharma'),
    ('300122.SZ', '智飞生物', 'pharma'),
    ('300015.SZ', '爱尔眼科', 'pharma'),
    ('002007.SZ', '华兰生物', 'pharma'),
    ('300529.SZ', '健帆生物', 'pharma'),
    ('688185.SS', '康希诺', 'pharma'),
    ('688164.SS', '华大智造', 'pharma'),
    ('688046.SS', '药师帮', 'pharma'),
    ('300347.SZ', '泰格医药', 'pharma'),
    ('300759.SZ', '康龙化成', 'pharma'),
    ('002821.SZ', '凯莱英', 'pharma'),
    ('688180.SS', '君实生物', 'pharma'),

    # ══════════════════════════════════════════════════════════════
    # manufacturing / 制造 (18)
    # ══════════════════════════════════════════════════════════════
    ('000333.SZ', '美的集团', 'manufacturing'),
    ('600031.SS', '三一重工', 'manufacturing'),
    ('601633.SS', '长城汽车', 'manufacturing'),
    ('002352.SZ', '顺丰控股', 'manufacturing'),
    ('601668.SS', '中国建筑', 'manufacturing'),
    ('000651.SZ', '格力电器', 'manufacturing'),
    ('600585.SS', '海螺水泥', 'manufacturing'),
    ('600309.SS', '万华化学', 'manufacturing'),
    ('601766.SS', '中国中车', 'manufacturing'),
    ('002008.SZ', '大族激光', 'manufacturing'),
    ('601100.SS', '恒立液压', 'manufacturing'),
    ('002466.SZ', '天齐锂业', 'manufacturing'),
    ('002460.SZ', '赣锋锂业', 'manufacturing'),
    ('300124.SZ', '汇川技术', 'manufacturing'),
    ('000002.SZ', '万科A', 'manufacturing'),
    ('688009.SS', '中国通号', 'manufacturing'),
    ('300285.SZ', '国瓷材料', 'manufacturing'),
    ('300699.SZ', '光威复材', 'manufacturing'),

    # ══════════════════════════════════════════════════════════════
    # solar / 光伏新能源 (12)
    # ══════════════════════════════════════════════════════════════
    ('601012.SS', '隆基绿能', 'solar'),
    ('600438.SS', '通威股份', 'solar'),
    ('300274.SZ', '阳光电源', 'solar'),
    ('002129.SZ', 'TCL中环', 'solar'),
    ('002459.SZ', '晶澳科技', 'solar'),
    ('688599.SS', '天合光能', 'solar'),
    ('300763.SZ', '锦浪科技', 'solar'),
    ('688223.SS', '晶科能源', 'solar'),
    ('688390.SS', '固德威', 'solar'),
    ('300316.SZ', '晶盛机电', 'solar'),
    ('601615.SS', '明阳智能', 'solar'),
    ('300443.SZ', '金雷股份', 'solar'),

    # ══════════════════════════════════════════════════════════════
    # military / 军工 (11)
    # ══════════════════════════════════════════════════════════════
    ('600760.SS', '中航沈飞', 'military'),
    ('600893.SS', '航发动力', 'military'),
    ('002179.SZ', '中航光电', 'military'),
    ('600372.SS', '中航电子', 'military'),
    ('600150.SS', '中国船舶', 'military'),
    ('601989.SS', '中国重工', 'military'),
    ('000768.SZ', '中航西飞', 'military'),
    ('688122.SS', '西部超导', 'military'),
    ('688187.SS', '时代电气', 'military'),
    ('002414.SZ', '高德红外', 'military'),
    ('688333.SS', '铂力特', 'military'),

    # ══════════════════════════════════════════════════════════════
    # liquor / 白酒 (5)
    # ══════════════════════════════════════════════════════════════
    ('600702.SS', '舍得酒业', 'liquor'),
    ('000799.SZ', '酒鬼酒', 'liquor'),
    ('000596.SZ', '古井贡酒', 'liquor'),
    ('600779.SS', '水井坊', 'liquor'),
    ('002646.SZ', '青青稞酒', 'liquor'),

    # ══════════════════════════════════════════════════════════════
    # real_estate / 地产 (5)
    # ══════════════════════════════════════════════════════════════
    ('600048.SS', '保利发展', 'real_estate'),
    ('001979.SZ', '招商蛇口', 'real_estate'),
    ('600383.SS', '金地集团', 'real_estate'),
    ('601155.SS', '新城控股', 'real_estate'),
    ('001914.SZ', '招商积余', 'real_estate'),

    # ══════════════════════════════════════════════════════════════
    # telecom / 通信 (9)
    # ══════════════════════════════════════════════════════════════
    ('600941.SS', '中国移动', 'telecom'),
    ('601728.SS', '中国电信', 'telecom'),
    ('000063.SZ', '中兴通讯', 'telecom'),
    ('300628.SZ', '亿联网络', 'telecom'),
    ('002396.SZ', '星网锐捷', 'telecom'),
    ('300590.SZ', '移为通信', 'telecom'),
    ('002194.SZ', '武汉凡谷', 'telecom'),
    ('300638.SZ', '广和通', 'telecom'),
    ('300698.SZ', '万达信息', 'telecom'),

    # ══════════════════════════════════════════════════════════════
    # Additional high-growth / sector expansion (45+)
    # ══════════════════════════════════════════════════════════════
    # ── more AI / cloud ──
    ('688318.SS', '财富趋势', 'ai'),
    ('688065.SS', '凯赛生物', 'ai'),
    ('300203.SZ', '聚光科技', 'ai'),
    ('688019.SS', '安集科技', 'ai'),
    # ── more chip / semiconductor equipment ──
    ('688066.SS', '航天宏图', 'chip'),
    ('688299.SS', '长阳科技', 'chip'),
    ('300373.SZ', '扬杰科技', 'chip'),
    ('605111.SS', '新洁能', 'chip'),
    ('688261.SS', '东微半导', 'chip'),
    # ── more EV battery & smart driving ──
    ('300037.SZ', '新宙邦', 'ev'),
    ('300568.SZ', '星源材质', 'ev'),
    ('002850.SZ', '科达利', 'ev'),
    ('300035.SZ', '中科电气', 'ev'),
    ('300750.SZ', '宁德时代', 'ev'),
    # ── more software / SaaS ──
    ('688318.SS', '财富趋势', 'software'),
    ('300170.SZ', '汉得信息', 'software'),
    ('688035.SS', '德邦科技', 'software'),
    # ── more robot / automation ──
    ('300382.SZ', '斯莱克', 'robot'),
    ('002380.SZ', '科远智慧', 'robot'),
    ('688022.SS', '瀚川智能', 'robot'),
    # ── more tech / internet HK ──
    ('0241.HK', '阿里健康', 'tech'),
    ('2518.HK', '汽车之家', 'tech'),
    ('1024.HK', '快手', 'tech'),
    ('9626.HK', '哔哩哔哩', 'tech'),
    # ── more manufacturing ──
    ('002032.SZ', '苏泊尔', 'manufacturing'),
    ('002444.SZ', '巨星科技', 'manufacturing'),
    ('603596.SS', '伯特利', 'manufacturing'),
    # ── more consumer ──
    ('300413.SZ', '芒果超媒', 'consumer'),
    ('603345.SS', '安井食品', 'consumer'),
    # ── more pharma / CRO ──
    ('300363.SZ', '博腾股份', 'pharma'),
    ('002252.SZ', '上海莱士', 'pharma'),
    ('688131.SS', '皓元医药', 'pharma'),
    # ── more energy ──
    ('601985.SS', '中国核电', 'energy'),
    ('003816.SZ', '中国广核', 'energy'),
    # ── more solar / wind ──
    ('300316.SZ', '晶盛机电', 'solar'),
    ('300443.SZ', '金雷股份', 'solar'),
    # ── more military ──
    ('002414.SZ', '高德红外', 'military'),
    ('688333.SS', '铂力特', 'military'),
    # ── more optical ──
    ('300487.SZ', '蓝晓科技', 'optical'),
    ('688002.SS', '睿创微纳', 'optical'),
    # ── more storage ──
    ('300101.SZ', '振芯科技', 'storage'),
    ('002185.SZ', '华天科技', 'storage'),
    # ── final additions to reach 300+ ──
    ('688365.SS', '光云科技', 'software'),
    ('688016.SS', '心脉医疗', 'pharma'),
    ('300394.SZ', '天孚通信', 'telecom'),
    ('688200.SS', '华峰测控', 'chip'),
    ('688036.SS', '传音控股', 'tech'),
    ('603501.SS', '韦尔股份', 'tech'),
    ('688536.SS', '思瑞浦', 'ai'),
    ('300750.SZ', '宁德时代', 'manufacturing'),
    ('002192.SZ', '融捷股份', 'ev'),
    ('300750.SZ', '宁德时代', 'solar'),
    ('688275.SS', '万润新能', 'ev'),
    ('688006.SS', '杭可科技', 'robot'),
    ('688188.SS', '柏楚电子', 'manufacturing'),
    ('002409.SZ', '雅克科技', 'chip'),
]

# De-duplicate: some tickers appear in both TOP50 (old sectors) and CN_UNIVERSE (new sectors).
# CN_UNIVERSE is the single source of truth.
_seen_tickers: set[str] = set()
_deduped: list[tuple[str, str, str]] = []
for _t, _n, _s in CN_UNIVERSE:
    if _t not in _seen_tickers:
        _seen_tickers.add(_t)
        _deduped.append((_t, _n, _s))
CN_UNIVERSE = _deduped

SECTORS: dict[str, list[tuple[str, str, str]]] = {}
for _ticker, _name, _sector in CN_UNIVERSE:
    SECTORS.setdefault(_sector, []).append((_ticker, _name, _sector))

VALID_SECTORS = sorted(SECTORS.keys())


# ── Scoring Engine ───────────────────────────────────────────────────

def compute_score(
    close: np.ndarray,
    volume: np.ndarray | None = None,
) -> dict:
    """Compute technical score for a price series.

    Returns dict with keys:
        score, rsi_val, macd_hist, pct_b, change_1d, change_5d, volume_ratio,
        signal, price, reasons
    """
    close = np.asarray(close, dtype=np.float64)
    if len(close) < 30:
        return _empty_result(close)

    price = float(close[-1])
    score = 0
    reasons: list[str] = []

    # RSI
    rsi_arr = rsi(close, 14)
    rsi_val = float(rsi_arr[-1]) if not np.isnan(rsi_arr[-1]) else 50.0

    if rsi_val < 30:
        score += 4
        reasons.append(f"RSI oversold({rsi_val:.0f})")
    elif rsi_val < 40:
        score += 3
        reasons.append(f"RSI oversold({rsi_val:.0f})")
    elif rsi_val < 50:
        score += 1
    elif rsi_val > 70:
        score -= 2
        reasons.append(f"RSI overbought({rsi_val:.0f})")

    # MACD histogram
    _macd_line, _macd_signal, macd_hist_arr = macd(close)
    macd_hist_val = float(macd_hist_arr[-1]) if not np.isnan(macd_hist_arr[-1]) else 0.0

    if macd_hist_val > 0:
        score += 2
        reasons.append("MACD golden cross")

    # Bollinger %B
    bb = bollinger_bands(close)
    pct_b_arr = bb['pct_b']
    pct_b_val = float(pct_b_arr[-1]) * 100 if not np.isnan(pct_b_arr[-1]) else 50.0

    if pct_b_val < 20:
        score += 3
        reasons.append("near Bollinger lower")
    elif pct_b_val < 40:
        score += 1

    # 5-day price change
    if len(close) >= 6:
        change_5d = (close[-1] / close[-6] - 1) * 100
    else:
        change_5d = 0.0

    if 0 < change_5d <= 8:
        score += 2

    # 1-day price change
    if len(close) >= 2:
        change_1d = (close[-1] / close[-2] - 1) * 100
    else:
        change_1d = 0.0

    # Volume ratio
    volume_ratio = 0.0
    if volume is not None and len(volume) >= 21:
        vol = np.asarray(volume, dtype=np.float64)
        avg_vol = np.mean(vol[-21:-1])
        if avg_vol > 0:
            volume_ratio = float(vol[-1] / avg_vol)
            if 1.2 <= volume_ratio <= 3.0:
                score += 1
                reasons.append(f"volume up {volume_ratio:.1f}x")

    signal = classify_signal(score)

    return {
        "score": score,
        "rsi_val": rsi_val,
        "macd_hist": macd_hist_val,
        "pct_b": pct_b_val,
        "change_1d": change_1d,
        "change_5d": change_5d,
        "volume_ratio": volume_ratio,
        "signal": signal,
        "price": price,
        "reasons": reasons,
    }


def classify_signal(score: int) -> str:
    """Classify score into signal string."""
    if score >= 6:
        return "** BUY"
    elif score >= 4:
        return "WATCH"
    else:
        return "HOLD"


def _empty_result(close: np.ndarray) -> dict:
    price = float(close[-1]) if len(close) > 0 else 0.0
    return {
        "score": 0,
        "rsi_val": 50.0,
        "macd_hist": 0.0,
        "pct_b": 50.0,
        "change_1d": 0.0,
        "change_5d": 0.0,
        "volume_ratio": 0.0,
        "signal": "HOLD",
        "price": price,
        "reasons": [],
    }


# ── V2 Scoring Engine (multi-signal) ────────────────────────────────

def _signal_volume_breakout(
    close: np.ndarray,
    volume: np.ndarray | None,
) -> tuple[int, str | None]:
    """Volume Breakout: price up >2% AND volume > 2x 20-day average. (+3)"""
    if volume is None or len(close) < 2 or len(volume) < 21:
        return 0, None
    change = (close[-1] / close[-2] - 1) * 100
    vol = np.asarray(volume, dtype=np.float64)
    avg_vol = np.mean(vol[-21:-1])
    if avg_vol <= 0:
        return 0, None
    vol_ratio = vol[-1] / avg_vol
    if change > 2.0 and vol_ratio > 2.0:
        return 3, f"vol breakout(+{change:.1f}%, vol {vol_ratio:.1f}x)"
    return 0, None


def _signal_bottom_reversal(
    close: np.ndarray,
    rsi_val: float,
) -> tuple[int, str | None]:
    """Bottom Reversal: RSI < 25 AND price > prev close (bouncing). (+4)"""
    if len(close) < 2:
        return 0, None
    if rsi_val < 25.0 and close[-1] > close[-2]:
        return 4, f"bottom reversal(RSI={rsi_val:.0f}, bouncing)"
    return 0, None


def _signal_macd_divergence(
    close: np.ndarray,
    macd_hist_arr: np.ndarray,
) -> tuple[int, str | None]:
    """MACD Bullish Divergence: price made new 10-day low but MACD hist didn't. (+3)"""
    if len(close) < 20 or len(macd_hist_arr) < 20:
        return 0, None
    # Check if current price is at or near 10-day low
    recent_10 = close[-10:]
    if close[-1] > np.nanmin(recent_10) * 1.005:  # within 0.5% of 10-day low
        return 0, None
    # Find previous trough: look at days -20 to -10 for a local low
    prev_window = close[-20:-10]
    if len(prev_window) == 0:
        return 0, None
    prev_low_offset = int(np.argmin(prev_window))  # offset within [-20:-10]
    prev_low_idx = len(close) - 20 + prev_low_offset  # absolute index
    # Compare MACD histogram values: current vs previous trough
    curr_hist = macd_hist_arr[-1]
    prev_hist = macd_hist_arr[prev_low_idx] if prev_low_idx < len(macd_hist_arr) else np.nan
    if np.isnan(curr_hist) or np.isnan(prev_hist):
        return 0, None
    # Divergence: price makes new low, but MACD histogram is higher (less negative)
    if close[-1] <= close[prev_low_idx] and curr_hist > prev_hist:
        return 3, "MACD bullish divergence"
    return 0, None


def _signal_ma_alignment(
    close: np.ndarray,
) -> tuple[int, str | None]:
    """MA Alignment: Close > MA5 > MA10 > MA20 (uptrend confirmation). (+2)"""
    if len(close) < 20:
        return 0, None
    ma5 = np.mean(close[-5:])
    ma10 = np.mean(close[-10:])
    ma20 = np.mean(close[-20:])
    if close[-1] > ma5 > ma10 > ma20:
        return 2, "MA alignment(bullish)"
    return 0, None


def _signal_low_volume_pullback(
    close: np.ndarray,
    volume: np.ndarray | None,
) -> tuple[int, str | None]:
    """Low-Volume Pullback: in uptrend (MA20 up), 3-day pullback with declining volume. (+3)"""
    if volume is None or len(close) < 25 or len(volume) < 25:
        return 0, None
    vol = np.asarray(volume, dtype=np.float64)
    # Check uptrend: MA20 rising
    ma20_now = np.mean(close[-20:])
    ma20_5ago = np.mean(close[-25:-5])
    if ma20_now <= ma20_5ago:
        return 0, None
    # Check 3-day pullback (close declining)
    if not (close[-1] < close[-2] or close[-2] < close[-3] or close[-3] < close[-4]):
        # At least 2 of last 3 days should be down
        down_count = sum(1 for i in range(-3, 0) if close[i] < close[i - 1])
        if down_count < 2:
            return 0, None
    # Check declining volume over last 3 days
    if not (vol[-1] < vol[-2] and vol[-2] < vol[-3]):
        return 0, None
    # Price still above MA20
    if close[-1] < ma20_now:
        return 0, None
    return 3, "low-vol pullback(uptrend)"


def _signal_nday_breakout(
    close: np.ndarray,
    n: int = 20,
) -> tuple[int, str | None]:
    """N-Day Breakout: price at N-day high. (+2)"""
    if len(close) < n:
        return 0, None
    n_day_max = np.max(close[-n:])
    if close[-1] >= n_day_max:
        return 2, f"{n}d high breakout"
    return 0, None


def _signal_short_term_reversal(
    close: np.ndarray,
) -> tuple[int, str | None]:
    """Short-Term Reversal: 5-day return < -5% (mean reversion). (+2)"""
    if len(close) < 6:
        return 0, None
    ret_5d = (close[-1] / close[-6] - 1) * 100
    if ret_5d < -5.0:
        return 2, f"5d reversal({ret_5d:+.1f}%)"
    return 0, None


def _signal_momentum_confirmation(
    close: np.ndarray,
) -> tuple[int, str | None]:
    """Momentum Confirmation: 10-day return > 0 AND 20-day return > 0. (+1)"""
    if len(close) < 21:
        return 0, None
    ret_10d = (close[-1] / close[-11] - 1) * 100
    ret_20d = (close[-1] / close[-21] - 1) * 100
    if ret_10d > 0 and ret_20d > 0:
        return 1, "momentum confirmed"
    return 0, None


def compute_score_v2(
    close: np.ndarray,
    volume: np.ndarray | None = None,
) -> dict:
    """Compute enhanced technical score using multi-signal approach (v2).

    Includes all v1 signals plus:
    - Volume Breakout (+3)
    - Bottom Reversal (+4)
    - MACD Bullish Divergence (+3)
    - MA Alignment (+2)
    - Low-Volume Pullback (+3)
    - N-Day Breakout (+2)
    - Short-Term Reversal (+2)
    - Momentum Confirmation (+1)

    Returns dict with same keys as compute_score(), plus ``strategy`` key.
    """
    close = np.asarray(close, dtype=np.float64)
    if len(close) < 30:
        result = _empty_result(close)
        result["strategy"] = "v2"
        return result

    # ── Start with v1 baseline ───────────────────────────────────
    base = compute_score(close, volume)
    score = base["score"]
    reasons = list(base["reasons"])
    rsi_val = base["rsi_val"]

    # ── V2 signals ───────────────────────────────────────────────
    # MACD histogram array (need it for divergence)
    _macd_line, _macd_signal, macd_hist_arr = macd(close)

    signal_funcs = [
        lambda: _signal_volume_breakout(close, volume),
        lambda: _signal_bottom_reversal(close, rsi_val),
        lambda: _signal_macd_divergence(close, macd_hist_arr),
        lambda: _signal_ma_alignment(close),
        lambda: _signal_low_volume_pullback(close, volume),
        lambda: _signal_nday_breakout(close, 20),
        lambda: _signal_short_term_reversal(close),
        lambda: _signal_momentum_confirmation(close),
    ]

    for fn in signal_funcs:
        pts, reason = fn()
        score += pts
        if reason:
            reasons.append(reason)

    signal = classify_signal_v2(score)

    return {
        "score": score,
        "rsi_val": base["rsi_val"],
        "macd_hist": base["macd_hist"],
        "pct_b": base["pct_b"],
        "change_1d": base["change_1d"],
        "change_5d": base["change_5d"],
        "volume_ratio": base["volume_ratio"],
        "signal": signal,
        "price": base["price"],
        "reasons": reasons,
        "strategy": "v2",
    }


def classify_signal_v2(score: int) -> str:
    """Classify v2 score into signal string (higher thresholds)."""
    if score >= 10:
        return "*** STRONG BUY"
    elif score >= 7:
        return "** BUY"
    elif score >= 4:
        return "WATCH"
    else:
        return "HOLD"


# ── V3 Signal Functions (OHLCV-based) ───────────────────────────────

def _signal_three_soldiers(
    open_: np.ndarray,
    high: np.ndarray,
    low: np.ndarray,
    close: np.ndarray,
) -> tuple[int, str | None]:
    """Three Soldiers: 3 consecutive up days, each closing near high. (+3)"""
    if len(close) < 4:
        return 0, None
    for i in range(-3, 0):
        # Each day must be up: close > open
        if close[i] <= open_[i]:
            return 0, None
        # Close near high: upper wick < 30% of body
        body = close[i] - open_[i]
        if body <= 0:
            return 0, None
        upper_wick = high[i] - close[i]
        if upper_wick > 0.3 * body:
            return 0, None
    return 3, "three soldiers(3 bullish candles)"


def _signal_long_lower_shadow(
    open_: np.ndarray,
    high: np.ndarray,
    low: np.ndarray,
    close: np.ndarray,
    rsi_val: float,
) -> tuple[int, str | None]:
    """Long Lower Shadow: lower shadow > 2x body at oversold (RSI<35). (+3)"""
    if len(close) < 1:
        return 0, None
    body = abs(close[-1] - open_[-1])
    if body < 1e-10:
        body = 1e-10
    lower_shadow = min(close[-1], open_[-1]) - low[-1]
    if lower_shadow <= 0:
        return 0, None
    if lower_shadow > 2.0 * body and rsi_val < 35.0:
        return 3, f"long lower shadow(RSI={rsi_val:.0f})"
    return 0, None


def _signal_doji_at_bottom(
    open_: np.ndarray,
    high: np.ndarray,
    low: np.ndarray,
    close: np.ndarray,
    volume: np.ndarray | None,
    rsi_val: float,
) -> tuple[int, str | None]:
    """Doji at Bottom: open ≈ close (0.5%), RSI<40, low volume. (+2)"""
    if len(close) < 21 or volume is None or len(volume) < 21:
        return 0, None
    price = close[-1]
    if price <= 0:
        return 0, None
    body_pct = abs(close[-1] - open_[-1]) / price * 100
    if body_pct > 0.5:
        return 0, None
    if rsi_val >= 40.0:
        return 0, None
    vol = np.asarray(volume, dtype=np.float64)
    avg_vol = np.mean(vol[-21:-1])
    if avg_vol <= 0:
        return 0, None
    vol_ratio = vol[-1] / avg_vol
    if vol_ratio < 0.7:  # low volume = below 70% of average
        return 2, f"doji at bottom(RSI={rsi_val:.0f}, vol={vol_ratio:.1f}x)"
    return 0, None


def _signal_volume_breakout_high(
    open_: np.ndarray,
    high: np.ndarray,
    low: np.ndarray,
    close: np.ndarray,
    volume: np.ndarray | None,
) -> tuple[int, str | None]:
    """Volume Breakout High: close > 20d high AND vol > 2.5x AND close in top 20% of range. (+4)"""
    if volume is None or len(close) < 21 or len(volume) < 21:
        return 0, None
    # Close must be above 20-day high (of prior 20 days, excluding today)
    prev_high = np.max(close[-21:-1])
    if close[-1] <= prev_high:
        return 0, None
    vol = np.asarray(volume, dtype=np.float64)
    avg_vol = np.mean(vol[-21:-1])
    if avg_vol <= 0:
        return 0, None
    vol_ratio = vol[-1] / avg_vol
    if vol_ratio <= 2.5:
        return 0, None
    # Close in top 20% of today's range
    day_range = high[-1] - low[-1]
    if day_range <= 0:
        return 0, None
    position_in_range = (close[-1] - low[-1]) / day_range
    if position_in_range < 0.8:
        return 0, None
    return 4, f"vol breakout new high(vol={vol_ratio:.1f}x)"


def _signal_volume_climax_reversal(
    close: np.ndarray,
    volume: np.ndarray | None,
) -> tuple[int, str | None]:
    """Volume Climax Reversal: huge vol (>3x) on down day, then up day. (+3)"""
    if volume is None or len(close) < 3 or len(volume) < 21:
        return 0, None
    vol = np.asarray(volume, dtype=np.float64)
    avg_vol = np.mean(vol[-21:-2])  # average excluding last 2 days
    if avg_vol <= 0:
        return 0, None
    # Day -2: down day with >3x volume
    if close[-2] >= close[-3]:  # not a down day
        return 0, None
    vol_ratio_prev = vol[-2] / avg_vol
    if vol_ratio_prev <= 3.0:
        return 0, None
    # Day -1 (today): up day
    if close[-1] <= close[-2]:
        return 0, None
    return 3, f"vol climax reversal(vol={vol_ratio_prev:.1f}x)"


def _signal_accumulation(
    close: np.ndarray,
    volume: np.ndarray | None,
) -> tuple[int, str | None]:
    """Accumulation: price flat (3%), 5d avg volume increasing >50%. (+2)"""
    if volume is None or len(close) < 11 or len(volume) < 11:
        return 0, None
    vol = np.asarray(volume, dtype=np.float64)
    # Price flat over last 5 days
    price_range = (np.max(close[-5:]) - np.min(close[-5:])) / close[-5] * 100 if close[-5] > 0 else 999
    if price_range > 3.0:
        return 0, None
    # 5-day avg volume vs prior 5-day avg volume
    avg_vol_recent = np.mean(vol[-5:])
    avg_vol_prev = np.mean(vol[-10:-5])
    if avg_vol_prev <= 0:
        return 0, None
    vol_increase = (avg_vol_recent / avg_vol_prev - 1) * 100
    if vol_increase > 50.0:
        return 2, f"accumulation(vol+{vol_increase:.0f}%)"
    return 0, None


def _signal_macd_hist_acceleration(
    close: np.ndarray,
) -> tuple[int, str | None]:
    """MACD Histogram Acceleration: hist positive AND increasing 2+ days. (+2)"""
    if len(close) < 30:
        return 0, None
    _, _, hist = macd(close)
    if len(hist) < 3:
        return 0, None
    # Last 3 histogram values
    h1, h2, h3 = float(hist[-3]), float(hist[-2]), float(hist[-1])
    if np.isnan(h1) or np.isnan(h2) or np.isnan(h3):
        return 0, None
    # All positive and increasing
    if h3 > 0 and h2 > 0 and h3 > h2 and h2 > h1:
        return 2, "MACD hist accelerating"
    return 0, None


def _signal_rsi_bullish_divergence(
    close: np.ndarray,
    rsi_arr: np.ndarray,
) -> tuple[int, str | None]:
    """RSI Bullish Divergence: price new 10d low but RSI didn't. (+3)"""
    if len(close) < 20 or len(rsi_arr) < 20:
        return 0, None
    # Current price must be at or near 10-day low
    recent_low = np.nanmin(close[-10:])
    if close[-1] > recent_low * 1.005:
        return 0, None
    # Find previous trough in days -20 to -10
    prev_window = close[-20:-10]
    if len(prev_window) == 0:
        return 0, None
    prev_low_offset = int(np.argmin(prev_window))
    prev_low_idx = len(close) - 20 + prev_low_offset
    # Price made a lower low
    if close[-1] > close[prev_low_idx]:
        return 0, None
    # RSI at current point vs RSI at previous trough
    rsi_now = rsi_arr[-1]
    rsi_prev = rsi_arr[prev_low_idx] if prev_low_idx < len(rsi_arr) else np.nan
    if np.isnan(rsi_now) or np.isnan(rsi_prev):
        return 0, None
    # Divergence: price lower low, RSI higher low
    if rsi_now > rsi_prev:
        return 3, "RSI bullish divergence"
    return 0, None


def _signal_squeeze_release(
    close: np.ndarray,
) -> tuple[int, str | None]:
    """Squeeze Release: BB bandwidth expanding after tight squeeze. (+3)"""
    if len(close) < 30:
        return 0, None
    bb = bollinger_bands(close)
    bw = bb['bandwidth']
    # Need at least 6 days of bandwidth data
    if len(bw) < 6:
        return 0, None
    # Check for squeeze: bandwidth < 5% for 5+ consecutive days ending 1-3 days ago
    # Then check if current bandwidth is expanding
    squeeze_found = False
    for end_offset in range(1, 4):  # check squeeze ending 1, 2, or 3 days ago
        if len(bw) < end_offset + 5:
            continue
        window = bw[-(end_offset + 5): -end_offset]
        # Filter NaN
        valid = window[~np.isnan(window)]
        if len(valid) >= 5 and np.all(valid < 0.05):
            squeeze_found = True
            break
    if not squeeze_found:
        return 0, None
    # Current bandwidth must be expanding (greater than recent squeeze levels)
    curr_bw = float(bw[-1])
    if np.isnan(curr_bw):
        return 0, None
    if curr_bw >= 0.05:
        return 3, f"squeeze release(bw={curr_bw:.3f})"
    return 0, None


def _signal_adx_trend_strength(
    high: np.ndarray,
    low: np.ndarray,
    close: np.ndarray,
) -> tuple[int, str | None]:
    """ADX Trend Strength: ADX > 25 AND +DI > -DI. (+2)"""
    if len(close) < 30:
        return 0, None
    adx_val, plus_di, minus_di = adx_full(high, low, close)
    a = float(adx_val[-1])
    p = float(plus_di[-1])
    m = float(minus_di[-1])
    if np.isnan(a) or np.isnan(p) or np.isnan(m):
        return 0, None
    if a > 25.0 and p > m:
        return 2, f"ADX strong uptrend({a:.0f})"
    return 0, None


def _signal_price_above_vwap(
    close: np.ndarray,
    volume: np.ndarray | None,
) -> tuple[int, str | None]:
    """Price Above VWAP: using volume-weighted average price. (+1)"""
    if volume is None or len(close) < 20 or len(volume) < 20:
        return 0, None
    vol = np.asarray(volume, dtype=np.float64)
    # 20-day VWAP
    total_vol = np.sum(vol[-20:])
    if total_vol <= 0:
        return 0, None
    vwap = np.sum(close[-20:] * vol[-20:]) / total_vol
    if close[-1] > vwap:
        return 1, "above VWAP"
    return 0, None


# ── V3 Scoring Engine (ultimate A-share short-term engine) ──────────

def compute_score_v3(
    close: np.ndarray,
    volume: np.ndarray | None = None,
    open_: np.ndarray | None = None,
    high: np.ndarray | None = None,
    low: np.ndarray | None = None,
) -> dict:
    """Compute enhanced technical score using V3 (OHLCV signals).

    Includes all V2 signals plus 11 new OHLCV-based signals:
    - Three Soldiers (+3)
    - Long Lower Shadow (+3)
    - Doji at Bottom (+2)
    - Volume Breakout High (+4)
    - Volume Climax Reversal (+3)
    - Accumulation Pattern (+2)
    - MACD Histogram Acceleration (+2)
    - RSI Bullish Divergence (+3)
    - Squeeze Release (+3)
    - ADX Trend Strength (+2)
    - Price Above VWAP (+1)

    Returns dict with same keys as compute_score_v2(), strategy='v3'.
    """
    close = np.asarray(close, dtype=np.float64)
    if len(close) < 30:
        result = _empty_result(close)
        result["strategy"] = "v3"
        return result

    # ── V2 baseline ──────────────────────────────────────────────
    base = compute_score_v2(close, volume)
    score = base["score"]
    reasons = list(base["reasons"])
    rsi_val = base["rsi_val"]

    # ── Synthesise OHLCV if not provided ─────────────────────────
    # When only close+volume are available, create approximate OHLCV
    if open_ is None:
        open_ = np.copy(close)
        # Approximate open as previous close
        open_[1:] = close[:-1]
    else:
        open_ = np.asarray(open_, dtype=np.float64)

    if high is None:
        high = np.copy(close)
    else:
        high = np.asarray(high, dtype=np.float64)

    if low is None:
        low = np.copy(close)
    else:
        low = np.asarray(low, dtype=np.float64)

    # ── RSI array for divergence ─────────────────────────────────
    rsi_arr = rsi(close, 14)

    # ── V3 signals ───────────────────────────────────────────────
    v3_signals = [
        lambda: _signal_three_soldiers(open_, high, low, close),
        lambda: _signal_long_lower_shadow(open_, high, low, close, rsi_val),
        lambda: _signal_doji_at_bottom(open_, high, low, close, volume, rsi_val),
        lambda: _signal_volume_breakout_high(open_, high, low, close, volume),
        lambda: _signal_volume_climax_reversal(close, volume),
        lambda: _signal_accumulation(close, volume),
        lambda: _signal_macd_hist_acceleration(close),
        lambda: _signal_rsi_bullish_divergence(close, rsi_arr),
        lambda: _signal_squeeze_release(close),
        lambda: _signal_adx_trend_strength(high, low, close),
        lambda: _signal_price_above_vwap(close, volume),
    ]

    for fn in v3_signals:
        pts, reason = fn()
        score += pts
        if reason:
            reasons.append(reason)

    signal = classify_signal_v3(score)

    return {
        "score": score,
        "rsi_val": base["rsi_val"],
        "macd_hist": base["macd_hist"],
        "pct_b": base["pct_b"],
        "change_1d": base["change_1d"],
        "change_5d": base["change_5d"],
        "volume_ratio": base["volume_ratio"],
        "signal": signal,
        "price": base["price"],
        "reasons": reasons,
        "strategy": "v3",
    }


def classify_signal_v3(score: int) -> str:
    """Classify v3 score into signal string (higher thresholds for v3)."""
    if score >= 14:
        return "*** STRONG BUY"
    elif score >= 10:
        return "** BUY"
    elif score >= 6:
        return "WATCH"
    else:
        return "HOLD"


# ── Stock Selection ──────────────────────────────────────────────────

def get_stock_universe(
    top: int = 30,
    sector: str | None = None,
) -> list[tuple[str, str, str]]:
    """Return list of (ticker, name, sector) based on filters."""
    if sector:
        sector_lower = sector.lower()
        if sector_lower not in SECTORS:
            raise ValueError(
                f"Unknown sector '{sector}'. Valid: {', '.join(VALID_SECTORS)}"
            )
        return SECTORS[sector_lower]
    return CN_UNIVERSE[:top]


# ── Scanner ──────────────────────────────────────────────────────────

def scan_cn_stocks(
    top: int = 30,
    sector: str | None = None,
    min_score: int = 0,
    sort_by: str = "score",
    strategy: str = "v3",
) -> list[dict]:
    """Scan A-share stocks and return scored results.

    Parameters
    ----------
    strategy : str
        ``"v1"`` for legacy, ``"v2"`` for multi-signal, ``"v3"`` for OHLCV (default).

    Returns list of dicts with keys: ticker, name, sector, code, + score fields.
    """
    from src.data.cache import DataCache
    import logging
    import warnings

    use_v3 = strategy == "v3"
    use_ml = strategy == "ml"
    if strategy == "v2":
        score_fn = compute_score_v2
    elif strategy == "v3":
        score_fn = None  # handled below with extra args
    elif strategy == "ml":
        score_fn = None  # handled below with ML scorer
    else:
        score_fn = compute_score

    universe = get_stock_universe(top=top, sector=sector)
    cache = DataCache()
    results: list[dict] = []

    for ticker, name, sect in universe:
        # Fetch data via yfinance
        cache_key = f"cn_{ticker}_3mo"
        df = cache.get(cache_key, max_age_hours=12)

        if df is None:
            try:
                import yfinance as yf
                logging.getLogger("yfinance").setLevel(logging.CRITICAL)
                with warnings.catch_warnings():
                    warnings.simplefilter("ignore")
                    stock = yf.Ticker(ticker)
                    df = stock.history(period="3mo")
                if df is not None and not df.empty:
                    cache.set(cache_key, df)
            except Exception as e:
                print(f"  ERROR fetching {ticker}: {e}")
                continue

        if df is None or len(df) < 30:
            continue

        close = np.array(df["Close"].tolist(), dtype=np.float64)
        volume = np.array(df["Volume"].tolist(), dtype=np.float64) if "Volume" in df.columns else None

        if use_v3 or use_ml:
            open_ = np.array(df["Open"].tolist(), dtype=np.float64) if "Open" in df.columns else None
            high = np.array(df["High"].tolist(), dtype=np.float64) if "High" in df.columns else None
            low = np.array(df["Low"].tolist(), dtype=np.float64) if "Low" in df.columns else None
            if use_ml:
                from src.cn_ml_scorer import compute_score_ml
                result = compute_score_ml(close, volume, open_, high, low)
            else:
                result = compute_score_v3(close, volume, open_, high, low)
        else:
            result = score_fn(close, volume)

        # Extract code from ticker (e.g. "600519" from "600519.SS")
        code = ticker.split(".")[0]
        result.update({
            "ticker": ticker,
            "name": name,
            "sector": sect,
            "code": code,
        })
        results.append(result)

    # Filter by min_score
    if min_score > 0:
        results = [r for r in results if r["score"] >= min_score]

    # Sort
    sort_key = sort_by.lower()
    if sort_key == "rsi":
        results.sort(key=lambda r: r["rsi_val"])
    elif sort_key == "price":
        results.sort(key=lambda r: r["price"], reverse=True)
    elif sort_key == "change":
        results.sort(key=lambda r: r["change_1d"], reverse=True)
    else:  # default: score descending
        results.sort(key=lambda r: r["score"], reverse=True)

    return results


# ── Output Formatting ────────────────────────────────────────────────

def format_scan_output(results: list[dict], version: str = "5.1.0") -> str:
    """Format scan results as a table string (ASCII-safe)."""
    lines: list[str] = []
    lines.append("")
    lines.append(f"  A-Share Scanner -- FinClaw v{version}")
    lines.append("  " + "=" * 90)
    # Header
    header = (
        f"  {'Rank':<5} {'Name':<14} {'Code':<10} {'Price':>8} "
        f"{'RSI':>6} {'MACD':>7} {'%B':>6} {'1D%':>6} {'5D%':>6} "
        f"{'VR':>5} {'Score':>6} {'Signal'}"
    )
    lines.append(header)
    lines.append("  " + "-" * 90)

    for i, r in enumerate(results, 1):
        name_display = r["name"]
        # Truncate name to 12 chars for alignment
        if len(name_display) > 12:
            name_display = name_display[:12]

        line = (
            f"  {i:<5} {name_display:<14} {r['code']:<10} {r['price']:>8.2f} "
            f"{r['rsi_val']:>6.1f} {r['macd_hist']:>+7.2f} {r['pct_b']:>5.1f} "
            f"{r['change_1d']:>+5.1f} {r['change_5d']:>+5.1f} "
            f"{r['volume_ratio']:>5.1f} {r['score']:>5} {r['signal']}"
        )
        lines.append(line)

    # Recommendations
    recommended = [r for r in results if r["score"] >= 5]
    if recommended:
        lines.append("")
        lines.append("  Recommended (Score >= 5):")
        for r in recommended:
            reason_str = ", ".join(r["reasons"]) if r["reasons"] else "composite"
            lines.append(
                f"    {r['name']} ({r['code']}) Score={r['score']} -- {reason_str}"
            )

    lines.append("")
    return "\n".join(lines)


# ── Backtest Engine ──────────────────────────────────────────────────

def _compute_score_at(
    close: np.ndarray,
    volume: np.ndarray | None,
    idx: int,
    strategy: str = "v1",
    open_: np.ndarray | None = None,
    high: np.ndarray | None = None,
    low: np.ndarray | None = None,
    ml_scorer: Optional[object] = None,
) -> dict:
    """Compute the scoring result using data up to (and including) *idx*.

    This slices ``close[:idx+1]`` and ``volume[:idx+1]`` so the scoring
    algorithm sees only data available on that trading day.

    Parameters
    ----------
    strategy : str
        ``"v1"`` for legacy, ``"v2"`` for multi-signal, ``"v3"`` for OHLCV,
        ``"ml"`` for machine learning blended.
    ml_scorer : MLStockScorer, optional
        Pre-trained scorer for ML strategy.
    """
    sliced_close = close[: idx + 1]
    sliced_volume = volume[: idx + 1] if volume is not None else None
    if strategy == "ml":
        from src.cn_ml_scorer import compute_score_ml
        sliced_open = open_[: idx + 1] if open_ is not None else None
        sliced_high = high[: idx + 1] if high is not None else None
        sliced_low = low[: idx + 1] if low is not None else None
        return compute_score_ml(sliced_close, sliced_volume, sliced_open, sliced_high, sliced_low, scorer=ml_scorer)
    if strategy == "v3":
        sliced_open = open_[: idx + 1] if open_ is not None else None
        sliced_high = high[: idx + 1] if high is not None else None
        sliced_low = low[: idx + 1] if low is not None else None
        return compute_score_v3(sliced_close, sliced_volume, sliced_open, sliced_high, sliced_low)
    score_fn = compute_score_v2 if strategy == "v2" else compute_score
    return score_fn(sliced_close, sliced_volume)


def backtest_cn_strategy(
    *,
    hold_days: int = 5,
    min_score: int = 6,
    period: str = "6mo",
    lookback_days: int = 30,
    sector: str | None = None,
    top: int | None = None,
    data_override: dict[str, dict] | None = None,
    strategy: str = "v1",
    stop_loss: float | None = None,
    take_profit: float | None = None,
    trailing_stop: bool = False,
    ml_version: str = "v2",
) -> dict:
    """Walk-forward backtest of the A-share scoring strategy.

    Parameters
    ----------
    hold_days : int
        How many trading days to hold each selected batch (1/3/5/10/20).
    min_score : int
        Minimum score for a stock to be selected on a given day.
    period : str
        yfinance period string for fetching historical data (e.g. ``"6mo"``).
    lookback_days : int
        How many recent trading days to evaluate (max depends on period).
    sector : str | None
        Limit backtest to a specific sector, or ``None`` for all.
    top : int | None
        Limit to top-N stocks if no sector is specified.
    data_override : dict | None
        Pre-loaded data keyed by ticker → ``{"close": np.ndarray, "volume": np.ndarray}``.
        For v3, also supports ``"open"``, ``"high"``, ``"low"`` keys.
        When provided, yfinance is **not** called, making unit-tests fast and deterministic.
    strategy : str
        ``"v1"`` for legacy, ``"v2"`` for multi-signal, ``"v3"`` for OHLCV.
    stop_loss : float | None
        Stop-loss percentage (positive number, e.g. 3 means sell if price drops 3%
        from entry). ``None`` disables stop-loss.
    take_profit : float | None
        Take-profit percentage (positive number, e.g. 8 means sell if price rises
        8% from entry). ``None`` disables take-profit.
    trailing_stop : bool
        If ``True``, once unrealised profit hits 5% the stop is raised to
        breakeven (0% from entry).

    Returns
    -------
    dict
        Keys: ``batches`` (list[dict]), ``summary`` (dict).
    """
    # For longer periods, allow more lookback days
    _period_max_lookback = {
        "1mo": 20, "3mo": 60, "6mo": 90,
        "1y": 200, "2y": 400,
    }
    max_lookback = _period_max_lookback.get(period, 90)
    lookback_days = min(max(lookback_days, 1), max_lookback)
    if hold_days not in (1, 3, 5, 10, 20):
        hold_days = 5

    universe = get_stock_universe(
        top=top if top is not None else len(CN_UNIVERSE),
        sector=sector,
    )

    use_v3 = strategy in ("v3", "ml")  # ML also needs OHLCV data

    # ── Pre-train ML scorer if needed ────────────────────────────
    ml_scorer = None  # will be populated per-stock during walk-forward

    # ── Fetch data ───────────────────────────────────────────────
    stock_data: dict[str, dict] = {}  # ticker → {close, volume, name, sector, [open, high, low]}

    if data_override is not None:
        for ticker, name, sect in universe:
            if ticker in data_override:
                d = data_override[ticker]
                entry: dict = {
                    "close": np.asarray(d["close"], dtype=np.float64),
                    "volume": np.asarray(d["volume"], dtype=np.float64) if d.get("volume") is not None else None,
                    "name": name,
                    "sector": sect,
                }
                if use_v3:
                    entry["open"] = np.asarray(d["open"], dtype=np.float64) if d.get("open") is not None else None
                    entry["high"] = np.asarray(d["high"], dtype=np.float64) if d.get("high") is not None else None
                    entry["low"] = np.asarray(d["low"], dtype=np.float64) if d.get("low") is not None else None
                stock_data[ticker] = entry
    else:
        import logging
        import warnings

        for ticker, name, sect in universe:
            try:
                import yfinance as yf
                logging.getLogger("yfinance").setLevel(logging.CRITICAL)
                with warnings.catch_warnings():
                    warnings.simplefilter("ignore")
                    stock = yf.Ticker(ticker)
                    df = stock.history(period=period)
                # Minimum data requirement scales with requested period
                _min_bars = 60  # default for 6mo
                if period in ("1y",):
                    _min_bars = 60  # still need 60 bars minimum
                elif period in ("2y",):
                    _min_bars = 60
                if df is None or df.empty or len(df) < _min_bars:
                    continue
                entry = {
                    "close": np.array(df["Close"].tolist(), dtype=np.float64),
                    "volume": np.array(df["Volume"].tolist(), dtype=np.float64) if "Volume" in df.columns else None,
                    "name": name,
                    "sector": sect,
                }
                if use_v3:
                    entry["open"] = np.array(df["Open"].tolist(), dtype=np.float64) if "Open" in df.columns else None
                    entry["high"] = np.array(df["High"].tolist(), dtype=np.float64) if "High" in df.columns else None
                    entry["low"] = np.array(df["Low"].tolist(), dtype=np.float64) if "Low" in df.columns else None
                stock_data[ticker] = entry
            except Exception:
                continue

    if not stock_data:
        return {"batches": [], "summary": _empty_summary()}

    # ── Train ML scorers (one per stock) if strategy == "ml" ─────
    ml_scorers: dict[str, object] = {}
    if strategy == "ml":
        from src.cn_ml_scorer import MLStockScorer, compute_features_series
        for ticker, info in stock_data.items():
            close_arr = info["close"]
            if len(close_arr) < 150:
                continue  # need enough data for walk-forward
            features = compute_features_series(
                close_arr, info.get("volume"),
                info.get("open"), info.get("high"), info.get("low"),
                version=ml_version,
            )
            if features is None:
                continue
            scorer = MLStockScorer(
                train_bars=250 if ml_version == "v2" else 120,
                predict_bars=5 if ml_version == "v2" else 20,
                forward_days=hold_days,
                version=ml_version,
                expanding_window=(ml_version == "v2"),
            )
            scorer.train_and_predict(
                features, close_arr,
                high=info.get("high") if ml_version == "v2" else None,
                low=info.get("low") if ml_version == "v2" else None,
            )
            if scorer._model is not None:
                ml_scorers[ticker] = scorer

    # ── Determine evaluation window ─────────────────────────────
    min_len = min(len(d["close"]) for d in stock_data.values())
    warmup = 30
    start_idx = max(warmup, min_len - lookback_days - hold_days)
    end_idx = min_len - hold_days

    if start_idx >= end_idx:
        return {"batches": [], "summary": _empty_summary()}

    # ── Walk-forward ─────────────────────────────────────────────
    # Pre-compute stop/take thresholds once
    use_risk_mgmt = (stop_loss is not None) or (take_profit is not None)
    sl_pct = -(abs(stop_loss) / 100.0) if stop_loss is not None else None  # e.g. -0.03
    tp_pct = abs(take_profit) / 100.0 if take_profit is not None else None  # e.g. 0.08
    trailing_threshold = 0.05  # 5% profit triggers trailing stop to breakeven

    batches: list[dict] = []
    day = start_idx

    while day < end_idx:
        selected: list[dict] = []
        for ticker, info in stock_data.items():
            close = info["close"]
            volume = info["volume"]
            if day >= len(close) - hold_days:
                continue
            result = _compute_score_at(
                close, volume, day, strategy=strategy,
                open_=info.get("open"),
                high=info.get("high"),
                low=info.get("low"),
                ml_scorer=ml_scorers.get(ticker),
            )
            if result["score"] >= min_score:
                entry_price = close[day]
                if entry_price <= 0:
                    continue

                # ── Determine exit with risk management ──────
                exit_day_offset = hold_days
                exit_reason = "hold-expiry"
                actual_exit_price = close[min(day + hold_days, len(close) - 1)]

                if use_risk_mgmt:
                    # current stop level (can be adjusted by trailing)
                    current_sl = sl_pct
                    # T+1 for A-shares, T+0 for HK stocks
                    start_day = 1 if ticker.endswith('.HK') else 2
                    for d in range(start_day, hold_days + 1):
                        idx = day + d
                        if idx >= len(close):
                            break
                        day_return = (close[idx] / entry_price) - 1.0

                        # Trailing stop: once we hit 5% profit, move stop to breakeven
                        if trailing_stop and day_return >= trailing_threshold:
                            if current_sl is None or current_sl < 0:
                                current_sl = 0.0  # breakeven

                        # Check stop-loss
                        if current_sl is not None and day_return <= current_sl:
                            actual_exit_price = close[idx]
                            exit_day_offset = d
                            exit_reason = "stop-loss"
                            break

                        # Check take-profit
                        if tp_pct is not None and day_return >= tp_pct:
                            actual_exit_price = close[idx]
                            exit_day_offset = d
                            exit_reason = "take-profit"
                            break

                fwd_return = (actual_exit_price / entry_price - 1) * 100

                stock_result: dict = {
                    "ticker": ticker,
                    "name": info["name"],
                    "sector": info["sector"],
                    "score": result["score"],
                    "entry_price": float(entry_price),
                    "exit_price": float(actual_exit_price),
                    "return_pct": float(fwd_return),
                }
                if use_risk_mgmt:
                    stock_result["exit_reason"] = exit_reason
                    stock_result["exit_day"] = exit_day_offset

                selected.append(stock_result)

        if selected:
            avg_ret = sum(s["return_pct"] for s in selected) / len(selected)
            best = max(selected, key=lambda s: s["return_pct"])
            worst = min(selected, key=lambda s: s["return_pct"])
            batches.append({
                "day_index": day,
                "num_selected": len(selected),
                "avg_return": avg_ret,
                "best_stock": best["name"],
                "best_ticker": best["ticker"],
                "best_return": best["return_pct"],
                "worst_stock": worst["name"],
                "worst_ticker": worst["ticker"],
                "worst_return": worst["return_pct"],
                "stocks": selected,
            })

        day += hold_days

    # ── Summary ──────────────────────────────────────────────────
    summary = _compute_summary(batches, hold_days, min_score)
    return {"batches": batches, "summary": summary}


def _compute_summary(batches: list[dict], hold_days: int, min_score: int) -> dict:
    """Aggregate backtest batches into a summary."""
    if not batches:
        return _empty_summary()

    returns = [b["avg_return"] for b in batches]
    total_batches = len(batches)
    avg_return = sum(returns) / total_batches
    win_count = sum(1 for r in returns if r > 0)
    win_rate = win_count / total_batches * 100
    best_batch = max(returns)
    worst_batch = min(returns)

    # Rough annualization:  (1 + avg_per_period)^(periods_per_year) - 1
    periods_per_year = 252 / max(hold_days, 1)
    avg_per_period = avg_return / 100.0
    ann_return = ((1 + avg_per_period) ** periods_per_year - 1) * 100

    return {
        "total_batches": total_batches,
        "avg_return": avg_return,
        "win_rate": win_rate,
        "best_batch": best_batch,
        "worst_batch": worst_batch,
        "annualized": ann_return,
        "hold_days": hold_days,
        "min_score": min_score,
    }


def _empty_summary() -> dict:
    return {
        "total_batches": 0,
        "avg_return": 0.0,
        "win_rate": 0.0,
        "best_batch": 0.0,
        "worst_batch": 0.0,
        "annualized": 0.0,
        "hold_days": 0,
        "min_score": 0,
    }


def format_backtest_output(result: dict, version: str = "5.1.0", strategy: str = "v1") -> str:
    """Format backtest result dict into a human-readable table."""
    lines: list[str] = []
    summary = result["summary"]
    batches = result["batches"]

    lines.append("")
    lines.append(f"  A-Share Selection Strategy Backtest -- FinClaw v{version} (strategy={strategy})")
    lines.append(
        f"  Hold: {summary.get('hold_days', '?')} days | "
        f"Min Score: {summary.get('min_score', '?')}"
    )
    lines.append("  " + "=" * 90)

    if not batches:
        lines.append("  No selections were made during the backtest period.")
        lines.append("")
        return "\n".join(lines)

    header = (
        f"  {'Batch':<6} {'Selected':>10} {'Avg Ret':>10} "
        f"{'Best Stock':<14} {'Best Ret':>10} "
        f"{'Worst Stock':<14} {'Worst Ret':>10}"
    )
    lines.append(header)
    lines.append("  " + "-" * 90)

    for i, b in enumerate(batches, 1):
        best_name = b["best_stock"]
        worst_name = b["worst_stock"]
        if len(best_name) > 12:
            best_name = best_name[:12]
        if len(worst_name) > 12:
            worst_name = worst_name[:12]
        line = (
            f"  {i:<6} {b['num_selected']:>8} stk {b['avg_return']:>+9.2f}% "
            f"{best_name:<14} {b['best_return']:>+9.2f}% "
            f"{worst_name:<14} {b['worst_return']:>+9.2f}%"
        )
        lines.append(line)

    lines.append("")
    lines.append("  Summary:")
    lines.append(f"    Total batches:      {summary['total_batches']}")
    lines.append(f"    Avg batch return:   {summary['avg_return']:+.2f}% ({summary.get('hold_days','?')}-day hold)")
    lines.append(f"    Win rate:           {summary['win_rate']:.1f}%")
    lines.append(f"    Best batch:         {summary['best_batch']:+.2f}%")
    lines.append(f"    Worst batch:        {summary['worst_batch']:+.2f}%")
    lines.append(f"    Annualized (est):   {summary['annualized']:+.1f}%")
    lines.append("")
    return "\n".join(lines)
