#!/usr/bin/env python3
"""第三步: 游客发垃圾评论 → 插件应把状态改成 spam。

用 Akismet 官方的固定垃圾值（昵称 akismet-guaranteed-spam、邮箱 akismet-guaranteed-spam@example.com）
构造一条游客评论, 交给插件的 comment-check 过滤器。只调用插件, 不写数据库。
"""

import common

args = common.make_parser(__doc__).parse_args()
info = common.site_info(args)
cid = info['post']['cid'] if info['post'] else 1

print('\n游客评论, 昵称/邮箱为固定垃圾值')
c = common.comment('akismet-guaranteed-spam', 'Great post, thanks for sharing.',
                   mail='akismet-guaranteed-spam@example.com', cid=cid)
res, logs = common.probe(args, 'filter', cid=cid, comment=c, api='comment-check')
common.check('状态被改为 spam', res['status'] == 'spam', f"status={res['status']}")
common.check('插件没有记录异常', not logs)
common.show_logs(logs)
common.finish()
