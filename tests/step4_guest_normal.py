#!/usr/bin/env python3
"""第四步: 游客发正常评论 → 插件应保持 approved。

Akismet 对正常评论的判断取决于内容、IP 等, 并不保证一定是 false,
所以被判为 spam 时这里只给 WARN, 不算失败; 关键是插件没有记录异常。
可用 --ip 换成真实访客常见的 IP、--text 换成更像真人写的内容。只调用插件, 不写数据库。
"""

import common

p = common.make_parser(__doc__)
p.add_argument('--ip', default='203.0.113.10', help='模拟的访客 IP')
p.add_argument('--text', default='这篇文章里关于缓存失效的部分讲得很清楚，我按照步骤在自己的站点上试了一下，问题解决了，谢谢分享。')
args = p.parse_args()
info = common.site_info(args)
cid = info['post']['cid'] if info['post'] else 1

print('\n游客正常评论')
c = common.comment('李明', args.text, mail='liming.reader@gmail.com', ip=args.ip, cid=cid)
res, logs = common.probe(args, 'filter', cid=cid, comment=c, api='comment-check')
if res['status'] == 'approved':
    common.check('状态保持 approved', True)
else:
    common.warn(f"被判为 {res['status']}（Akismet 的判断, 不一定是插件问题; 可换 --ip / --text 再试）")
common.check('插件没有记录异常', not logs)
common.show_logs(logs)
common.finish()
