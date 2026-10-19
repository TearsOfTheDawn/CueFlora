"""Truthful GitHub download/help pages; rendering never asserts hosting."""
import html
import json
from pathlib import Path
import re
import sys
from release_inputs import ROOT, digest

sys.path.insert(0,str(ROOT/'native'))
from cueflora_setup.public_release import validate_identity


def build(output, configuration, artifacts=None, version=None, prelaunch=False):
    from public_materials import markdown, privacy_revision
    validate_identity(configuration,require_binding=False)
    if configuration.get('distribution') != 'github' or not isinstance(prelaunch,bool):
        raise ValueError('Explicit GitHub channel and boolean preparation mode required')
    if prelaunch and artifacts is not None: raise ValueError('Prelaunch pages cannot offer candidate downloads')
    if not prelaunch and (not isinstance(artifacts,dict) or not re.fullmatch('[0-9a-f]{64}',str(artifacts.get('setupSha256',''))) or not re.fullmatch('[0-9a-f]{64}',str(artifacts.get('sha256','')))):
        raise ValueError('Exact installer and full-package hashes required')
    output=Path(output).resolve()
    if output.exists(): raise ValueError('Fresh public-materials directory required')
    version=version or json.loads((ROOT/'package.json').read_text())['version']
    if not re.fullmatch(r'\d+\.\d+\.\d+',version): raise ValueError('Exact release version required')
    repository=configuration['repositoryUrl']; assets=repository+'/releases/download/v'+version+'/'
    output.mkdir(parents=True)
    paired=bool(configuration.get('extensionInventorySha256'))
    package_name='CueFlora-'+version+('-Setup.exe' if paired else '-Windows-x64.zip')
    primary='[Download CueFlora for Windows — includes everything you need]('+assets+package_name+')'
    download='''# Install CueFlora

Windows x64 / Google Chrome.

'''+primary+'''

This is the only download you need: the complete Windows ZIP contains both the Chrome extension and Setup. Ignore the separate installer, extension ZIP and source-code files unless you specifically need them. Your AI services and models are separate.

## Install in five steps

1. Download the complete Windows ZIP above and extract it to a permanent folder.
2. Open chrome://extensions, enable Developer mode, choose Load unpacked and select CueFlora Setup/Chrome-extension inside the extracted package. Keep this folder.
3. In the extracted CueFlora Setup folder, run CueFlora Setup.exe, select Chrome, read Third-party terms and confirm Install.
4. Open CueFlora settings, check the helper connection, connect your existing AI services, Save and choose languages.
5. On YouTube, select the flower button and press Run. Available captions can be used without AI configuration.

No administrator access, separate Python installation or PATH changes are required. The helper runs on demand. CueFlora does not install models or start services. Transcription needs a compatible /audio/transcriptions API; translation needs /chat/completions with structured JSON Schema output. Supply an API address, optional key and model for each. A ChatGPT or other website login is not necessarily API access.

The installer is unsigned. Do not disable antivirus or automatically bypass a warning. Checksums show file identity, not guaranteed safety. Hosted AI may cost money and generated subtitles may be inaccurate. Process only content you are entitled to use and comply with applicable terms and law.

## Updates and removal

For extension updates, keep the same folder and Chrome ID, replace its files and click Reload at chrome://extensions; then reload YouTube tabs. Do not remove the extension just to update it. Run the matching new Setup for helper upgrades. Setup from the Start Menu offers Repair, Roll back and recoverable Uninstall. Uninstall preserves settings/evidence and quarantines runtime files; remove the browser extension separately if desired. Never change Substrata to install or remove CueFlora.
'''
    if paired:
        from installation_guide import paired_guide
        download=primary+'\n\n'+paired_guide(configuration['extensionIds']['chrome'],version)
    if prelaunch:
        download='# CueFlora release preparation\n\nNo public installer is offered by these preparation pages. Source, privacy and support are available. The intended route is a keyed unpacked Chrome extension and matching Windows helper from GitHub.\n\n[Source code]('+repository+')'
    else:
        download+='\n\n## For developers and verification — optional\n\nYou do not need these separate files for normal installation. Original notices and corresponding third-party sources remain available here.\n\n'
        download+='Version: '+version+'. Chrome ID: '+configuration['extensionIds']['chrome']+'.\n\n'
        download+='Windows package SHA-256: '+artifacts['sha256']+'.\n\nInstaller SHA-256: '+artifacts['setupSha256']+'.\n\n'
        download+='\n'.join('- ['+label+']('+assets+name+')' for label,name in (
            ('Complete Windows ZIP — optional alternative','CueFlora-'+version+'-Windows-x64.zip') if paired else
            ('Helper installer only — already included above','CueFlora-'+version+'-Setup.exe'),
            ('Unpacked extension ZIP — already included above','CueFlora-Chrome-extension.zip'),
            ('Application source','CueFlora-source.zip'),('Third-party sources','CueFlora-third-party-sources.zip'),
            ('Original notices','CueFlora-notices.zip'),('Consolidated notices','CueFlora-CONSOLIDATED-NOTICES.txt'),
            ('Dependency ledger','CueFlora-dependency-ledger.json'),('Checksums','SHA256SUMS.txt')))
    privacy=(ROOT/'docs/public/privacy.md').read_text()
    revision=privacy_revision(privacy)
    pages={
        'index':'# CueFlora\n\nAI Subtitles & Translation for YouTube. Use available captions or your own compatible transcription and translation services. AI work starts only when you press Run.\n\nWindows x64 / Chrome, distributed through GitHub.\n\n[Install and download](download.html)\n\n[Read the source]('+repository+')\n\nBased on Substrata by jmviz under MIT; bundled components retain their original licences.',
        'download':download,'privacy':privacy,
        'support':'# CueFlora support\n\n[Report a problem on GitHub Issues]('+configuration['supportUrl']+')\n\nInclude app, Windows and Chrome versions, the failing step and redacted reason codes. Never post API keys, encrypted credential records, signed media URLs or private captures.\n\nUse the keyed extension and Setup from the same release. The helper check verifies connection/tool availability; model discovery checks metadata, not generation compatibility. Local services must already be running.\n\n[Installation, updates and removal](download.html)\n\nRemembered keys use your Windows account protection, not protection against malware running as you. Recognition and translation can be wrong.'}
    if not prelaunch:
        pages['index']=pages['index'].replace('[Install and download](download.html)',primary+'\n\nOne ZIP includes the Chrome extension and Setup.\n\n[Follow the five installation steps](download.html)')
        if paired:pages['index']=pages['index'].replace('One ZIP includes the Chrome extension and Setup.','One Setup installer includes the matching extension, helper, audio tools and notices. Initial Chrome Load unpacked remains a one-time manual step.')
    labels={'index':'Home','download':'Download','privacy':'Privacy','support':'Help'}
    nav='<nav>'+''.join('<a href="'+name+'.html">'+label+'</a> ' for name,label in labels.items())+'</nav>'
    for name,content in pages.items():
        notice='<p role="status">Preparation only: no installer is published by this page.</p>' if prelaunch else ''
        rendered=markdown(content)
        if name in ('index','download') and not prelaunch:
            target='href="'+html.escape(assets+package_name,quote=True)+'"'
            rendered=rendered.replace('<a '+target,'<a class="primary-download" '+target,1)
        page='<!doctype html><html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1"><title>CueFlora — '+labels[name]+'</title><link rel="stylesheet" href="style.css"></head><body><main>'+nav+notice+rendered+'<footer>Publisher: '+html.escape(configuration['owner'])+'. <a href="'+html.escape(configuration['supportUrl'],quote=True)+'">Support</a>. Privacy policy revision '+revision+'. No publisher analytics on these static pages.</footer></main></body></html>'
        (output/(name+'.html')).write_text(page,encoding='utf-8')
    (output/'style.css').write_text('body{margin:0;background:#faf8fd;color:#24202e;font:18px/1.6 system-ui,sans-serif}main{max-width:850px;margin:auto;padding:32px 24px}nav{display:flex;flex-wrap:wrap;gap:20px;border-bottom:1px solid #ddd;padding-bottom:16px}a{color:#5d36a8}a:focus-visible{outline:3px solid #e6b337;outline-offset:3px}footer{border-top:1px solid #ddd;margin-top:40px;padding-top:20px;font-size:14px}p,li{overflow-wrap:anywhere}',encoding='utf-8')
    with (output/'style.css').open('a',encoding='utf-8') as style:
        style.write('.primary-download{display:inline-block;background:#5d36a8;color:#fff;padding:14px 20px;border-radius:8px;font-weight:700;text-decoration:none}.primary-download:hover{background:#47277f}ol{padding-left:28px}ol li{margin:16px 0}')
    (output/'.nojekyll').write_text('',encoding='utf-8')
    report={'schema':1,'rendered':True,'published':False,'distribution':'github','version':version,
        'repositoryUrl':repository,'extensionId':configuration['extensionIds']['chrome'],
        'installerSha256':None if prelaunch else artifacts['setupSha256'],
        'files':{path.name:digest(path) for path in output.iterdir() if path.is_file()},
        'visualAcceptance':False,'releaseStatus':'prelaunch-source-and-help-only' if prelaunch else 'candidate pages; verify actual assets before deployment'}
    (output/'public-materials.json').write_text(json.dumps(report,indent=2)+'\n',encoding='utf-8')
    return report
