#!/usr/bin/env python3
"""第一步: 绕开插件, 直接用 API Key 调用 Akismet 接口。

验证 Key 有效、服务器能连上 Akismet、urlencoded 请求被接受。所有请求都带 is_test=1,
不会影响 Akismet 对你账号的判定。

默认从插件配置里读取 Key、服务地址和站点地址（需在 Typecho 服务器上运行）;
加 --ask-key 则手动输入 Key（输入不回显）, 配合 --blog 可在任意机器上运行。
"""

import getpass
import sys
import urllib.error
import urllib.parse
import urllib.request

import common

p = common.make_parser(__doc__)
p.add_argument('--ask-key', action='store_true', help='手动输入 API Key, 不读插件配置')
p.add_argument('--blog', help='站点首页地址（配合 --ask-key 使用）')
p.add_argument('--url', help='服务地址, 默认取插件配置, 否则 https://rest.akismet.com')
args = p.parse_args()

if args.ask_key:
    key = getpass.getpass('API Key: ').strip()
    blog = args.blog or common.die('--ask-key 需要同时用 --blog 指定站点首页地址')
    base = args.url or 'https://rest.akismet.com'
else:
    info = common.site_info(args)
    key, blog = info['key'], info['siteUrl']
    base = args.url or info['url'] or 'https://rest.akismet.com'

base = base.rstrip('/')
UA = 'Typecho-Akismet-Test/1.0 | Akismet/1.3.0'


def call(api, **fields):
    data = urllib.parse.urlencode(dict(fields, blog=blog)).encode()
    req = urllib.request.Request(f'{base}/1.1/{api}', data=data, method='POST', headers={
        'Content-Type': 'application/x-www-form-urlencoded; charset=UTF-8', 'User-Agent': UA})
    try:
        with urllib.request.urlopen(req, timeout=10) as r:
            return r.status, r.read().decode(errors='replace').strip(), dict(r.headers)
    except urllib.error.HTTPError as e:
        return e.code, e.read().decode(errors='replace').strip(), dict(e.headers)
    except (urllib.error.URLError, OSError) as e:
        common.die(f'连不上 {base}: {e}')


def debug(headers):
    h = {k.lower(): v for k, v in headers.items()}
    return h.get('x-akismet-debug-help') or h.get('x-akismet-error') or ''


print(f'\n直接调用 {base}')

status, body, h = call('verify-key', key=key, api_key=key)
common.check('verify-key 返回 valid', body == 'valid', f'HTTP {status} "{body[:60]}" {debug(h)}'.strip())
if body != 'valid':
    print('  Key 无效或接口不可用, 后面的测试没有意义, 停止。')
    common.finish()

status, body, h = call('verify-key', key=key + 'x', api_key=key + 'x')
common.check('错误的 Key 返回 invalid', body == 'invalid', f'HTTP {status} "{body[:60]}"')

base_fields = dict(api_key=key, user_ip='203.0.113.10', user_agent='Mozilla/5.0', comment_type='comment',
                   blog_lang='zh_cn', blog_charset='UTF-8', is_test='1')

status, body, h = call('comment-check', **base_fields, comment_author='akismet-guaranteed-spam',
                       comment_author_email='akismet-guaranteed-spam@example.com', comment_content='test')
common.check('固定垃圾值 → true', body == 'true', f'HTTP {status} "{body[:60]}" {debug(h)}'.strip())

# 按官方文档: 其他字段用正常值, 只把 user_role 设为 administrator。
# 不能夹带 akismet-guaranteed-spam —— 固定垃圾值优先级更高, 会让结果变成 true。
status, body, h = call('comment-check', **base_fields, comment_author='Akismet Probe',
                       comment_author_email='probe@example.com',
                       comment_content='Thanks for the detailed write-up, it helped me fix my setup.',
                       user_role='administrator')
common.check('user_role=administrator → false', body == 'false', f'HTTP {status} "{body[:60]}" {debug(h)}'.strip())

status, body, h = call('comment-check', **dict(base_fields, api_key=key + 'x'), comment_author='x', comment_content='x')
common.check('comment-check 用错误 Key 返回 invalid', body == 'invalid', f'HTTP {status} "{body[:60]}" {debug(h)}'.strip())

common.finish()
