"""Buildless GitHub Pages kit from real publisher values; no hosting or browser."""
import argparse
import html
import json
from pathlib import Path
import re
import shutil
import sys
from urllib.parse import urlsplit
from release_inputs import ROOT, digest

sys.path.insert(0,str(ROOT/'native'))
from cueflora_setup.public_release import validate_identity


def markdown(text):
    def inline(value):
        escaped=html.escape(value)
        return re.sub(r'\[([^\]]+)\]\((https://[^\s)]+|(?:index|download|privacy|support)\.html)\)',lambda match:'<a href="'+match[2]+'" rel="noopener noreferrer">'+match[1]+'</a>',escaped)
    blocks=[]
    for paragraph in text.strip().split('\n\n'):
        lines=paragraph.splitlines()
        if len(lines)==1 and lines[0].startswith('#'):
            level=min(3,len(lines[0])-len(lines[0].lstrip('#')))
            blocks.append('<h'+str(level)+'>'+inline(lines[0].lstrip('# '))+'</h'+str(level)+'>')
        elif all(line.startswith('- ') for line in lines):
            blocks.append('<ul>'+''.join('<li>'+inline(line[2:])+'</li>' for line in lines)+'</ul>')
        else: blocks.append('<p>'+inline(' '.join(lines))+'</p>')
    return '\n'.join(blocks)


def build(output, configuration=None, artifact_report=None, version=None):
    if output.exists(): raise ValueError('Fresh public-materials directory required')
    output.mkdir(parents=True)
    if configuration is None:
        shutil.copytree(ROOT/'docs/public',output/'page-sources')
        shutil.copy2(ROOT/'packaging/public-identity.template.json',output/'public-identity.template.json')
        report={'schema':1,'rendered':False,'published':False,'reason':'Actual publisher/repository/contact/Store identity required before render/hosting',
            'pageSources':{path.name:digest(path) for path in (output/'page-sources').iterdir() if path.is_file()}}
    else:
        validate_identity(configuration,require_binding=False)
        repository=configuration.get('repositoryUrl')
        if not isinstance(repository,str) or not re.fullmatch(r'https://github\.com/[A-Za-z0-9_-]+/[A-Za-z0-9_.-]+',repository) or repository.endswith(('.git','/..','/.')):
            raise ValueError('Real GitHub repository URL required')
        if not isinstance(artifact_report,dict) or not re.fullmatch('[0-9a-f]{64}',str(artifact_report.get('setupSha256',''))):
            raise ValueError('Verified installer hash required for download page')
        version=version or json.loads((ROOT/'package.json').read_text())['version']
        if not re.fullmatch(r'\d+\.\d+\.\d+',version): raise ValueError('Exact release version required')
        assets=repository+'/releases/download/v'+version+'/'
        links={'Store': 'https://chromewebstore.google.com/detail/'+configuration['extensionIds']['chrome'],
            'Setup':assets+'CueFlora-'+version+'-Setup.exe','Sources':assets+'CueFlora-third-party-sources.zip','Code':repository,'Support':configuration['supportUrl']}
        download='''# Install CueFlora

Windows x64 and Google Chrome. This is an unsigned review candidate until the publisher announces its approved release. AI services are not included.

- Install the Chrome extension from its Store listing when available.
- Download CueFlora Setup.exe. Run it, select Chrome, and choose Install.
- Open CueFlora settings and check the helper connection.
- Connect your existing transcription and translation services: API base address, model name and optional API key. Select each independently. A website login or ChatGPT subscription is not necessarily API access.
- Choose languages. On YouTube, open the flower button and press Run.

No Python, administrator access or PATH editing is needed. Caption-only use can skip the helper and AI connections when the video provides suitable captions.

The first installer is unsigned. Windows or security software may warn. Do not disable protection; stop if the file, publisher or checksum does not match. A checksum or build attestation is not a guarantee of safety.

Repair/upgrade: rerun the matching Setup or open CueFlora Setup from the Start Menu. Preview registrations are not silently taken over. To move from preview to Store identity, remove the preview helper first; do not modify Substrata. Uninstall removes owned registration and quarantines runtime files while preserving settings and evidence. Remove the extension/clear its data separately to remove saved configuration.

CueFlora uses FFmpeg libraries under LGPL 2.1-or-later and Opus under its BSD licence. Exact corresponding sources, notices and build instructions accompany the downloads. CueFlora's MIT licence does not relicense these components.
'''
        download+='\nVersion: '+version+'. Chrome ID: '+configuration['extensionIds']['chrome']+'.\n\nInstaller SHA-256: '+artifact_report['setupSha256']+'.\n\n'
        download+='\n'.join('- ['+name+']('+url+')' for name,url in links.items())
        pages={'index':('# CueFlora\n\nAI Subtitles & Translation for YouTube. Use your own compatible AI services, or available YouTube captions.\n\n'+
            'Install the extension, install its on-demand helper, connect your services, choose languages, then press Run. No AI runs automatically on navigation.\n\n'+
            '[Install and download](download.html)\n\nTranslation and recognition depend on your selected services; output can contain errors. Windows x64 / Chrome is the supported release.\n\n'+
            'Based on Substrata by jmviz under MIT; bundled dependencies retain their own licences.'),
            'download':download,'privacy':(ROOT/'docs/public/privacy.md').read_text(),
            'support':(ROOT/'docs/public/support.md').read_text()}
        navigation='<nav>'+''.join('<a href="'+name+'.html">'+name.title()+'</a> ' for name in pages)+'</nav>'
        for name,content in pages.items():
            page='<!doctype html><html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1"><title>CueFlora — '+name.title()+'</title><link rel="stylesheet" href="style.css"></head><body><main>'
            page+=navigation+markdown(content)+'<footer>Publisher: '+html.escape(configuration['owner'])+'. <a href="'+html.escape(configuration['supportUrl'],quote=True)+'">Contact/support</a>. Privacy policy revision 2026-10-13. No publisher analytics on these static pages.</footer></main></body></html>'
            (output/(name+'.html')).write_text(page,encoding='utf-8')
        (output/'style.css').write_text('body{margin:0;background:#faf8fd;color:#24202e;font:18px/1.6 system-ui,sans-serif}main{max-width:850px;margin:auto;padding:32px 24px}nav{display:flex;flex-wrap:wrap;gap:20px;border-bottom:1px solid #ddd;padding-bottom:16px}a{color:#5d36a8}a:focus-visible{outline:3px solid #e6b337;outline-offset:3px}footer{border-top:1px solid #ddd;margin-top:40px;padding-top:20px;font-size:14px}p,li{overflow-wrap:anywhere}h1{font-size:36px;line-height:1.2}',encoding='utf-8')
        report={'schema':1,'rendered':True,'published':False,'repositoryUrl':repository,'version':version,
            'storeIdentity':configuration['extensionIds']['chrome'],'installerSha256':artifact_report['setupSha256'],
            'files':{path.name:digest(path) for path in output.iterdir() if path.is_file()},'visualAcceptance':False,
            'releaseStatus':'review-candidate; promotion requires external decisions'}
    (output/'public-materials.json').write_text(json.dumps(report,indent=2)+'\n',encoding='utf-8')
    return report


if __name__ == '__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output',type=Path,required=True)
    parser.add_argument('--configuration',type=Path)
    parser.add_argument('--artifacts',type=Path)
    args=parser.parse_args()
    build(args.output.resolve(),json.loads(args.configuration.read_text()) if args.configuration else None,
        json.loads(args.artifacts.read_text()) if args.artifacts else None)
