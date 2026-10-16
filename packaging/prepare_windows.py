"""Windows/Chrome preparation only: no publication, live install, browser or AI."""
import argparse
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import time
from release_inputs import ROOT, obtain_inputs, verify_environment, source_inventory, digest, compare_outputs, inspect_ejs, explain_frozen_differences, explain_library_order
from bootstrap_offline import bootstrap
from collect_release_evidence import collect
from source_export import source_identity


BLOCKERS = ['Exact source-built FFmpeg/Opus sources supplied; dependency-specific licensing assessment required',
    'Exact yt-dlp bundled-dependency source closure needs redistribution review',
    'Deno/native DLL licence closure needs final review; interpreter payload matching is established',
    'Store eligibility of native audio downloads and JavaScript challenge execution unresolved',
    'DPAPI and store-only HTTPS implemented; independent security review and live acceptance still deferred',
    'Genuine screenshots and artifact-bound verification of supplied publisher/Store identity and public locations required',
    'Unsigned first release accepted; clean-Windows/real-Chrome acceptance absent; other platforms not certified']


def copy_extension_sources(root, workspace):
    """All source inputs used by config/plugins, without installed/private files."""
    workspace.mkdir()
    for directory in ['entrypoints','utils','public','scripts']:
        shutil.copytree(root/directory,workspace/directory)
    for name in ['package.json','package-lock.json','wxt.config.ts','tsconfig.json','vitest.config.ts','preview-identity.json','LICENSE.md']:
        shutil.copy2(root/name,workspace/name)
    # The bundle plugin reads original supplemental notice bytes at build time.
    # Copy the complete public notice directory, not an installed dependency patch.
    (workspace/'packaging').mkdir()
    shutil.copy2(root/'packaging/npm-notices.lock.json',workspace/'packaging/npm-notices.lock.json')
    shutil.copytree(root/'packaging/notices',workspace/'packaging/notices')


def prepare(output, cache, offline, evidence_cache=None, audio_build=None, audio_cache=None, toolchain=None, public_config=None, downloader_cache=None):
    if os.name != 'nt':
        raise ValueError('Windows x64 preparation only')
    output = output.resolve(); cache = cache.resolve()
    if output.exists():
        raise ValueError('Preparation output must be fresh')
    output.mkdir(parents=True)
    for name in ['build-user.npmrc','build-global.npmrc']:
        (output/name).write_text('update-notifier=false\naudit=false\nfund=false\nregistry=https://registry.npmjs.org/\n')
    os.environ['NPM_CONFIG_USERCONFIG'] = str(output/'build-user.npmrc')
    os.environ['NPM_CONFIG_GLOBALCONFIG'] = str(output/'build-global.npmrc')
    os.environ['npm_config_update_notifier'] = 'false'
    report = {'schema':1,'engineeringPassed':False,'publicReleaseReady':False,'redistributionApproved':False,
        'published':False,'liveInstallation':False,'browserAutomation':False,'inference':False,
        'offline':offline,'releaseBlockers':list(BLOCKERS),'checks':[]}
    report_file = output/'readiness.json'
    def persist(): report_file.write_text(json.dumps(report,indent=2)+'\n',encoding='utf-8')
    def run(name, command, cwd=ROOT, env=None):
        started = time.monotonic(); log = output/(name+'.log')
        with log.open('wb') as stream:
            try:
                result = subprocess.run([str(part) for part in command],cwd=cwd,env=env,stdout=stream,stderr=subprocess.STDOUT,timeout=1800)
                code = result.returncode
            except (OSError, subprocess.TimeoutExpired) as error:
                stream.write(str(error).encode()); code = -1
        report['checks'].append({'name':name,'exitCode':code,'seconds':round(time.monotonic()-started,2),'log':log.name})
        persist(); print(name+': '+('PASS' if code == 0 else 'FAIL'),flush=True)
        if code: raise RuntimeError(name+' failed; see '+str(log))
    persist()
    try:
        from node_inputs import restore as restore_node
        node_root,node_evidence=restore_node(cache,output/'offline-node',online=not offline)
        os.environ['PATH']=str(node_root)+os.pathsep+os.environ.get('PATH','')
        os.environ['CUEFLORA_NPM_MODULES']=str(node_root/'node_modules/npm')
        report['nodeInputs']=node_evidence
        if public_config:
            sys.path.insert(0,str(ROOT/'native'))
            from cueflora_setup.public_release import validate_identity
            validate_identity(json.loads(public_config.read_text()),require_binding=False)
        prior_hashes = {}
        for prior_report in (ROOT/'artifacts/distribution').rglob('artifact-report.json'):
            prior = json.loads(prior_report.read_text())
            if not all(key in prior for key in ('archive','sha256','setupSha256')): continue
            for path, expected in [(prior_report.parent/prior['archive'],prior['sha256']),
                (prior_report.parent/'CueFlora Setup/CueFlora Setup.exe',prior['setupSha256'])]:
                if digest(path) != expected: raise ValueError('Previous preview differs from its recorded inventory')
                prior_hashes[str(path)] = expected
        lock = json.loads((ROOT/'packaging/inputs-windows.lock.json').read_text())
        obtain_inputs(lock,cache,offline=offline,source_audio=True); verify_environment(lock)
        locked_files = {item['file']:item['sha256'] for item in lock['files']}
        for notice in (ROOT/'packaging/notices').glob('*'):
            if notice.name in locked_files and digest(notice) != locked_files[notice.name]:
                raise ValueError('Notice differs from pinned upstream input')
        if inspect_ejs(cache/'yt-dlp.exe') != lock['ejs']: raise ValueError('EJS input mismatch')
        inputs = source_inventory()
        (output/'source-files.json').write_text(json.dumps(inputs,indent=2)+'\n',encoding='utf-8')
        report['sourceInventorySha256'] = source_identity(inputs)
        report['sourceFilesReportSha256'] = digest(output/'source-files.json')
        report['inputLockSha256'] = digest(ROOT/'packaging/inputs-windows.lock.json')
        profiles = ['acceptance','store-candidate'] if public_config else ['preview','store-candidate']
        report['effectiveConfiguration'] = {'version':json.loads((ROOT/'package.json').read_text())['version'],
            'profiles':profiles,'platform':'Windows-x64','chromeDevelopmentId':json.loads((ROOT/'preview-identity.json').read_text())['chromeId'],
            'publicIdentity':json.loads(public_config.read_text())['extensionIds']['chrome'] if public_config else None,'nodeVersion':subprocess.check_output(['node','--version'],text=True).strip(),
            'nodeSha256':digest(Path(shutil.which('node'))),'npmVersion':subprocess.check_output(['cmd.exe','/d','/c','npm','--version'],text=True).strip()}
        run('npm-cache',['node','scripts/cache-npm.mjs',cache/'npm',*(['--offline'] if offline else [])])
        run('offline-python',[sys.executable,'packaging/bootstrap_offline.py','--cache',cache,'--output',output/'offline-python','--official'])
        python = output/'offline-python/venv/Scripts/python.exe'
        run('verification',[python,'packaging/verify_local.py','--output',output/'verification'])
        v8_notices=output/'v8-notice-evidence'
        run('v8-core-notices',[python,'packaging/collect_v8_notices.py','--inputs',cache,'--cache',evidence_cache,'--output',v8_notices,*(['--online'] if not offline else [])])
        interpreter_notices=output/'interpreter-component-notices'
        run('interpreter-component-notices',[python,'packaging/interpreter_component_notices.py','--inputs',cache,'--output',interpreter_notices])
        cargo_notices=output/'cargo-notice-evidence'
        run('cargo-source-notices',[python,'packaging/cargo_notice_evidence.py','--inputs',cache,'--cache',evidence_cache/'cargo-registry-cache','--output',cargo_notices,*(['--online'] if not offline else [])])
        repository_notices=output/'repository-notice-evidence'
        run('cargo-repository-notices',[python,'packaging/repository_notice_evidence.py','--inputs',cache,'--registry-cache',evidence_cache/'cargo-registry-cache','--repository-cache',evidence_cache/'cargo-repository-cache','--output',repository_notices,*(['--online'] if not offline else [])])
        downloader_cache=(downloader_cache or cache/'downloader').resolve()
        downloader_build=output/'downloader-build'
        run('downloader-build',[python,'packaging/build_downloader.py','--inputs',cache,'--cache',downloader_cache,'--output',downloader_build,*(['--online'] if not offline else [])])
        from build_downloader import validate_build
        report['downloaderBuild']=validate_build(downloader_build)
        run('curl-source-evidence',[python,'packaging/collect_curl_sources.py','--cache',evidence_cache,'--output',output/'curl-source-evidence','--downloader',downloader_build/'bin/yt-dlp.exe',*(['--online'] if not offline else [])])
        if audio_build:
            # Never write new reports into a preserved prior audio build/package.
            supplied = audio_build.resolve(); audio_build = output/'audio-build'
            audio_build.mkdir()
            shutil.copy2(supplied/'audio-build.json',audio_build/'audio-build.json')
            for name in ('notices','corresponding-source'):
                shutil.copytree(supplied/name,audio_build/name)
            shutil.copytree(supplied/'install/bin',audio_build/'install/bin')
        else:
            if audio_cache is None: raise ValueError('Provide --audio-cache for a complete public-source build')
            audio_cache = audio_cache.resolve()
            if toolchain is None:
                run('audio-toolchain',[python,'packaging/audio_build.py','--cache',audio_cache,'--output',output/'audio-toolchain','--bootstrap',*(['--online'] if not offline else [])])
                toolchain = output/'audio-toolchain/msys64'
            run('audio-build',[python,'packaging/audio_build.py','--cache',audio_cache,'--toolchain',toolchain.resolve(),'--output',output/'audio-build',*(['--online'] if not offline else [])])
            audio_build = output/'audio-build'
        run('audio-conformance',[python,'packaging/verify_audio_conformance.py','--candidate',audio_build,'--output',output/'audio-verification'])
        shutil.copy2(output/'audio-verification/audio-conformance.json',audio_build/'audio-conformance.json')
        report['audioBuild'] = {'manifestSha256':digest(audio_build/'audio-build.json'),
            'conformanceSha256':digest(audio_build/'audio-conformance.json'),
            'inputLockSha256':digest(ROOT/'packaging/audio-inputs.lock.json'),
            'toolchainLockSha256':digest(ROOT/'packaging/audio-toolchain.lock.json'),'privateBaselineRequired':False}
        workspace = output/'offline-extension-workspace'
        copy_extension_sources(ROOT,workspace)
        run('offline-npm-ci',['cmd.exe','/d','/c','npm','ci','--offline','--cache',cache/'npm','--no-audit','--no-fund','--update-notifier=false'],cwd=workspace)
        npm = ['cmd.exe','/d','/c','npm']
        for profile in profiles:
            environment = {**os.environ,'CUEFLORA_BUILD_PROFILE':profile}
            environment.pop('CUEFLORA_PUBLIC_CONFIG',None)
            if public_config: environment['CUEFLORA_PUBLIC_CONFIG'] = str(public_config.resolve())
            run('extension-'+profile,npm+['run','build:chrome'],cwd=workspace,env=environment)
            destination = output/('Chrome-'+profile)
            shutil.copytree(workspace/'.output/chrome-mv3',destination)
            manifest = json.loads((destination/'manifest.json').read_text())
            if (profile != 'store-candidate') != ('key' in manifest): raise ValueError('Profile identity mismatch')
        # The same restored offline environment builds both fresh pairs.
        environment = dict(os.environ)
        for name, file in lock['tools'].items():
            environment[{'yt-dlp':'YT_DLP_PATH','ffmpeg':'FFMPEG_PATH','ffprobe':'FFPROBE_PATH','deno':'DENO_PATH'}[name]] = str(cache/file)
        for name in ('ffmpeg','ffprobe'):
            environment[{'ffmpeg':'FFMPEG_PATH','ffprobe':'FFPROBE_PATH'}[name]] = str(audio_build/'install/bin'/(name+'.exe'))
        environment['YT_DLP_PATH']=str(downloader_build/'bin/yt-dlp.exe')
        tool_lock = output/'tool-lock.json'
        tool_lock.write_text(json.dumps({'tools':[{'name':name,'sha256':digest(Path(environment[{'yt-dlp':'YT_DLP_PATH','ffmpeg':'FFMPEG_PATH','ffprobe':'FFPROBE_PATH','deno':'DENO_PATH'}[name]]))} for name in lock['tools']]},indent=2)+'\n')
        for iteration in [1,2]:
            runtime_output = output/f'runtime-{iteration}'
            binding = ['--public-config',public_config.resolve()] if public_config else []
            run(f'runtime-{iteration}',[python,'packaging/build_runtime.py','--output',runtime_output,'--tool-lock',tool_lock,'--audio-build',audio_build,'--downloader-build',downloader_build,'--v8-notices',v8_notices,'--interpreter-notices',interpreter_notices,'--cargo-notices',cargo_notices,'--repository-notices',repository_notices,*binding],env=environment)
            runtime = runtime_output/'dist/cueflora-host'
            run(f'setup-{iteration}',[python,'packaging/build_preview.py','--runtime',runtime,'--output',output/f'setup-{iteration}',*binding],env=environment)
        runtime = output/'runtime-1/dist/cueflora-host'
        setup = output/'setup-1/dist/CueFlora Setup.exe'
        comparison = {'runtime':compare_outputs(runtime,output/'runtime-2/dist/cueflora-host'),
            'setup':compare_outputs(output/'setup-1/dist',output/'setup-2/dist'),
            'hostExplanation':explain_frozen_differences(runtime/'cueflora-host.exe',output/'runtime-2/dist/cueflora-host/cueflora-host.exe'),
            'setupExplanation':explain_frozen_differences(setup,output/'setup-2/dist/CueFlora Setup.exe'),
            'libraryExplanation':explain_library_order(runtime/'_internal/base_library.zip',output/'runtime-2/dist/cueflora-host/_internal/base_library.zip'),
            'sourceAndInputHashesWereFixed':True}
        from verify_two_builds import verify as verify_two_builds
        comparison['strictValidation'] = verify_two_builds(runtime,output/'runtime-2/dist/cueflora-host',setup,output/'setup-2/dist/CueFlora Setup.exe')
        (output/'build-comparison.json').write_text(json.dumps(comparison,indent=2)+'\n')
        report['buildComparison'] = comparison
        source_evidence=collect(cache,output/'licence-evidence',lock,evidence_cache,source_audio=True,downloader_build=downloader_build)
        shutil.copytree(output/'curl-source-evidence',output/'licence-evidence/downloader-native/curl')
        source_evidence['curlSourceEvidence']=json.loads((output/'curl-source-evidence/curl-source-evidence.json').read_text())
        shutil.copytree(v8_notices,output/'licence-evidence/deno-v8')
        source_evidence['v8NoticeEvidence']=json.loads((v8_notices/'v8-notice-evidence.json').read_text())
        shutil.copytree(interpreter_notices,output/'licence-evidence/interpreter-components')
        source_evidence['interpreterComponentEvidence']=json.loads((interpreter_notices/'interpreter-component-notices.json').read_text())
        shutil.copytree(cargo_notices,output/'licence-evidence/cargo-superset')
        source_evidence['cargoNoticeEvidence']=json.loads((cargo_notices/'cargo-notice-inventory.json').read_text())
        shutil.copytree(repository_notices,output/'licence-evidence/repository-notices')
        source_evidence['repositoryNoticeEvidence']=json.loads((repository_notices/'repository-notice-inventory.json').read_text())
        run('tool-dependency-audit',[python,'packaging/audit_bundled_tools.py','--cache',cache,'--output',output/'tool-dependency-audit','--downloader-build',downloader_build])
        report['evidenceLockSha256']=digest(ROOT/'packaging/evidence-windows.lock.json')
        from dependency_ledger import write as write_ledger
        write_ledger(runtime,output/('Chrome-acceptance' if public_config else 'Chrome-preview'),source_evidence,source_evidence['supplemental'],output/'release-ledger',output/'licence-evidence/supplemental/source-notices',
            setup,output/'setup-1/work/CueFlora Setup/Analysis-00.toc')
        run('capabilities',[python,'packaging/verify_capabilities.py','--runtime',runtime,'--output',output/'capability-verification'])
        run('credentials',[python,'packaging/verify_credentials.py','--runtime',runtime,'--output',output/'credential-verification'])
        run('installer',[python,'packaging/verify_installer.py','--setup',setup,'--runtime',runtime,'--output',output/'installer-verification'])
        run('lifecycle',[python,'packaging/smoke_setup.py','--payload',runtime,'--release',output/'setup-1/bundle/release.json','--launcher',setup,'--output',output/'lifecycle'])
        isolated = {**os.environ,'GIT_CONFIG_COUNT':'2','GIT_CONFIG_KEY_0':'safe.directory','GIT_CONFIG_VALUE_0':'C:/AI/substrata',
            'GIT_CONFIG_KEY_1':'safe.directory','GIT_CONFIG_VALUE_1':'C:/AI/CueFlora','GIT_OPTIONAL_LOCKS':'0'}
        if (ROOT/'artifacts/source-baseline.json').is_file():
            run('original-preservation',[python,'packaging/verify_isolation.py','--report',output/'isolation.json'],env=isolated)
        else:
            report['originalPreservation'] = {'status':'not-applicable','reason':'Independent source checkout contains no private source-copy baseline; no original project is accessed.'}
        run('assembly',[python,'packaging/assemble_preview.py','--setup',setup,'--runtime',runtime,'--extension',output/('Chrome-acceptance' if public_config else 'Chrome-preview'),
            '--store-extension',output/'Chrome-store-candidate','--release-ledger',output/'release-ledger','--output',output/'delivery'])
        archive = output/('delivery/CueFlora-Windows-x64-Chrome-public-candidate.zip' if public_config else 'delivery/CueFlora-Windows-x64-Chrome-preview.zip')
        run('independent-archive',[python,'packaging/verify_archive.py',archive])
        run('source-export',[python,'packaging/source_export.py','--output',output/'source-export'])
        run('source-bundle',[python,'packaging/bundle_sources.py','--audio',runtime/'corresponding-source/audio',
            '--evidence',output/'licence-evidence','--output',output/'source-bundle'])
        report['sourceArchive'] = json.loads((output/'source-export/source-audit.json').read_text())
        run('clean-source',[python,'packaging/verify_source_checkout.py','--cache',cache/'npm','--output',output/'clean-source-verification'])
        report['cleanSourceVerification'] = json.loads((output/'clean-source-verification/clean-source-verification.json').read_text())
        if report['cleanSourceVerification'].get('passed') is not True or report['cleanSourceVerification'].get('sourceArchiveSha256') != report['sourceArchive']['archiveSha256']:
            raise ValueError('Clean-source verification does not match this candidate source archive')
        if inputs != source_inventory(): raise ValueError('Source changed during preparation; rebuild from a stable source snapshot')
        if any(digest(Path(path)) != expected for path,expected in prior_hashes.items()):
            raise ValueError('Previous preview changed during preparation')
        report['previousPreviewPreserved'] = bool(prior_hashes)
        report['engineeringPassed'] = True
        report['artifacts'] = json.loads((output/'delivery/artifact-report.json').read_text())
        report['artifactBindings'] = {'sourceInventorySha256':report['sourceInventorySha256'],
            'runtimeInventorySha256':digest(runtime/'runtime-manifest.json'),
            'setupSha256':digest(setup),'extensionSha256':digest(output/'delivery/CueFlora Setup/CueFlora-Chrome-store-upload.zip')}
        from approval_evidence import pending
        (output/'external-approvals.json').write_text(json.dumps(pending(report['artifactBindings']),indent=2)+'\n',encoding='utf-8')
        from redistribution_assessment import template as redistribution_template
        final_ledger=json.loads((output/'release-ledger/dependency-ledger.json').read_text())
        (output/'licence-assessment.template.json').write_text(json.dumps(redistribution_template(final_ledger,report['artifactBindings']),indent=2)+'\n',encoding='utf-8')
        from release_readiness import assess
        configuration = json.loads((output/'setup-1/bundle/release.json').read_text()) if public_config else None
        gates = assess(report,report['sourceArchive'],json.loads((output/'release-ledger/dependency-ledger.json').read_text()),configuration)
        (output/'release-gates.json').write_text(json.dumps(gates,indent=2)+'\n',encoding='utf-8')
        from public_materials import build as public_materials
        public_materials(output/'public-pages',configuration,report['artifacts'])
        report['offlineCache'] = {'directory':str(cache),'inputs':len(lock['files']),'pythonWheels':len(lock['pythonWheels']),
            'npm':json.loads((cache/'npm/cueflora-npm-inputs.json').read_text())}
        persist()
        from release_assets import assemble as release_assets
        release_assets(output,output/'release-assets')
        print('Preparation passed. PUBLIC RELEASE REMAINS BLOCKED.',flush=True)
        return 0
    except Exception as error:
        report['failure'] = str(error); persist(); print(str(error),file=sys.stderr,flush=True)
        return 1


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output',required=True,type=Path)
    parser.add_argument('--cache',default=ROOT/'artifacts/input-cache-v1',type=Path)
    parser.add_argument('--evidence-cache',default=ROOT/'artifacts/redistribution-evidence-v2',type=Path)
    parser.add_argument('--online',action='store_true',help='Fetch missing URL-bound inputs; never latest or substitute mismatched inputs')
    parser.add_argument('--audio-build',type=Path,help='Preserved 9.0.2 build to copy and reverify; never modified')
    parser.add_argument('--audio-cache',type=Path,help='Pinned source/compiler cache for a complete build without private binaries')
    parser.add_argument('--toolchain',type=Path,help='Optional already-restored hash-audited compiler; otherwise restored into output')
    parser.add_argument('--public-config',type=Path,help='Schema 2 real public identity/URLs, not approval or publication permission')
    parser.add_argument('--downloader-cache',type=Path,help='Exact upstream Python dependency wheels/sources; default <cache>/downloader')
    args = parser.parse_args()
    raise SystemExit(prepare(args.output,args.cache,not args.online,args.evidence_cache,args.audio_build,args.audio_cache,args.toolchain,args.public_config,args.downloader_cache))
