"""Shared milestone formatting and exact-link README/resume updates."""
import re
from urllib.parse import quote


def check(condition, message):
    if not condition:
        raise ValueError(message)


def badge(count):
    check(type(count) is int and count >= 0, 'Invalid download total')
    if count < 10:
        return str(count)
    if count < 100:
        return f'{count // 10 * 10}+'
    if count < 1000:
        return f'{count // 100 * 100}+'
    if count < 1_000_000:
        return f'{count // 1000}K+'
    return f'{count // 1_000_000}M+'


def update_download_copy(readme, resume, entries):
    for item in entries:
        label = item['badge']
        check(re.fullmatch(r'\d{1,6}[KM]?\+?', label), 'Invalid download label')
        image = (f'<img alt="Downloads: {label}" src="https://apoorvdarshan.com/badges/downloads/v1/'
                 f'{quote(label, safe="")}.svg">')
        rows = readme.splitlines(keepends=True)
        matched = [i for i, line in enumerate(rows) if f'<strong><a href="{item["link"]}">' in line]
        check(len(matched) == 1, f'Expected one README entry for {item["name"]}')
        i = matched[0]
        rows[i], count = re.subn(r'<img\b[^>]*alt="Downloads: [^"]*"[^>]*>', lambda _: image, rows[i])
        check(count == 1, f'Missing/duplicate download badge for {item["name"]}')
        readme = ''.join(rows)
        rows = resume.splitlines(keepends=True)
        matched = [i for i, line in enumerate(rows)
                   if line.lstrip().startswith(r'\resumeProjectHeading') and
                   ('\\href{' + item['link'] + '}') in line]
        check(len(matched) == 1, f'Expected one resume entry for {item["name"]}')
        i = matched[0]
        rows[i], count = re.subn(r'(\\textcolor\{Maroon\}\{\$\\downarrow\$ )[^}]+',
                                 lambda m: m[1] + label, rows[i])
        check(count == 1, f'Missing/duplicate resume count for {item["name"]}')
        resume = ''.join(rows)
    return readme, resume
