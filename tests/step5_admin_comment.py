#!/usr/bin/env python3
"""第五步: 管理员评论即使内容是固定垃圾值, 也应保持 approved（插件发送 user_role=administrator）。

同时做一次对照: 同样的内容以游客身份提交, 应被判为 spam —— 证明是 user_role 起了作用。
只调用插件, 不写数据库。
"""

import common

args = common.make_parser(__doc__).parse_args()
info = common.site_info(args)
admin = info['admin'] or common.die('找不到管理员账号')
cid = info['post']['cid'] if info['post'] else 1

print(f"\n管理员 {admin['screenName']}（uid={admin['uid']}）评论, 正文为 akismet-guaranteed-spam")
c = common.comment(admin['screenName'], 'akismet-guaranteed-spam', author_id=int(admin['uid']), cid=cid)
res, logs = common.probe(args, 'filter', cid=cid, comment=c, api='comment-check')
common.check('管理员评论保持 approved', res['status'] == 'approved', f"status={res['status']}")
common.show_logs(logs)

print('\n对照: 同样内容以游客身份提交')
c = common.comment('akismet-guaranteed-spam', 'akismet-guaranteed-spam',
                   mail='akismet-guaranteed-spam@example.com', cid=cid)
res, logs2 = common.probe(args, 'filter', cid=cid, comment=c, api='comment-check')
common.check('游客评论被判 spam', res['status'] == 'spam', f"status={res['status']}")
common.check('插件没有记录异常', not logs and not logs2)
common.show_logs(logs2)
common.finish()
