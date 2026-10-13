"""Compose independently refreshed iOS and Android snapshots, even after API failure."""
import copy
from datetime import date
import json
import os
from pathlib import Path

from download_badges import badge, check, update_download_copy


def combine(snapshot, configs, android):
    result = copy.deepcopy(snapshot)
    for config in configs:
        row = result['apps'][config['id']]
        package = config.get('android_package')
        other = 0
        if package:
            check(android.get('version') == 1, 'Missing verified Android snapshot')
            report = android['apps'].get(package, {})
            other = report.get('first_time')
            check(type(other) is int and other >= 0, 'Missing validated Android first-time count')
            date.fromisoformat(report['as_of'])
            row['android_as_of'] = report['as_of']
            row['android_package'] = package
        check(type(row['first_time']) is int and row['first_time'] >= 0, 'Invalid iOS first-time total')
        row['other_platform_downloads'] = other
        row['display_total'] = row['first_time'] + other
        row['badge'] = badge(row['display_total'])
    return result


def main():
    resume = Path(os.environ['PROFILE_RESUME_PATH'])
    readme = Path(os.environ.get('PROFILE_README_PATH', '../README.md'))
    path = resume.parent / 'ios-downloads.json'
    configs = json.loads(Path(__file__).with_name('ios-downloads.json').read_text())['apps']
    android = json.loads((resume.parent / 'android-downloads.json').read_text())
    snapshot = combine(json.loads(path.read_text()), configs, android)
    new_readme, new_resume = update_download_copy(readme.read_text(), resume.read_text(), [
        {**c, 'badge': snapshot['apps'][c['id']]['badge']} for c in configs])
    outputs = {path: json.dumps(snapshot, indent=2) + '\n', readme: new_readme, resume: new_resume}
    for target, content in outputs.items():
        if target.read_text() != content:
            temporary = target.with_name(target.name + '.tmp')
            temporary.write_text(content)
            temporary.replace(target)
    print('Mobile labels synchronized from the latest verified iOS and Android snapshots.')


if __name__ == '__main__':
    main()
