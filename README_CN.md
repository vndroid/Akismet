# Akismet

## Typecho 反垃圾评论插件

使用 [Akismet](https://akismet.com) 服务识别垃圾评论、引用（trackback）和广播（pingback）的 Typecho 插件。

## 简介

当前版本： [CHANGELOG](/CHANGELOG)

当前语言： [英文](/README.md) | **简体中文**

### 最近更新

- 按 Akismet 官方文档重写请求方式（API Key 放在请求体、urlencoded 格式）
- 移除已停止服务的 Typepad AntiSpam
- 管理员评论不再被误判为垃圾
- 服务地址增加格式校验，支持自定义端口
- 服务异常时写入 PHP 错误日志，不再静默放行
- 修复 Akismet 不可达时保存配置导致后台 500

### 安装

1. 下载本仓库，把目录放到 `usr/plugins/` 下，**目录名必须是 `Akismet`**；
2. 在后台「控制台 → 插件」中启用；
3. 在插件设置里填写 API Key（在 [Akismet 账户](https://akismet.com/account/) 中获取）并保存。看到「插件设置已经保存」即表示 Key 校验通过。

### 注意事项

* 需要 PHP 的 `curl` 扩展，没有时插件无法启用；
* 插件所在目录名必须为 `Akismet`，否则命名空间对不上，插件无法加载；
* **从 1.2.x 升级**：配置项名称没有变化，直接覆盖文件即可，不需要重新启用或重新填写 Key。
  但如果服务地址里填过带 `?`、`#`、用户名或非 http/https 协议的地址，升级后会被视为不合法而停止请求，请到设置里改正；
* **服务地址**一般保持默认的 `https://rest.akismet.com`，只在需要经由自建代理访问时修改。
  只接受 `http://` 或 `https://`，可以带端口和路径前缀（例如 `https://proxy.example.com:8443/akismet`），
  请求会发到 `<服务地址>/1.1/<接口名>`；
* **服务异常时评论会被放行**：Key 失效、Akismet 返回错误或无法识别的内容、超时（5 秒）或连不上时，评论按原状态入库，
  同时向 PHP 错误日志写一条以 `Akismet ` 开头的记录，带 HTTP 状态码和 Akismet 给的出错说明。排查时：

  ```bash
  grep "Akismet " /path/to/php-fpm/error.log
  ```

* **登录用户的评论**会带上 `user_role`（取 Typecho 用户组）。按 Akismet 文档，`administrator` 一律判为正常；
* 在后台把评论标为垃圾或从垃圾恢复时，插件会向 Akismet 回报（submit-spam / submit-ham），用于改进对你站点的判定。
  **回报是同步的，每条最多等 5 秒**，服务慢时一次批量标记大量评论可能超出网关超时；
* 按 Typecho 核心规则，同一 IP 只要有过一条垃圾评论，之后它发来的 trackback 一律返回 404，这不是插件行为；
* **隐私**：每条评论都会把访客 IP、User-Agent、昵称、邮箱、网址、评论正文，以及部分请求头发送给 Akismet（Automattic 公司）。
  请求头只取固定白名单，不包含 Cookie。如有需要，请在站点隐私政策中说明。

### 功能亮点

- 检查评论、trackback、pingback，垃圾内容自动进入垃圾箱
- 后台纠正误判时自动回报 Akismet
- 管理员评论免判（`user_role`）
- 发送文档推荐的完整字段：评论时间、文章修改时间、站点语言与字符集等
- 服务地址支持自定义端口与路径前缀，便于经由代理访问
- 服务异常有日志可查，保存配置不会因网络问题报错
- 已在 Typecho 1.3.0 + PHP 8.4 下验证，开启全部报错级别无任何弃用或警告

### 功能测试

[`tests/`](/tests) 目录里是七个 Python 脚本，使用后台已保存的真实 API Key 做功能测试。
需要在装有 Typecho 的服务器上运行（要有 `python3` 和 `php` 命令行，无需安装依赖）：

```bash
cd tests
python3 run_all.py --root /var/www/typecho          # 第 1～5、7 步
python3 run_all.py --root /var/www/typecho --yes    # 连同第 6 步（向 Akismet 发送回报）一起
```

| 脚本 | 内容 |
|---|---|
| `step1_api.py` | 不经过插件直接调用 Akismet，确认 Key 与网络可用（请求带 `is_test=1`） |
| `step2_trackback.py` | 端到端发送一条 trackback，确认被标为垃圾，测完自动删除 |
| `step3_guest_spam.py` | 游客使用固定垃圾值评论，应被判垃圾 |
| `step4_guest_normal.py` | 游客正常评论，应保持通过（被判垃圾只给警告） |
| `step5_admin_comment.py` | 管理员评论应保持通过，并确认插件发送了 `administrator` |
| `step6_mark_feedback.py` | 回报 spam / ham，应收到成功响应（需 `--yes`） |
| `step7_wrong_key.py` | 保存配置时的 Key 校验：正确、错误、服务不可达三种情况 |

测试脚本不需要、也不应该部署到网站目录；本仓库的 `.gitattributes` 已把 `tests/` 排除在发布包之外。

### 开发者

<a href="https://github.com/vndroid/Akismet/graphs/contributors">
<img src="https://contrib.rocks/image?repo=vndroid/Akismet" />
</a>

原作者

[@joyqi](https://github.com/joyqi)（[typecho-plugins](https://github.com/joyqi/typecho-plugins)）

### 许可

[BSD 3-Clause](/LICENSE)
