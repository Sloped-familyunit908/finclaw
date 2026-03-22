import urllib.request, re, sys, io
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

codes = 'sz000533,sh601919,sz001267,sz002151,sz000617,sz002636,sh601669,sz002015,sz001309,sz300274,sz301308,sh600821,sh600989,sh600722,sh688048,sh601117,sh603083,sh605117,sz300085,sh688472'
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
