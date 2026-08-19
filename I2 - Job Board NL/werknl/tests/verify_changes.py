"""WerkNL — ad-hoc verification of contact/button/seeding behavior.

Run:  python3 tests/verify_changes.py  (plain python, no pytest needed)
Covers: contact_url mapping, respond buttons, job post/DM links,
cmd_jobs buttons, /post contact validation, seed dedupe, seed_jobs.json,
and the db job lifecycle (tests/test_db.py).
"""
import importlib.util
import inspect
import json
import os
import subprocess
import sys

APP = r'C:\Users\veria\Desktop\Telegram-Ideas\I2 - Job Board NL\werknl'
os.chdir(APP)
sys.path.insert(0, APP)

FAILED = []


def check(name, fn):
    try:
        fn()
        print('  \u2713 ' + name)
    except Exception as e:
        print('  \u2717 ' + name + ' -> ' + repr(e))
        FAILED.append(name)


# ── 1. formatting.contact_url ──
from werknl.formatting import contact_url, respond_label, job_post_text, job_dm_text

check('contact_url: @user -> t.me', lambda: (_ for _ in ()).throw(AssertionError()) if contact_url('@iamyomih') != 'https://t.me/iamyomih' else None)
check('contact_url: url -> itself', lambda: (_ for _ in ()).throw(AssertionError()) if contact_url('https://www.youngcapital.nl/vacatures/1') != 'https://www.youngcapital.nl/vacatures/1' else None)
check('contact_url: phone -> tel:', lambda: (_ for _ in ()).throw(AssertionError()) if contact_url('+31 6 1234 5678') != 'tel:+31612345678' else None)
check('contact_url: junk -> empty', lambda: (_ for _ in ()).throw(AssertionError()) if contact_url('Telegram') != '' else None)
check('contact_url: empty -> empty', lambda: (_ for _ in ()).throw(AssertionError()) if contact_url('') != '' else None)

check('respond_label: chat/call/ad', lambda: (
    (_ for _ in ()).throw(AssertionError()) if respond_label('https://t.me/x') != '\U0001F4AC Chat' else None,
    (_ for _ in ()).throw(AssertionError()) if respond_label('tel:+316') != '\U0001F4DE Call' else None,
    (_ for _ in ()).throw(AssertionError()) if respond_label('https://example.com') != '\U0001F517 Open ad' else None,
))

job = {'title': 'Mover', 'sector': 'moving', 'area': 'Diemen', 'pay': '19/hr',
       'hours': '1 shift', 'description': 'help move boxes', 'contact': '@iamyomih'}

def test_post_link():
    t = job_post_text(job)
    assert 'href="https://t.me/iamyomih"' in t and '\U0001F4E9' in t
check('job_post_text: clickable contact', test_post_link)

def test_post_plain():
    t = job_post_text(dict(job, contact='Telegram'))
    assert '\U0001F4E9' in t and 'href=' not in t
check('job_post_text: junk contact stays plain text', test_post_plain)

def test_dm_link():
    t = job_dm_text(job)
    assert 'href="https://t.me/iamyomih"' in t
check('job_dm_text: clickable contact', test_dm_link)

# ── 2. digest._respond_button ──
from werknl.digest import _respond_button

def test_button_username():
    kb = _respond_button({'contact': '@iamyomih'})
    assert kb is not None and kb.inline_keyboard[0][0].url == 'https://t.me/iamyomih'
    assert kb.inline_keyboard[0][0].text == '\U0001F4AC Chat'
check('respond button: @username -> Chat button', test_button_username)

def test_button_url():
    kb = _respond_button({'contact': 'https://www.youngcapital.nl/vacatures/1'})
    assert kb is not None and kb.inline_keyboard[0][0].text == '\U0001F517 Open ad'
check('respond button: url -> Open ad button', test_button_url)

def test_button_phone():
    kb = _respond_button({'contact': '+31612345678'})
    assert kb is not None and kb.inline_keyboard[0][0].url == 'tel:+31612345678'
check('respond button: phone -> Call button', test_button_phone)

def test_button_none():
    assert _respond_button({'contact': 'Telegram'}) is None
check('respond button: junk contact -> no button', test_button_none)

# ── 3. bot.py: cmd_jobs buttons + post_contact validation ──
import werknl.bot as botmod

def test_cmd_jobs_buttons():
    src = inspect.getsource(botmod.cmd_jobs)
    assert 'contact_url' in src and 'reply_markup' in src and 'InlineKeyboardMarkup(keyboard)' in src
check('bot.cmd_jobs: builds per-job url buttons', test_cmd_jobs_buttons)

def test_post_contact_validation():
    src = inspect.getsource(botmod.post_contact)
    assert 'contact_url(contact)' in src and 'return CONTACT' in src
check('bot.post_contact: rejects invalid contact, re-prompts', test_post_contact_validation)

# ── 4. seed dedupe (end-to-end rerun) ──
def test_seed_dedupe():
    out = subprocess.run([sys.executable, '-m', 'werknl.seed', '--json', 'data/seed_jobs.json'],
                         capture_output=True, text=True, cwd=APP)
    assert out.returncode == 0, out.stderr[-300:]
    assert 'Inserted 0 pending seed jobs.' in out.stdout, out.stdout
check('seed: rerun inserts 0 (dedupe works)', test_seed_dedupe)

def test_seed_json_valid():
    jobs = json.load(open(os.path.join(APP, 'data', 'seed_jobs.json'), encoding='utf-8'))
    assert len(jobs) == 13
    assert all(j['contact'].startswith('http') for j in jobs)
    assert {j['sector'] for j in jobs} == {'horeca', 'cleaning'}
check('seed_jobs.json: 13 entries, real urls, horeca+cleaning', test_seed_json_valid)

# ── 5. existing db tests (pytest-style, run directly) ──
def test_db_module():
    spec = importlib.util.spec_from_file_location('test_db', os.path.join(APP, 'tests', 'test_db.py'))
    m = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(m)
    m.test_job_lifecycle()
check('tests/test_db.py: job lifecycle passes', test_db_module)

print()
if FAILED:
    print('FAILED: ' + ', '.join(FAILED))
    sys.exit(1)
print('ALL CHECKS PASSED \u2014 ad-hoc verification (not a suite)')
