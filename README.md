# Akismet

## Akismet Anti-Spam Plugin For Typecho

A Typecho plugin that uses the [Akismet](https://akismet.com) service to catch spam in comments, trackbacks and pingbacks.

## Intro

Current Version: [CHANGELOG](/CHANGELOG)

Current Language: **English** | [Simplified Chinese](/README_CN.md)

### Latest Update Description

- Requests rewritten to follow the official Akismet API docs (API key in the request body, urlencoded).
- Removed Typepad AntiSpam, which no longer exists.
- Comments by administrators are no longer flagged as spam.
- The service URL is validated, and a custom port is honoured.
- Service failures are written to the PHP error log instead of being silently ignored.
- Saving the settings no longer returns a 500 when Akismet is unreachable.

### Install

1. Download this repository and put it under `usr/plugins/`. **The directory must be named `Akismet`.**
2. Enable it under *Console → Plugins*.
3. Enter your API key (from your [Akismet account](https://akismet.com/account/)) in the plugin settings and save. "Settings saved" means the key was verified.

### Notice

* The PHP `curl` extension is required; without it the plugin cannot be enabled.
* The plugin directory must be named `Akismet`, otherwise the namespace does not match and the plugin will not load.
* **Upgrading from 1.2.x**: the setting names are unchanged, so just replace the files — no need to re-enable the plugin or re-enter the key. If the service URL contains `?`, `#`, user info, or a scheme other than http/https, it is now treated as invalid and no requests are sent; fix it in the settings.
* **Service URL**: keep the default `https://rest.akismet.com` unless you reach Akismet through your own proxy. Only `http://` and `https://` are accepted; a port and a path prefix are allowed (e.g. `https://proxy.example.com:8443/akismet`), and requests go to `<service URL>/1.1/<endpoint>`.
* **Comments are let through when the service fails.** If the key is invalid, Akismet returns an error or an unrecognised response, the request times out (5 s) or cannot connect, the comment is stored with its original status and a line starting with `Akismet ` is written to the PHP error log, including the HTTP status and Akismet's debug message:

  ```bash
  grep "Akismet " /path/to/php-fpm/error.log
  ```

* **Comments by logged-in users** carry `user_role` (the Typecho user group). Per the Akismet docs, `administrator` is always treated as not spam.
* Marking a comment as spam, or restoring one from spam, in the admin panel reports it back to Akismet (submit-spam / submit-ham). **These reports are synchronous and can take up to 5 s each**, so bulk-marking many comments while the service is slow may exceed your gateway timeout.
* Typecho core returns 404 for any trackback from an IP that already has a spam comment. That is core behaviour, not this plugin.
* **Privacy**: for every comment the visitor's IP, User-Agent, name, email, URL, comment text and a fixed allow-list of request headers (never cookies) are sent to Akismet (Automattic). Mention this in your privacy policy if needed.

### Features

- Checks comments, trackbacks and pingbacks; spam goes straight to the spam folder.
- Reports corrections made in the admin panel back to Akismet.
- Administrators' comments are exempt (`user_role`).
- Sends the full set of recommended fields: comment date, post modified date, site language and charset, and more.
- Custom port and path prefix in the service URL, for use behind a proxy.
- Service failures are logged, and network problems never break the settings page.
- Verified on Typecho 1.3.0 with PHP 8.4, with no deprecations or warnings at the highest error reporting level.

### Testing

[`tests/`](/tests) contains seven Python scripts that exercise the plugin with the real API key already saved in the admin panel. Run them on the server hosting Typecho (needs `python3` and the `php` CLI; no dependencies to install):

```bash
cd tests
python3 run_all.py --root /var/www/typecho          # steps 1–5 and 7
python3 run_all.py --root /var/www/typecho --yes    # also step 6 (sends reports to Akismet)
```

| Script | What it checks |
|---|---|
| `step1_api.py` | Calls Akismet directly, bypassing the plugin, to confirm the key and network (with `is_test=1`) |
| `step2_trackback.py` | Sends a real trackback end to end and confirms it is marked as spam, then deletes it |
| `step3_guest_spam.py` | A guest comment using Akismet's guaranteed-spam values is marked as spam |
| `step4_guest_normal.py` | A normal guest comment stays approved (a spam verdict is only a warning) |
| `step5_admin_comment.py` | An administrator's comment stays approved, and the plugin sends `administrator` |
| `step6_mark_feedback.py` | Spam / ham reports receive a success response (requires `--yes`) |
| `step7_wrong_key.py` | Key verification when saving settings: valid key, wrong key, unreachable service |

The test scripts are not needed on, and should not be deployed to, the web root; `.gitattributes` excludes `tests/` from release archives.

### Author

<a href="https://github.com/vndroid/Akismet/graphs/contributors">
<img src="https://contrib.rocks/image?repo=vndroid/Akismet" />
</a>

And origin author

[@joyqi](https://github.com/joyqi) ([typecho-plugins](https://github.com/joyqi/typecho-plugins))

### License

[BSD 3-Clause](/LICENSE)
