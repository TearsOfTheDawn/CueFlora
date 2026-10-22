# CueFlora 0.2.2 candidate engineering

The initial request was a wider audit and preparation of 0.2.2, not publication. [Audit findings](CUEFLORA_022_AUDIT.md) describe confirmed defects and narrow repairs. The publisher subsequently authorised publication with "Ok, publish"; [the separate publication handoff](CUEFLORA_022_PUBLICATION.md) records the actual public 0.2.2 release. This document retains the engineering-preparation boundary, not an ongoing publication blocker.

## Candidate contents

Matching unsigned Windows x64 Setup, keyed unpacked Chrome extension, complete Windows ZIP, update manifest, clean source archive, original notices, dependency inventory and corresponding third-party sources. The development and GitHub release identities are unchanged. No provider/model defaults, service provisioning or subtitle-generation behavior is added.

`tool_process.py` is the common native subprocess contract. Production tools never inherit the native control input; user-confirmed Setup launches also detach output streams. `persistent_native.py` verifies two responses before closing input, rather than relying on a closed-input self-test. `run_native_tests.py` discovers the same host/setup suites in local, clean-source and CI checks.

## Verification

Run `packaging/verify_local.py --output <fresh-directory>`, then full pinned preparation. `prepare_windows.py` accepts a preserved hash-validated 9.0.2 audio build for copying/reverification, or rebuilds from the pinned public source/toolchain cache. No moving latest input is permitted. Clean-source exports must retain exact byte/source identities.

The 0.2.2 workflow is read-only and exact-branch/version bounded; it cannot publish, change Pages or install anything. Fresh preparation reports retain explicit pending external approvals. Unit/build success is not live-browser or semantic subtitle acceptance.

## Eventual upgrade

Finish Runs, run the matching Setup and confirm Upgrade, then Reload CueFlora at `chrome://extensions` and reload YouTube tabs. Keep the current extension identity; do not remove/reinstall or reset keys/models. Manual Setup is the safe fallback for older launchers. This document does not claim that an unpublished candidate URL exists.

A final artifact handoff records actual paths, hashes and results after preparation. Separate authorisation and exact candidate-bound review were required and are now recorded by the publication handoff; preparing a candidate never authorises its publication by itself.
