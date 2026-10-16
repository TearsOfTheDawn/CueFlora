import type { Browser } from 'wxt/browser';

// Complete synthetic tab for the browser-typed test event API; no real browser.
export const messageTab: Browser.tabs.Tab = {
    id: 1, index: 0, windowId: 1, groupId: -1,
    pinned: false, highlighted: false, active: true, frozen: false,
    incognito: false, selected: true, discarded: false, autoDiscardable: true,
};
