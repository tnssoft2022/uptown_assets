/** One finished video under listings/<listing>/output/. */
export type Video = {
  /** The listing folder, e.g. "A01-condo-asoke". */
  listing: string
  /** The file name, e.g. "final.mp4". */
  name: string
  /** Path relative to the project root. */
  path: string
  sizeBytes: number
  mtimeMs: number
  /** Length in seconds from ffprobe; null when it could not be read. */
  seconds: number | null
}

declare module 'claude-code' {
  interface PluginState {
    'video-list': { videos: Shaped<Video[]> }
  }
}
