"""Fail closed if staged/tracked release files contain private runtime state."""
from pathlib import Path
import re
import subprocess
import sys
root = Path(__file__).resolve().parents[1]
files = subprocess.check_output(['git', 'ls-files', '-z'], cwd=root).decode().split('\0')
errors = []
public_base = '60b9dec46e9ffae97a87cad0905a654acc726167'
def public_example(name, value):
    # Public upstream documentation contains dummy /home/user paths and URL examples.
    upstream_name = re.sub('sickshift', lambda m: 'sickgear' if m.group().islower() else 'SickGear', name, flags=re.I)
    result = subprocess.run(['git', 'show', public_base + ':' + upstream_name], cwd=root, capture_output=True)
    original_value = re.sub('sickshift', 'sickgear', value, flags=re.I)
    return result.returncode == 0 and original_value.encode() in result.stdout

for name in filter(None, files):
    p = root / name
    if not p.is_file():
        continue
    if (p.suffix.lower() in {'.db', '.sqlite', '.sqlite3', '.log'} or
        name.startswith(('backup/', 'backups/', 'Logs/', '.aws/', '.code' + 'x/', '.agents/', 'venv/')) or
        (p.name.startswith('.env') and p.name != '.env.example') or
        p.name in {'config.ini', 'SICKSHIFT_LOCAL.md', 'SICKSHIFT_MIGRATION.json'}):
        errors.append((name, 'runtime/private file'))
        continue
    try:
        text = p.read_text(encoding='utf-8')
    except (UnicodeError, OSError):
        continue
    checks = {
        'personal machine path': r'/(?:home|Users)/[A-Za-z0-9_.-]+/',
        'embedded URL credential': r'https?://[^\s/\x22\x27]+:[^\s/\x22\x27]+@',
        'private key': r'-----BEGIN (?:RSA |OPENSSH |EC )?PRIVATE KEY-----',
        'GitHub token': r'\b(?:gh[pousr]_[A-Za-z0-9]{30,}|github_pat_[A-Za-z0-9_]{30,})\b',
        'embedded dashboard key': r'api_key\s*=\s*[\x22\x27][a-f0-9]{24,}[\x22\x27]',
    }
    for label, pattern in checks.items():
        for match in re.finditer(pattern, text):
            if not public_example(name, match.group()):
                errors.append((name, label))
                break
for name, reason in errors:
    print(f'BLOCKED {name}: {reason}')
print(f'Release privacy check: {len(files)-1} indexed files, {len(errors)} issue(s).')
sys.exit(bool(errors))
