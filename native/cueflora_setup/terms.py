"""Installation acknowledgement; original component licences remain authoritative."""
TERMS = '''CueFlora third-party terms

CueFlora's application code is MIT-licensed, with the original Substrata attribution retained. Bundled software has its own terms; the application licence does not replace them. The runtime's licenses folder and the accompanying consolidated notices contain the original component terms.

This Windows package includes Microsoft Distributable Code through its upstream Python build. Keep Microsoft's copyright, trademark and patent notices intact; do not imply Microsoft endorsement; do not distribute that code for non-Microsoft platforms; and do not include it in malicious, deceptive or unlawful programs. Further distributors and external end users must agree to applicable terms protecting that Microsoft code. These conditions concern Microsoft Distributable Code only, not ownership of Python, CueFlora, or other third-party code. The original Windows Python additional conditions remain included, unchanged, in Python-LICENSE.txt.

FFmpeg uses LGPL version 2.1 or later; other tools include permissive, MPL and GPL-covered components. Their respective rights and conditions remain effective. CueFlora imposes no prohibition on reverse engineering or replacing LGPL libraries, and no restriction overriding any applicable open-source licence. No third-party endorsement or warranty is promised.

Matching sources and build instructions are supplied in CueFlora-third-party-sources.zip alongside this package; keep them available with binary redistribution. Original source archives, licence declarations and notices are retained. Authorship metadata and standard reference texts are not invented original copyright notices.

Install or repair only if you agree to the applicable third-party terms. Uninstall does not erase your settings or evidence. This acknowledgement is not a claim of Chrome Store approval or an absolute security guarantee.
'''


def confirmation(action):
    text=action.title()+' the CueFlora native runtime?\nBrowser/provider settings and evidence remain unchanged.'
    if action in ('install','repair'):
        text+='\n\nChoosing Yes confirms that you agree to the applicable third-party licence terms. Read them using Third-party terms in the main window. Original licences and source instructions are included.'
    return text


def requires_acceptance(action,apply):
    return apply is True and action in ('install','repair')
