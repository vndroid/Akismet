<?php

namespace TypechoPlugin\Akismet;

use Typecho\Common;
use Typecho\Db;
use Typecho\Http\Client;
use Typecho\Plugin\Exception;
use Typecho\Plugin\PluginInterface;
use Typecho\Request;
use Typecho\Widget\Helper\Form;
use Widget\Base;
use Widget\Base\Comments;
use Widget\Comments\Edit;
use Widget\Feedback;
use Widget\Options;
use Widget\XmlRpc;

if (!defined('__TYPECHO_ROOT_DIR__')) {
    exit;
}

/**
 * Akismet 反垃圾评论插件 for Typecho
 *
 * @package Akismet
 * @author joyqi
 * @version 1.3.0
 * @since 1.2.0
 * @link https://github.com/joyqi/typecho-plugins
 */
class Plugin implements PluginInterface
{
    /** 插件版本, 用于 User-Agent */
    private const VERSION = '1.3.0';

    /** 官方服务地址 */
    private const DEFAULT_URL = 'https://rest.akismet.com';

    /** submit-spam / submit-ham 成功时的响应体 */
    private const FEEDBACK_SUCCESS_BODY = 'Thanks for making the web a better place.';

    /**
     * 激活插件方法,如果激活失败,直接抛出异常
     *
     * @throws Exception
     */
    public static function activate()
    {
        if (null === Client::get()) {
            throw new Exception(_t('对不起, 您的主机没有启用 php-curl 扩展, 无法使用此插件'));
        }

        Feedback::pluginHandle()->comment = __CLASS__ . '::filter';
        Feedback::pluginHandle()->trackback = __CLASS__ . '::filter';
        XmlRpc::pluginHandle()->pingback = __CLASS__ . '::filter';
        Edit::pluginHandle()->mark = __CLASS__ . '::mark';

        return _t('请配置此插件的API KEY, 以使您的反垃圾策略生效');
    }

    /**
     * 禁用插件方法,如果禁用失败,直接抛出异常
     */
    public static function deactivate()
    {
    }

    /**
     * 获取插件配置面板
     *
     * @param Form $form 配置面板
     */
    public static function config(Form $form)
    {
        $key = new Form\Element\Text(
            'key',
            null,
            null,
            _t('API Key'),
            _t('在 <a href="https://akismet.com/account/" target="_blank" rel="noopener noreferrer">Akismet 账户</a> 中获取的 API Key')
        );
        $form->addInput($key->addRule('required', _t('您必须填写 API Key'))
            ->addRule([self::class, 'validate'], _t('API Key 校验失败, 请检查 API Key 与服务地址')));

        $url = new Form\Element\Text(
            'url',
            null,
            self::DEFAULT_URL,
            _t('服务地址'),
            _t('Akismet 接口地址, 一般保持默认的 %s 即可; 仅在需要经由自建代理访问时修改', self::DEFAULT_URL)
        );
        $form->addInput($url->addRule('required', _t('您必须填写服务地址'))
            ->addRule([self::class, 'validateUrl'], _t('服务地址只能是 http:// 或 https:// 开头的有效地址'))
            ->addRule('url', _t('您使用的地址格式错误')));
    }

    /**
     * 验证服务地址格式
     *
     * @param string $url 服务地址
     * @return boolean
     */
    public static function validateUrl(string $url): bool
    {
        return null !== self::parseServiceUrl($url);
    }

    /**
     * 解析服务地址, 格式不合法时返回 null
     *
     * 只接受 http/https; 拒绝 userinfo、query、fragment,
     * 以免拼接接口路径时改变实际请求的主机。
     *
     * @param mixed $url 服务地址
     * @return array|null
     */
    private static function parseServiceUrl($url): ?array
    {
        if (!is_string($url) || '' === $url) {
            return null;
        }

        $params = parse_url($url);
        if (false === $params || empty($params['scheme']) || empty($params['host'])) {
            return null;
        }

        $scheme = strtolower($params['scheme']);
        if (!in_array($scheme, ['http', 'https'], true)) {
            return null;
        }

        if (isset($params['user']) || isset($params['pass']) || isset($params['query']) || isset($params['fragment'])) {
            return null;
        }

        if (!preg_match('/^[a-z0-9](?:[a-z0-9.-]*[a-z0-9])?$/i', $params['host'])) {
            return null;
        }

        if (isset($params['port']) && ($params['port'] < 1 || $params['port'] > 65535)) {
            return null;
        }

        return [
            'scheme' => $scheme,
            'host'   => strtolower($params['host']),
            'port'   => $params['port'] ?? null,
            'path'   => rtrim($params['path'] ?? '', '/')
        ];
    }

    /**
     * 由解析结果拼出接口地址, 保留端口
     *
     * @param array $params parseServiceUrl 的返回值
     * @param string $api 接口名, 如 comment-check
     * @return string
     */
    private static function buildServiceUrl(array $params, string $api): string
    {
        $base = $params['scheme'] . '://'
            . $params['host']
            . (null === $params['port'] ? '' : ':' . $params['port'])
            . $params['path'];

        return Common::url('/1.1/' . $api, $base);
    }

    /**
     * 个人用户的配置面板
     *
     * @param Form $form
     */
    public static function personalConfig(Form $form)
    {
    }

    /**
     * 向 Akismet 发送请求
     *
     * 按官方文档: POST、application/x-www-form-urlencoded, API Key 放在 api_key 参数里。
     *
     * @param array $params parseServiceUrl 的返回值
     * @param string $api 接口名
     * @param string $key API Key
     * @param array $fields 请求字段（不含 api_key / blog）
     * @param int $timeout 超时秒数
     * @return Client
     * @throws Client\Exception
     */
    private static function request(array $params, string $api, string $key, array $fields, int $timeout): Client
    {
        $options = Options::alloc();

        $fields = array_merge($fields, [
            'api_key' => $key,
            'blog'    => $options->siteUrl
        ]);

        $client = Client::get();
        $client->setHeader('User-Agent', str_replace(' ', '/', $options->generator) . ' | Akismet/' . self::VERSION)
            ->setHeader('Content-Type', 'application/x-www-form-urlencoded; charset=' . ($options->charset ?: 'UTF-8'))
            ->setMultipart(false)
            ->setTimeout($timeout)
            ->setData($fields)
            ->send(self::buildServiceUrl($params, $api));

        return $client;
    }

    /**
     * 记录一次非预期的响应
     *
     * @param string $api 接口名
     * @param Client $client 已完成请求的客户端
     */
    private static function logUnexpected(string $api, Client $client)
    {
        $detail = $client->getResponseHeader('X-akismet-debug-help')
            ?? $client->getResponseHeader('X-akismet-error')
            ?? '';

        error_log(sprintf(
            'Akismet %s: unexpected response (HTTP %d) "%s"%s',
            $api,
            $client->getResponseStatus(),
            Common::subStr(trim($client->getResponseBody()), 0, 100, '...'),
            '' === $detail ? '' : ' - ' . $detail
        ));
    }

    /**
     * 验证api的key值
     *
     * @param string $key 服务密钥
     * @return boolean
     */
    public static function validate(string $key): bool
    {
        $params = self::parseServiceUrl(Request::getInstance()->get('url'));

        // 服务地址不合法时不发请求（Validate 先跑 key 的规则, 此时 url 还没被校验）
        if (null === $params || null === Client::get()) {
            return false;
        }

        try {
            // verify-key 读取的是 key 参数, 官方插件与 SDK 都同时带上 key 和 api_key
            $client = self::request($params, 'verify-key', $key, ['key' => $key], 5);
        } catch (Client\Exception $e) {
            error_log('Akismet verify-key: ' . $e->getMessage());
            return false;
        }

        $body = $client->getResponseBody();
        if ('valid' == $body) {
            return true;
        }

        if ('invalid' != $body) {
            self::logUnexpected('verify-key', $client);
        }

        return false;
    }

    /**
     * 标记评论状态时的插件接口
     *
     * @access public
     * @param array $comment 评论数据的结构体
     * @param Edit $commentWidget 评论组件
     * @param string $status 评论状态
     * @return void
     */
    public static function mark(array $comment, Edit $commentWidget, string $status)
    {
        if ('spam' == $comment['status'] && $status != 'spam') {
            self::filter($comment, $commentWidget, null, 'submit-ham');
        } elseif ('spam' != $comment['status'] && $status == 'spam') {
            self::filter($comment, $commentWidget, null, 'submit-spam');
        }
    }

    /**
     * 取被评论的文章组件
     *
     * 回报 ham/spam 时传进来的是评论组件, 换成它所属的文章。
     *
     * @param Base $post 被评论的文章或评论组件
     * @return Base
     */
    private static function postWidget(Base $post): Base
    {
        return $post instanceof Comments ? $post->parentContent : $post;
    }

    /**
     * 取被评论文章的地址
     *
     * 评论组件的 permalink 是评论地址（带 #comment-N, 开启评论分页时还是评论分页地址）,
     * 这里统一用所属文章的地址并去掉片段。
     *
     * @param Base $post 被评论的文章
     * @return string|null
     */
    private static function postPermalink(Base $post): ?string
    {
        $permalink = $post->permalink;
        if (!is_string($permalink) || '' === $permalink) {
            return null;
        }

        $pos = strpos($permalink, '#');
        return false === $pos ? $permalink : substr($permalink, 0, $pos);
    }

    /**
     * 取评论者在本站的用户组, 作为 Akismet 的 user_role
     *
     * Akismet 对 user_role=administrator 一律返回 false。
     *
     * @param array $comment 评论结构
     * @return string|null 游客返回 null
     */
    private static function userRole(array $comment): ?string
    {
        $uid = (int) ($comment['authorId'] ?? 0);
        if ($uid <= 0) {
            return null;
        }

        $db = Db::get();
        $user = $db->fetchRow($db->select('group')->from('table.users')->where('uid = ?', $uid)->limit(1));

        return empty($user['group']) ? null : $user['group'];
    }

    /**
     * 评论过滤器
     *
     * @param array $comment 评论结构
     * @param Base $post 被评论的文章
     * @param array|null $result 返回的结果上下文
     * @param string $api api地址
     * @return array
     */
    public static function filter(array $comment, Base $post, ?array $result, string $api = 'comment-check'): array
    {
        $comment = empty($result) ? $comment : $result;

        $options = Options::alloc();
        $url = $options->plugin('Akismet')->url;
        $key = $options->plugin('Akismet')->key;

        // 旧配置里可能存着不合法的地址, 这里再校验一次, 不合法则不发请求
        $params = self::parseServiceUrl($url);
        if (!$key || null === $params || null === Client::get()) {
            return $comment;
        }

        $isCheck = 'comment-check' == $api;
        $post = self::postWidget($post);

        $allowedServerVars = $isCheck ? [
            'SCRIPT_URI',
            'HTTP_HOST',
            'HTTP_USER_AGENT',
            'HTTP_ACCEPT',
            'HTTP_ACCEPT_LANGUAGE',
            'HTTP_ACCEPT_ENCODING',
            'HTTP_ACCEPT_CHARSET',
            'HTTP_KEEP_ALIVE',
            'HTTP_CONNECTION',
            'HTTP_CACHE_CONTROL',
            'HTTP_PRAGMA',
            'HTTP_DATE',
            'HTTP_EXPECT',
            'HTTP_MAX_FORWARDS',
            'HTTP_RANGE',
            'CONTENT_TYPE',
            'CONTENT_LENGTH',
            'SERVER_SIGNATURE',
            'SERVER_SOFTWARE',
            'SERVER_NAME',
            'SERVER_ADDR',
            'SERVER_PORT',
            'REMOTE_PORT',
            'GATEWAY_INTERFACE',
            'SERVER_PROTOCOL',
            'REQUEST_METHOD',
            'QUERY_STRING',
            'REQUEST_URI',
            'SCRIPT_NAME',
            'REQUEST_TIME'
        ] : [];

        $data = [
            'user_ip'                   => $comment['ip'],
            'user_agent'                => $comment['agent'],
            // 回报 ham/spam 发生在后台, 当前请求的来源是后台页面而非评论者的来源, 原始来源又没有入库, 因此不发
            'referrer'                  => $isCheck ? Request::getInstance()->getReferer() : null,
            'permalink'                 => self::postPermalink($post),
            'comment_type'              => $comment['type'],
            'comment_author'            => $comment['author'],
            'comment_author_email'      => $comment['mail'] ?? '',
            'comment_author_url'        => $comment['url'],
            'comment_content'           => $comment['text'],
            'comment_date_gmt'          => isset($comment['created']) ? gmdate('c', (int) $comment['created']) : null,
            'comment_post_modified_gmt' => $post->modified ? gmdate('c', (int) $post->modified) : null,
            'comment_lang'              => $options->lang ? strtolower(str_replace('-', '_', $options->lang)) : null,
            'comment_charset'           => $options->charset ?: null,
            'user_role'                 => self::userRole($comment)
        ];

        // 没有值的字段不发, 以免把空串当成有效数据交给 Akismet
        $data = array_filter($data, function ($value) {
            return null !== $value && '' !== $value;
        });

        foreach ($allowedServerVars as $val) {
            if (array_key_exists($val, $_SERVER)) {
                $data[$val] = $_SERVER[$val];
            }
        }

        // 内部统一用 comment_ 前缀命名, 请求接口前换成 Akismet 规定的字段名
        $apiFieldNames = [
            'comment_lang'    => 'blog_lang',
            'comment_charset' => 'blog_charset'
        ];

        $fields = [];
        foreach ($data as $name => $value) {
            $fields[$apiFieldNames[$name] ?? $name] = $value;
        }

        try {
            $client = self::request($params, $api, $key, $fields, 5);
        } catch (Client\Exception $e) {
            error_log('Akismet ' . $api . ': ' . $e->getMessage());
            return $comment;
        }

        $body = $client->getResponseBody();

        if ($isCheck) {
            if ('true' == $body) {
                $comment['status'] = 'spam';
            } elseif ('false' != $body) {
                // invalid（API Key 失效等）或非预期响应: 放行, 但必须留下记录
                self::logUnexpected($api, $client);
            }
        } elseif (self::FEEDBACK_SUCCESS_BODY != $body) {
            self::logUnexpected($api, $client);
        }

        return $comment;
    }
}
