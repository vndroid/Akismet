#!/usr/bin/env python3
"""按顺序跑完全部七步。参数原样传给每个脚本, 例如:

  python3 run_all.py --root /var/www/typecho --yes
"""

import os
import subprocess
import sys

here = os.path.dirname(os.path.abspath(__file__))
steps = ['step1_api.py', 'step2_trackback.py', 'step3_guest_spam.py', 'step4_guest_normal.py',
         'step5_admin_comment.py', 'step6_mark_feedback.py', 'step7_wrong_key.py']
extra = sys.argv[1:]
failed = []
for s in steps:
    print(f'\n========== {s} ==========')
    argv = extra if s == 'step6_mark_feedback.py' else [a for a in extra if a != '--yes']
    if s == 'step6_mark_feedback.py' and '--yes' not in argv:
        print('跳过（需要 --yes 确认向 Akismet 发送回报）')
        continue
    if subprocess.run([sys.executable, os.path.join(here, s), *argv]).returncode != 0:
        failed.append(s)
print('\n全部通过' if not failed else f"\n失败: {', '.join(failed)}")
sys.exit(1 if failed else 0)
