import sys, io, urllib.request
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
url = 'https://qt.gtimg.cn/q=sh600438'
data = urllib.request.urlopen(url, timeout=10).read().decode('gbk')
start = data.find('"')
val = data[start+1:].rstrip('";')
parts = val.split('~')
if len(parts) > 10:
    name = parts[1]
    cur = parts[3]
    prev = parts[4]
    cur_f = float(cur)
    prev_f = float(prev)
    chg = (cur_f - prev_f) / prev_f * 100
    print(name + ': ' + cur + ' ({:+.2f}%)'.format(chg) + '  prev=' + prev)
