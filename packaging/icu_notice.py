"""Verify original ICU terms against the exact V8 data dependency, offline."""
import hashlib
import json
from pathlib import Path
import re
import tarfile
from cargo_notice_evidence import obtain, pins
from release_inputs import ROOT, digest


def blob_sha(data):
    return hashlib.sha1(b'blob ' + str(len(data)).encode() + b'\0' + data).hexdigest()


def validate(record):
    fields = {'commit', 'version', 'crateVersion', 'crateSha256', 'dataSha256',
              'dataGitBlobSha1', 'noticeFile', 'noticeSha256', 'noticeGitBlobSha1',
              'treeFile', 'treeSha256', 'sourceUrl'}
    if not isinstance(record, dict) or set(record) != fields:
        raise ValueError('Complete ICU source/notice pins required')
    for name in ('commit', 'dataGitBlobSha1', 'noticeGitBlobSha1'):
        if not re.fullmatch('[0-9a-f]{40}', str(record[name])):
            raise ValueError('Exact ICU Git pins required')
    for name in ('crateSha256', 'dataSha256', 'noticeSha256', 'treeSha256'):
        if not re.fullmatch('[0-9a-f]{64}', str(record[name])):
            raise ValueError('Exact ICU content pins required')
    for name in ('noticeFile', 'treeFile'):
        if not re.fullmatch('[A-Za-z0-9][A-Za-z0-9_.-]+', str(record[name])):
            raise ValueError('Unsafe ICU evidence filename')
    if record['version'] != '77.1' or record['crateVersion'] != '0.77.0' or record['sourceUrl'] != 'https://chromium.googlesource.com/chromium/deps/icu/+/' + record['commit'] + '/LICENSE':
        raise ValueError('Exact original ICU notice origin required')
    return record


def local_evidence(record, root=ROOT):
    validate(record)
    folder = Path(root) / 'packaging/source-metadata'
    for key, checksum in (('noticeFile', 'noticeSha256'), ('treeFile', 'treeSha256')):
        path = folder / record[key]
        if path.is_symlink() or not path.is_file() or path.stat().st_size > 1024 * 1024 or digest(path) != record[checksum]:
            raise ValueError('Changed/missing original ICU evidence')
    notice = (folder / record['noticeFile']).read_bytes()
    raw = (folder / record['treeFile']).read_bytes()
    if blob_sha(notice) != record['noticeGitBlobSha1'] or not raw.startswith(b")]}'"):
        raise ValueError('ICU original notice/tree identity mismatch')
    tree = json.loads(raw[4:])
    matches = [row for row in tree.get('entries', []) if row.get('name') == 'icudtl.dat']
    if len(matches) != 1 or matches[0].get('type') != 'blob' or matches[0].get('mode') != 33188 or matches[0].get('id') != record['dataGitBlobSha1']:
        raise ValueError('ICU data Git-tree identity mismatch')
    return notice


def notice_origin(record):
    validate(record)
    return {'sourceEntry': 'LICENSE',
            'sourceFile': 'packaging/source-metadata/' + record['noticeFile'],
            'sourceUrl': record['sourceUrl'], 'sha256': record['noticeSha256'],
            'scope': 'Original ICU terms including third-party data notices; exact pinned V8/crate data bytes matched'}


def verify_data(record, data, deps):
    validate(record)
    match = re.search(rb"'third_party/icu'\s*:\s*Var\('chromium_url'\)\s*\+\s*'/chromium/deps/icu.git'\s*\+\s*'@'\s*\+\s*'([0-9a-f]{40})'", deps)
    if not match or match[1].decode() != record['commit'] or hashlib.sha256(data).hexdigest() != record['dataSha256'] or blob_sha(data) != record['dataGitBlobSha1']:
        raise ValueError('ICU data/V8 dependency lineage mismatch')


def collect(record, cargo, cache, deps, online=False):
    notice = local_evidence(record)
    matches = [row for row in pins(cargo) if row['name'] == 'deno_core_icudata' and row['version'] == record['crateVersion']]
    if len(matches) != 1 or matches[0]['sha256'] != record['crateSha256']:
        raise ValueError('ICU crate differs from exact Deno Cargo lock')
    crate = obtain(matches[0], Path(cache) / 'cargo-registry-cache', online)
    name = 'deno_core_icudata-' + record['crateVersion'] + '/src/icudtl.dat'
    with tarfile.open(crate) as archive:
        entries = [entry for entry in archive if entry.name == name]
        if len(entries) != 1 or not entries[0].isfile() or not 0 < entries[0].size < 32 * 1024 * 1024:
            raise ValueError('Missing/linked/oversized ICU data member')
        data = archive.extractfile(entries[0]).read()
    verify_data(record, data, deps)
    return notice, crate, {'pins': record, 'dataLineageVerified': True,
                          'originalNoticeRestored': True,
                          'scope': 'Exact ICU data/notice lineage, not complete Deno/V8 binary closure or redistribution approval.'}
