import sys, io, urllib.request, re
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

codes = 'sz000533,sh601919,sz001267,sz002151,sz000617,sz002636,sh601669,sz002015,sz001309,sz300274,sh603799,sh601899,sz301171,sz300655,sh688361,sh603993,sz300803,sh600143,sh603179,sz002342'
url = 'https://qt.gtimg.cn/q=' + codes
data = urllib.request.urlopen(url).read()
text = data.decode('gbk')

for line in text.split(';'):
    line = line.strip()
    m = re.match(r'v_(\w+)="\d+~(.+?)~(\d+)~([\d.]+)~([\d.]+)', line)
    if m:
        code = m.group(3)
        name = m.group(2)
        price = m.group(4)
        prev_close = m.group(5)
        print(code + ': ' + name + ' | now=' + price + ' | prev=' + prev_close)
