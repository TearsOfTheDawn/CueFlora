/** Page scripts share the DOM but cannot create browser-trusted input events. */
export const trustedRun = (handler: () => void | Promise<void>) => async (event: Pick<Event, 'isTrusted'>): Promise<void> => {
    if (!event.isTrusted) return;
    await handler();
};
