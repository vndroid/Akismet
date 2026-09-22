"""Akismet 插件真实 API Key 测试 —— 公共代码。

所有脚本都在 **装有 Typecho 的服务器上** 运行（需要 python3 和 php 命令行）。
插件相关的测试通过 php 命令行加载站点的 config.inc.php，直接调用插件代码，
使用的就是后台里配置的真实 API Key；这样可以绕开评论表单的反垃圾令牌和主题的 reCAPTCHA。

通用参数（每个脚本都支持）:
  --root   Typecho 根目录（默认: 环境变量 TYPECHO_ROOT，否则当前目录）
  --php    php 可执行文件（默认: 环境变量 PHP_BIN，否则 php）
"""

import argparse
import json
import os
import subprocess
import sys
import tempfile

PROBE_PHP = r'''<?php
error_reporting(E_ALL);
ini_set('display_errors', 'stderr');
ini_set('log_errors', '0');

$in = json_decode(stream_get_contents(STDIN), true);
chdir($in['root']);
require $in['root'] . '/config.inc.php';

use TypechoPlugin\Akismet\Plugin as Akismet;

$db = \Typecho\Db::get();
// 命令行下没有请求地址, 用库里的站点地址作为根地址, 否则文章地址会变成相对路径
if (!defined('__TYPECHO_ROOT_URL__')) {
    define('__TYPECHO_ROOT_URL__', rtrim((string) $db->fetchObject($db->select('value')->from('table.options')
        ->where('name = ? AND user = 0', 'siteUrl'))->value, '/'));
}
$options = \Widget\Options::alloc();
// 命令行下没有经过 Widget\Init, 手动装载路由表, 否则文章地址会算错
\Typecho\Router::setRoutes($options->routingTable);
$out = [];

switch ($in['action']) {
    case 'info':
        // 命令行下插件系统没有初始化, 直接读库里的启用列表
        $plugins = json_decode((string) $db->fetchObject($db->select('value')->from('table.options')
            ->where('name = ? AND user = 0', 'plugins'))->value, true);
        $out['activated'] = isset($plugins['activated']['Akismet']);
        $out['siteUrl'] = $options->siteUrl;
        $out['php'] = PHP_VERSION;
        $out['typecho'] = $options->generator;
        try {
            $cfg = $options->plugin('Akismet');
            $out['url'] = $cfg->url;
            $out['key'] = (string) $cfg->key;
        } catch (\Throwable $e) {
            $out['url'] = null;
            $out['key'] = '';
        }
        $file = $in['root'] . '/usr/plugins/Akismet/Plugin.php';
        $out['version'] = preg_match('/@version\s+(\S+)/', (string) @file_get_contents($file), $m) ? $m[1] : null;
        $admin = $db->fetchRow($db->select('uid', 'screenName')->from('table.users')
            ->where('`group` = ?', 'administrator')->order('uid', \Typecho\Db::SORT_ASC)->limit(1));
        $out['admin'] = $admin ?: null;
        $post = $db->fetchRow($db->select('cid')->from('table.contents')
            ->where('type = ? AND status = ? AND allowPing = ?', 'post', 'publish', '1')
            ->order('cid', \Typecho\Db::SORT_DESC)->limit(1));
        if ($post) {
            $w = \Widget\Contents\From::allocWithAlias('akismet-probe-' . $post['cid'], ['cid' => $post['cid']]);
            $out['post'] = ['cid' => (int) $post['cid'], 'title' => $w->title,
                'permalink' => $w->permalink, 'trackbackUrl' => $w->trackbackUrl];
        } else {
            $out['post'] = null;
        }
        break;

    case 'validate':
        $_GET['url'] = $in['url'];
        $out['valid'] = Akismet::validate($in['key']);
        break;

    case 'filter':
        $post = \Widget\Contents\From::allocWithAlias('akismet-probe-' . $in['cid'], ['cid' => $in['cid']]);
        $result = Akismet::filter($in['comment'], $post, null, $in['api']);
        $out['status'] = $result['status'];
        break;

    case 'user_role':
        $m = new \ReflectionMethod(Akismet::class, 'userRole');
        $out['role'] = $m->invoke(null, $in['comment']);
        break;

    case 'find':
        $row = $db->fetchRow($db->select('coid', 'status', 'type', 'author')->from('table.comments')
            ->where('cid = ? AND url = ?', $in['cid'], $in['url'])->order('coid', \Typecho\Db::SORT_DESC)->limit(1));
        $out['row'] = $row ?: null;
        break;

    case 'delete':
        // 只删测试写入的 spam 记录; spam 不计入文章评论数, 不需要修正 commentsNum
        $out['deleted'] = $db->query($db->delete('table.comments')
            ->where('coid = ? AND status = ?', $in['coid'], 'spam'));
        break;
}

echo json_encode($out, JSON_UNESCAPED_UNICODE | JSON_UNESCAPED_SLASHES);
'''


def make_parser(description):
    p = argparse.ArgumentParser(description=description)
    p.add_argument('--root', default=os.environ.get('TYPECHO_ROOT', os.getcwd()), help='Typecho 根目录')
    p.add_argument('--php', default=os.environ.get('PHP_BIN', 'php'), help='php 可执行文件')
    return p


def probe(args, action, **payload):
    """在 php 命令行里加载站点并执行一个动作; 返回 (结果 dict, 插件写出的日志行列表)。"""
    root = os.path.abspath(args.root)
    if not os.path.isfile(os.path.join(root, 'config.inc.php')):
        die(f'{root} 下没有 config.inc.php, 请用 --root 指定 Typecho 根目录')

    with tempfile.NamedTemporaryFile('w', suffix='.php', delete=False, encoding='utf-8') as f:
        f.write(PROBE_PHP)
        script = f.name
    try:
        proc = subprocess.run(
            [args.php, '-d', 'error_log=', script],
            input=json.dumps(dict(payload, action=action, root=root)),
            capture_output=True, text=True, timeout=60,
        )
    except FileNotFoundError:
        die(f'找不到 php 命令: {args.php}（可用 --php 指定路径）')
    finally:
        os.unlink(script)

    stderr = [l for l in proc.stderr.splitlines() if l.strip()]
    logs = [l[l.index('Akismet '):] for l in stderr if 'Akismet ' in l]
    php_errors = [l for l in stderr if 'Akismet ' not in l]
    if proc.returncode != 0 or not proc.stdout.strip():
        die('php 执行失败:\n' + proc.stdout[-2000:] + '\n' + '\n'.join(stderr[-30:]))
    if php_errors:
        warn('PHP 输出了诊断信息:\n  ' + '\n  '.join(php_errors))
    return json.loads(proc.stdout[proc.stdout.index('{'):]), logs


def site_info(args, need_key=True):
    info, _ = probe(args, 'info')
    print(f"站点 {info['siteUrl']} | {info['typecho']} | PHP {info['php']} | 插件版本 {info['version']}")
    if not info['activated']:
        die('Akismet 插件没有启用')
    if need_key and not info['key']:
        die('插件还没有配置 API Key, 请先在后台保存配置')
    if need_key:
        print(f"服务地址 {info['url']} | API Key {mask(info['key'])}")
    return info


def comment(author, text, *, mail='', url='', ip='203.0.113.10', author_id=0, ctype='comment', cid=0):
    import time
    return {
        'cid': cid, 'created': int(time.time()), 'type': ctype, 'status': 'approved',
        'agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 14_0) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.0 Safari/605.1.15',
        'ip': ip, 'author': author, 'mail': mail, 'url': url, 'text': text, 'authorId': author_id,
    }


def mask(key):
    return (key[:2] + '*' * (len(key) - 4) + key[-2:]) if len(key) > 4 else '****'


RESULTS = {'pass': 0, 'fail': 0, 'warn': 0}


def check(name, ok, detail=''):
    RESULTS['pass' if ok else 'fail'] += 1
    print(f"  {'PASS' if ok else 'FAIL'}  {name}" + (f'  ({detail})' if detail else ''))
    return ok


def warn(msg):
    RESULTS['warn'] += 1
    print(f'  WARN  {msg}')


def show_logs(logs):
    for l in logs:
        print(f'        日志: {l}')


def die(msg):
    print(f'错误: {msg}', file=sys.stderr)
    sys.exit(2)


def finish():
    print(f"\n结果: {RESULTS['pass']} 通过, {RESULTS['fail']} 失败, {RESULTS['warn']} 警告")
    sys.exit(1 if RESULTS['fail'] else 0)
