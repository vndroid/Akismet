#!/usr/bin/env python3
"""第六步: 后台纠正误判 → 插件向 Akismet 回报 submit-spam / submit-ham。

用一条虚构的游客评论依次回报 spam 和 ham, 两次都应收到
「Thanks for making the web a better place.」—— 插件收到别的响应会写日志, 这里检查没有日志。
只调用插件, 不写数据库。

注意: 回报接口不支持 is_test, 这两次回报会被 Akismet 当作你账号的真实纠错,
所以需要加 --yes 确认后才会执行。
"""

import common

p = common.make_parser(__doc__)
p.add_argument('--yes', action='store_true', help='确认向 Akismet 发送两次回报')
args = p.parse_args()
if not args.yes:
    common.die('这一步会向 Akismet 发送真实回报, 确认后加 --yes 重新运行')

info = common.site_info(args)
cid = info['post']['cid'] if info['post'] else 1
c = common.comment('Akismet Probe', 'akismet plugin feedback test, please ignore', mail='probe@example.com', cid=cid)

for api in ('submit-spam', 'submit-ham'):
    print(f'\n{api}')
    _, logs = common.probe(args, 'filter', cid=cid, comment=c, api=api)
    common.check(f'{api} 收到成功响应', not logs)
    common.show_logs(logs)

common.finish()
