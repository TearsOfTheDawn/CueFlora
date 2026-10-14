# Source and privacy/help publication

## Verified hosting status

On 2026-10-15, the publisher made `TearsOfTheDawn/CueFlora` public and enabled Pages from `codex/public-pages` at `/ (root)`. GitHub deployment run `38654562336` succeeded. Direct HTTPS checks of all four pages, CSS and the generation report returned 200 and matched the exact uploaded byte counts and SHA-256 hashes. Local evidence is preserved as `LIVE_HOSTING_VERIFICATION.json` under release-binding artifacts; earlier preparation reports remain historical. No browser automation was used. There are still no public installer or Store download links; no binary release or Store submission was authorized.

The publisher approved making CueFlora source and privacy/help pages public on 2026-10-15. This approval excludes installers, binary/source bundles for a runtime release, Chrome Store submission/publication and redistribution clearance. The Store item remains a draft and previous private previews remain unchanged.

## Site preparation

`packaging/public_materials.py --prelaunch` produces a buildless four-page kit: introduction, release status/intended installation, privacy and support. It uses verified publisher/Store values and GitHub Issues. All pages say the software is not released. The kit contains no scripts, tracking, forms, installer checksums or binary/Store download links. `.nojekyll` permits direct static serving. Normal candidate-page generation remains a separate mode that requires a matching installer report.

```text
python packaging/public_materials.py --output artifacts/public-source-pages/site-001 --configuration artifacts/release-binding/TearsOfTheDawn-CueFlora/public-identity.draft.json --prelaunch
```

The local draft holds the verified publisher-controlled prelaunch URLs. Live hosting is not proof of installer readiness. Builders must fill exact fresh runtime/source bindings; all public release/redistribution approvals remain false.

## Account settings

The connected GitHub interface supports source and branch writes but currently exposes neither repository-visibility nor Pages-configuration mutations. No authenticated GitHub CLI is available. The owner must therefore perform these two settings changes without giving passwords or tokens to an agent:

1. Repository Settings → General → Danger Zone → Change repository visibility → Public.
2. Repository Settings → Pages → Deploy from a branch → `codex/public-pages` → `/ (root)` → Save.

Only the static site files belong at the root of `codex/public-pages`. Main retains the audited source and build-only CI. Do not use the source repository root as the website or upload runtime artifacts. GitHub performs its own Pages deployment after the publishing source is configured.

Before changing visibility, be aware that existing Git author/committer email metadata and Actions history become public with the source. GitHub Issues avoids a public support email; it does not erase Git metadata. No history is rewritten or deleted by this task.

Expected addresses after successful hosting:

- `https://tearsofthedawn.github.io/CueFlora/`
- `https://tearsofthedawn.github.io/CueFlora/privacy.html`
- `https://tearsofthedawn.github.io/CueFlora/download.html` — pre-release status, not an installer download.
- `https://tearsofthedawn.github.io/CueFlora/support.html`
- `https://github.com/TearsOfTheDawn/CueFlora/issues`

An agent can then read repository/Actions state and the HTTPS pages without browser automation, check their exact content and record actual hosting evidence. Any missing deployment or HTTP failure remains incomplete, not a pass.

## Remaining software-release gates

Public source/help is not Store approval, binary redistribution permission or Windows/Chrome acceptance. Final Store-bound installer preparation, exact-byte licence/security/download-policy review, genuine product screenshots, actual acceptance or permitted explicit testing waivers, Store approval and final publication authorization remain separate. The first installer is unsigned; no signing or harmlessness guarantee is inferred from tests or hashes.
