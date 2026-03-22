import urllib.request, re, sys, io
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

codes = 'sh688766,sh601899,sz301611,sh603799,sz002342,sh600570,sh603179,sh688777,sh600143,sz002222,sz300803,sz002931,sz301550,sh603993,sz300339,sh601168,sh688361,sz002361,sz300655,sz002600,sz300496,sz000425,sz002738,sh600588,sh600031,sz300316,sh600760,sh688726,sz000426,sz300842'
url = f'https://qt.gtimg.cn/q={codes}'
data = urllib.request.urlopen(url).read()

for enc in ['gbk', 'gb2312', 'utf-8']:
    try:
        text = data.decode(enc)
        break
    except:
        continue

for line in text.split(';'):
    line = line.strip()
    m = re.match(r'v_(\w+)="\d+~(.+?)~(\d+)~([\d.]+)', line)
    if m:
        var_name = m.group(1)
        name = m.group(2)
        code = m.group(3)
        price = m.group(4)
        print(f'{var_name}: {name} ({code}) price={price}')
