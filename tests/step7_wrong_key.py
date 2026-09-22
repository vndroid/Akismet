#!/usr/bin/env python3
"""第七步: 保存配置时的 Key 校验（插件的 validate）。

- 真实 Key + 当前服务地址 → 通过
- 改错一位的 Key → 不通过（Akismet 返回 invalid, 不写日志）
- 连不上的服务地址 → 不通过, 写一条日志, 且不能抛异常（旧版这里会让后台 500）
只调用插件的校验函数, 不会修改已保存的配置。
"""

import common

args = common.make_parser(__doc__).parse_args()
info = common.site_info(args)
key, url = info['key'], info['url']

print()
res, logs = common.probe(args, 'validate', key=key, url=url)
common.check('真实 Key 校验通过', res['valid'] is True)
common.show_logs(logs)

res, logs = common.probe(args, 'validate', key=key[:-1] + ('x' if key[-1] != 'x' else 'y'), url=url)
common.check('错误 Key 校验不通过', res['valid'] is False)
common.check('错误 Key 不写日志', not logs)
common.show_logs(logs)

res, logs = common.probe(args, 'validate', key=key, url='http://127.0.0.1:9')
common.check('服务不可达时校验不通过且不抛异常', res['valid'] is False)
common.check('服务不可达时写了日志', any(l.startswith('Akismet verify-key:') for l in logs))
common.show_logs(logs)
common.finish()
