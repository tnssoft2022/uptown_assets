/** One finished video under listings/<listing>/output/. */
export type Video = {
  /** The listing folder, e.g. "A01-condo-asoke". */
  listing: string
  /** The property name from the first "# " line of listing.md; the folder name without one. */
  title: string
  /** ประเภททรัพย์ from listing.md (คอนโด, บ้านเดี่ยว …); "" when it isn't there. */
  kind: string
  /** ประเภทประกาศ from listing.md (ขาย or เช่า); "" when it isn't there. */
  deal: string
  /** The file name, e.g. "final.mp4". */
  name: string
  /** Path relative to the project root. */
  path: string
  sizeBytes: number
  mtimeMs: number
  /** Length in seconds from ffprobe; null when it could not be read. */
  seconds: number | null
}

/** One row of a listing's output/progress.md table. */
export type Step = {
  /** The # column, e.g. "3". */
  number: string
  /** ขั้นตอน, e.g. "เขียนบรีฟ". */
  name: string
  /** สถานะ as written, e.g. "✅ เสร็จ" or "⏳ กำลังทำ". */
  status: string
  /** ใช้เวลา, e.g. "1 นาที 24 วิ"; "" while it isn't filled. */
  time: string
}

/** The progress table of this session's listing. */
export type Progress = {
  /** The listing folder, e.g. "1069-condo-asoke". */
  listing: string
  /** The property name from listing.md; the folder name without one. */
  title: string
  steps: Step[]
  mtimeMs: number
}

declare module 'claude-code' {
  interface PluginState {
    'video-list': {
      videos: Shaped<Video[]>
      progress: Shaped<Progress | null>
      /** The listing folder whose progress.md this session wrote or read. */
      listing: Shaped<string | null>
    }
  }
}
