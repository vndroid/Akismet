#!/usr/bin/env python3
"""第二步: 端到端测试 trackback（真实 HTTP 请求 → Typecho → 插件 → Akismet）。

向最新一篇允许引用的文章发送博客名为 akismet-guaranteed-spam 的 trackback, 然后查库确认它被标为 spam。
测完默认删除这条测试记录（--keep 保留）。

注意: Typecho 核心会拒绝「已有 spam 评论的 IP」发来的 trackback（返回 404）,
所以请在其他测试之前先跑这一步, 或者从另一个 IP 发送。
"""

import time
import urllib.error
import urllib.parse
import urllib.request

import common

p = common.make_parser(__doc__)
p.add_argument('--keep', action='store_true', help='保留测试写入的 trackback 记录')
args = p.parse_args()

info = common.site_info(args)
post = info['post']
if not post:
    common.die('找不到允许被引用的已发布文章, 请在某篇文章的高级选项里勾选「允许被引用」')

if not post['permalink'].startswith('http'):
    common.die(f"算出的文章地址不正确: {post['permalink']}")

print(f"\n目标文章 cid={post['cid']} 《{post['title']}》\ntrackback 地址 {post['trackbackUrl']}")

src = f'https://example.com/akismet-test/{int(time.time())}'
data = urllib.parse.urlencode({'blog_name': 'akismet-guaranteed-spam', 'url': src,
                               'title': 'Akismet test', 'excerpt': 'akismet plugin trackback test'}).encode()
# 不能带 Referer: Typecho 收到带 Referer 的 trackback 会直接重定向
req = urllib.request.Request(post['trackbackUrl'], data=data, method='POST',
                             headers={'User-Agent': 'Typecho-Akismet-Test/1.0'})
try:
    with urllib.request.urlopen(req, timeout=30) as r:
        status, body = r.status, r.read().decode(errors='replace')
except urllib.error.HTTPError as e:
    status, body = e.code, e.read().decode(errors='replace')

if status == 404:
    common.check('trackback 被接受', False, '404: 发送方 IP 已有 spam 评论, Typecho 核心直接拒绝; 换个 IP 或先清理该 IP 的 spam 记录')
    common.finish()

common.check('trackback 被接受', status == 200 and 'Trackback has registered' in body, f'HTTP {status} {body[-120:].strip()}')

row, _ = common.probe(args, 'find', cid=post['cid'], url=src)
row = row['row']
common.check('记录已入库', row is not None)
if row:
    common.check('被 Akismet 标为 spam', row['status'] == 'spam', f"coid={row['coid']} status={row['status']}")
    if not args.keep:
        res, _ = common.probe(args, 'delete', coid=row['coid'])
        print(f"  已删除测试记录 coid={row['coid']}" if res['deleted'] else f"  未删除 coid={row['coid']}（状态不是 spam）, 请到后台手动处理")

common.finish()
