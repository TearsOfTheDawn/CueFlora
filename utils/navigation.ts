import { getVideoId } from './log';

let generation = 0;
/** Invalidate even when navigation returns to the same video ID. */
export function invalidateNavigation(): void { generation++; }
export function navigationGuard(): () => boolean {
    const expected = generation;
    const videoId = getVideoId();
    return () => generation === expected && getVideoId() === videoId;
}
