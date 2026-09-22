#!/usr/bin/env python3
"""第五步: 管理员评论应保持 approved（插件发送 user_role=administrator）。

分两部分:
1. 确认插件为管理员算出的 user_role 是 administrator, 为游客算出的是空（不发送）;
2. 管理员用正常内容评论, 经真实 Akismet 判定后保持 approved。

注意: 不能用 akismet-guaranteed-spam 来测管理员 —— Akismet 的固定垃圾值优先级高于 user_role,
带着它的请求即使 user_role=administrator 也会返回 true（直接调用接口也是如此）。
只调用插件, 不写数据库。
"""

import common

args = common.make_parser(__doc__).parse_args()
info = common.site_info(args)
admin = info['admin'] or common.die('找不到管理员账号')
cid = info['post']['cid'] if info['post'] else 1
text = '补充一点：如果开启了全页缓存，改完配置后记得清一下缓存再看效果。'

print(f"\n插件为评论者计算的 user_role")
c_admin = common.comment(admin['screenName'], text, author_id=int(admin['uid']), cid=cid)
c_guest = common.comment('李明', text, mail='liming.reader@gmail.com', cid=cid)
role, _ = common.probe(args, 'user_role', comment=c_admin)
common.check('管理员 → administrator', role['role'] == 'administrator', f"role={role['role']}")
role, _ = common.probe(args, 'user_role', comment=c_guest)
common.check('游客 → 不发送', role['role'] is None, f"role={role['role']}")

print(f"\n管理员 {admin['screenName']}（uid={admin['uid']}）用正常内容评论")
res, logs = common.probe(args, 'filter', cid=cid, comment=c_admin, api='comment-check')
common.check('管理员评论保持 approved', res['status'] == 'approved', f"status={res['status']}")
common.check('插件没有记录异常', not logs)
common.show_logs(logs)
common.finish()
