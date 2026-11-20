import { atom, read, update } from 'claude-code'
import type { EngineInterface, McpToolResult, Register } from 'claude-code'

import type { Video } from '../types'

const PAGE = 'videos.html'
const TITLE = 'วีดีโอทั้งหมด'
const ROOT = 'listings'
const EXTENSIONS = ['.mp4', '.mov', '.m4v']

// Change the tag when Video's fields change: it declines what an earlier
// version stored, which outlives a reload.
const videos = atom({ plugin: 'video-list', key: 'videos' } as const, [], {
  shape: 'videos-2',
})

const isVideo = (name: string) =>
  EXTENSIONS.some(ext => name.toLowerCase().endsWith(ext))

const pad = (n: number) => String(n).padStart(2, '0')

export const formatDate = (ms: number) => {
  const d = new Date(ms)
  return `${pad(d.getDate())}/${pad(d.getMonth() + 1)}/${d.getFullYear()} ${pad(d.getHours())}:${pad(d.getMinutes())}`
}

export const formatLength = (seconds: number | null) => {
  if (seconds === null) return '-'
  const s = Math.round(seconds)
  return `${Math.floor(s / 60)}:${pad(s % 60)}`
}

export const formatSize = (bytes: number) =>
  `${(bytes / (1024 * 1024)).toFixed(1)} MB`

/** Groups videos by listing, newest listing first, newest video first. */
export const groupByListing = (list: readonly Video[]) => {
  const groups = new Map<string, Video[]>()
  for (const video of [...list].sort((a, b) => b.mtimeMs - a.mtimeMs)) {
    groups.set(video.listing, [...(groups.get(video.listing) ?? []), video])
  }
  return [...groups.entries()]
}

type Engine = EngineInterface

async function lengthOf($: Engine, path: string) {
  try {
    const { exitCode, stdout } = await $.process.run(
      [
        'ffprobe',
        '-v',
        'error',
        '-show_entries',
        'format=duration',
        '-of',
        'default=noprint_wrappers=1:nokey=1',
        path,
      ],
      { timeoutMs: 10000 },
    )
    const seconds = Number.parseFloat(stdout.trim())
    return exitCode === 0 && Number.isFinite(seconds) ? seconds : null
  } catch {
    return null
  }
}

/** The listing's property name: the first "# " heading of its listing.md. */
async function titleOf($: Engine, folder: string, fallback: string) {
  try {
    const text = await $.fs.read(`${folder}/listing.md`)
    const heading = /^#[ \t]+(.+?)\s*$/m.exec(text)?.[1]
    return heading || fallback
  } catch {
    return fallback
  }
}

/**
 * listings/ under the project root. Not the session's cwd: a shell `cd` into
 * a listing's output/ moves the cwd, and listings/ would then not be found.
 */
const listingsDir = async ($: Engine) => `${await $.session.root()}/${ROOT}`

async function scan($: Engine) {
  const root = await listingsDir($)
  const known = new Map(
    (await read($, videos)).map(v => [`${v.path}:${v.mtimeMs}`, v]),
  )
  const found: Video[] = []
  if (await $.fs.exists(root)) {
    for (const listing of await $.fs.list(root)) {
      if (listing.kind !== 'dir') continue
      const output = `${root}/${listing.name}/output`
      if (!(await $.fs.exists(output))) continue
      let title: string | undefined
      for (const file of await $.fs.list(output)) {
        if (file.kind !== 'file' || !isVideo(file.name)) continue
        const path = `${ROOT}/${listing.name}/output/${file.name}`
        const cached = known.get(`${path}:${file.mtimeMs}`)
        title ??= await titleOf($, `${root}/${listing.name}`, listing.name)
        found.push({
          listing: listing.name,
          title,
          name: file.name,
          path,
          sizeBytes: file.size,
          mtimeMs: file.mtimeMs,
          seconds: cached
            ? cached.seconds
            : await lengthOf($, `${output}/${file.name}`),
        })
      }
    }
  }
  await update($, videos, () => found)
}

const escapeHtml = (text: string) =>
  text.replace(/[&<>"']/g, c =>
    ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' })[c]!,
  )

/** The page's link to a video, relative to listings/ where the page sits. */
const hrefOf = (video: Video) =>
  [video.listing, 'output', video.name].map(encodeURIComponent).join('/')

/** The reference code at the front of a listing folder, e.g. "1069". */
export const codeOf = (listing: string) => /^([^-]+)-/.exec(listing)?.[1] ?? ''

/**
 * The name a download saves as: the property name, plus the file's own name
 * when the listing has more than one video. No "/" (888/71 is a room number).
 */
export const downloadName = (video: Video, isOnly: boolean) => {
  const dot = video.name.lastIndexOf('.')
  const ext = dot > 0 ? video.name.slice(dot) : ''
  const stem = dot > 0 ? video.name.slice(0, dot) : video.name
  const base = isOnly ? video.title : `${video.title} (${stem})`
  return `${base.replace(/[\\/:*?"<>|]+/g, '-').trim()}${ext}`
}

/** What the search box matches: property name, code, folder and file name. */
const searchTextOf = (video: Video) =>
  [video.title, codeOf(video.listing), video.listing, video.name]
    .join(' ')
    .toLowerCase()

/** Groups videos by the local day they were made, newest day and video first. */
export const groupByDay = (list: readonly Video[]) => {
  const groups = new Map<string, Video[]>()
  for (const video of [...list].sort((a, b) => b.mtimeMs - a.mtimeMs)) {
    const day = formatDate(video.mtimeMs).slice(0, 10)
    groups.set(day, [...(groups.get(day) ?? []), video])
  }
  return [...groups.entries()]
}

/** A day heading: "วันนี้" or "เมื่อวาน" before the date when it is one. */
export const dayLabel = (day: string, now: number) => {
  const today = formatDate(now).slice(0, 10)
  const yesterday = formatDate(now - 24 * 60 * 60 * 1000).slice(0, 10)
  if (day === today) return `วันนี้ · ${day}`
  if (day === yesterday) return `เมื่อวาน · ${day}`
  return day
}

/** One video's card: player, property name, file, length, size, date, download. */
const cardOf = (video: Video, isOnly: boolean) => `
    <figure data-search="${escapeHtml(searchTextOf(video))}">
      <video src="${hrefOf(video)}" controls preload="metadata" playsinline></video>
      <figcaption>
        <a class="title" href="${hrefOf(video)}" target="_blank">${escapeHtml(video.title)}</a>
        <span>${escapeHtml(video.name)}</span>
        <span>${formatLength(video.seconds)} · ${formatSize(video.sizeBytes)} · ${formatDate(video.mtimeMs)}</span>
        <a class="download" href="${hrefOf(video)}" download="${escapeHtml(downloadName(video, isOnly))}">⬇ ดาวน์โหลด</a>
      </figcaption>
    </figure>`

/**
 * A self-contained page that lists and plays every video, in two views the
 * user switches between: by listing and by day.
 */
export const buildPage = (list: readonly Video[], now: number) => {
  const groups = groupByListing(list)
  const days = groupByDay(list)
  const perListing = new Map(groups.map(([listing, items]) => [listing, items.length]))
  const card = (video: Video) => cardOf(video, perListing.get(video.listing) === 1)
  const section = (heading: string, items: Video[]) => `
<section>
  <h2>${heading}</h2>
  <div class="grid">${items.map(card).join('')}
  </div>
</section>`
  const byListing = groups
    .map(([listing, items]) => {
      const code = codeOf(listing)
      const tag = code ? ` <small>รหัสทรัพย์ ${escapeHtml(code)}</small>` : ''
      return section(`${escapeHtml(items[0]!.title)}${tag}`, items)
    })
    .join('')
  const byDay = days
    .map(([day, items]) =>
      section(`${escapeHtml(dayLabel(day, now))} <small>${items.length} วีดีโอ</small>`, items),
    )
    .join('')
  const sections = `
<div class="view" id="view-listing">${byListing}
</div>
<div class="view" id="view-day" hidden>${byDay}
</div>`
  const empty = `<p class="empty">ยังไม่มีวีดีโอใน ${ROOT}/*/output/</p>`
  return `<!DOCTYPE html>
<html lang="th">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>${TITLE}</title>
<style>
  body { margin: 0; padding: 24px; font-family: -apple-system, "Sukhumvit Set", sans-serif; background: #111; color: #eee; }
  header { display: flex; align-items: baseline; gap: 16px; margin-bottom: 8px; }
  h1 { margin: 0; font-size: 24px; }
  .meta, figcaption span, .empty, h2 small { color: #999; font-size: 13px; font-weight: normal; }
  h2 { font-size: 18px; margin: 32px 0 12px; }
  #search { width: 100%; max-width: 480px; box-sizing: border-box; margin: 12px 0 0; padding: 10px 14px; font: inherit; font-size: 15px; color: #eee; background: #1c1c1c; border: 1px solid #333; border-radius: 8px; }
  #search:focus { outline: none; border-color: #666; }
  [hidden] { display: none !important; }
  .tools { display: flex; flex-wrap: wrap; align-items: center; gap: 12px; margin-top: 12px; }
  .tools #search { margin: 0; }
  .views { display: inline-flex; background: #1c1c1c; border: 1px solid #333; border-radius: 8px; overflow: hidden; }
  .views button { font: inherit; font-size: 14px; color: #aaa; background: none; border: 0; padding: 9px 14px; cursor: pointer; }
  .views button[aria-pressed="true"] { color: #fff; background: #2a6df4; }
  .grid { display: grid; grid-template-columns: repeat(auto-fill, minmax(220px, 1fr)); gap: 16px; }
  figure { margin: 0; background: #1c1c1c; border-radius: 10px; overflow: hidden; }
  video { width: 100%; aspect-ratio: 9 / 16; background: #000; display: block; }
  figcaption { padding: 8px 10px; display: flex; flex-direction: column; gap: 2px; }
  a { color: #eee; text-decoration: none; word-break: break-word; }
  a:hover { text-decoration: underline; }
  a.title { font-weight: 600; }
  a.download { align-self: flex-start; margin-top: 6px; padding: 6px 12px; background: #2a6df4; border-radius: 6px; font-size: 13px; color: #fff; }
  a.download:hover { background: #1f5ad1; text-decoration: none; }
</style>
</head>
<body>
<header>
  <h1>🎬 ${TITLE}</h1>
  <span class="meta">${list.length} วีดีโอ · ${groups.length} ทรัพย์ · อัปเดต ${formatDate(now)}</span>
</header>
${
  list.length === 0
    ? empty
    : `<div class="tools">
  <input id="search" type="search" placeholder="ค้นหาชื่อทรัพย์ รหัสทรัพย์ หรือชื่อไฟล์" autocomplete="off">
  <div class="views" role="group" aria-label="แยกวีดีโอ">
    <button type="button" data-view="listing" aria-pressed="true">ตามทรัพย์</button>
    <button type="button" data-view="day" aria-pressed="false">ตามวันที่</button>
  </div>
</div>
<p id="none" class="empty" hidden>ไม่พบวีดีโอที่ตรงกับคำค้น</p>
${sections}
<script>
  const box = document.getElementById('search')
  const buttons = document.querySelectorAll('.views button')
  const showView = view => {
    for (const button of buttons) {
      button.setAttribute('aria-pressed', String(button.dataset.view === view))
    }
    for (const el of document.querySelectorAll('.view')) {
      el.hidden = el.id !== 'view-' + view
    }
    try { localStorage.setItem('video-list-view', view) } catch {}
  }
  for (const button of buttons) {
    button.addEventListener('click', () => showView(button.dataset.view))
  }
  let saved = null
  try { saved = localStorage.getItem('video-list-view') } catch {}
  if (saved === 'day') showView('day')
  box.addEventListener('input', () => {
    const words = box.value.toLowerCase().split(/\\s+/).filter(Boolean)
    let shown = 0
    for (const section of document.querySelectorAll('section')) {
      let inSection = 0
      for (const figure of section.querySelectorAll('figure')) {
        const text = figure.dataset.search
        const isMatch = words.every(word => text.includes(word))
        figure.hidden = !isMatch
        if (isMatch) inSection++
      }
      section.hidden = inSection === 0
      shown += inSection
    }
    document.getElementById('none').hidden = shown > 0
  })
</script>`
}
</body>
</html>
`
}

/** The page server's port while it runs; one per module life. */
let serverPort: Promise<number> | undefined

/**
 * Starts server.py on listings/ (Range support, so videos seek) and resolves
 * the port it bound. The child lives as long as the module.
 */
function startServer($: Engine, folder: string) {
  return new Promise<number>((resolve, reject) => {
    void (async () => {
      let isReady = false
      try {
        const child = $.process.spawn({
          argv: ['python3', `${$.plugin.root}/server.py`, folder],
        })
        let out = ''
        for await (const { stream, text } of child) {
          if (isReady || stream !== 'stdout') continue
          out += text
          const port = /PORT (\d+)/.exec(out)?.[1]
          if (port) {
            isReady = true
            resolve(Number(port))
          }
        }
      } catch (error) {
        if (!isReady) reject(error)
      } finally {
        serverPort = undefined
        if (!isReady) reject(new Error('page server stopped before it was ready'))
      }
    })()
  })
}

/** The app's built-in browser pane, by the name /mcp lists it under. */
const BROWSER = 'Claude Browser'

const textOf = (result: McpToolResult) =>
  result.content.map(block => (block.type === 'text' ? String(block.text) : '')).join('\n')

/** The pane's tab already showing a page at this origin, if any. */
async function tabAt($: Engine, server: string, origin: string) {
  const result = await $.mcp.call(server, 'tabs_context', {})
  if (result.isError) return undefined
  const json = /\{[\s\S]*\}/.exec(textOf(result))?.[0]
  if (!json) return undefined
  const context = JSON.parse(json) as {
    browserOpen?: boolean
    tabs?: { tabId: string; origin: string }[]
  }
  if (!context.browserOpen) return undefined
  return context.tabs?.find(tab => tab.origin === origin)?.tabId
}

/**
 * Opens the URL in the app's built-in browser pane, reloading the tab that
 * already shows the page rather than opening one more; false if it can't.
 */
async function openInPane($: Engine, url: string) {
  try {
    const browser = await $.mcp.connect(BROWSER)
    if (!browser.isConnected) return false
    const tabId = await tabAt($, browser.server, new URL(url).origin).catch(
      () => undefined,
    )
    if (tabId) {
      const shown = await $.mcp.call(browser.server, 'navigate', { url, tabId })
      if (!shown.isError) {
        await $.mcp.call(browser.server, 'tabs_select', { tabId })
        return true
      }
    }
    const opened = await $.mcp.call(browser.server, 'preview_start', { url })
    return !opened.isError
  } catch {
    return false
  }
}

/**
 * Scans, writes listings/videos.html, serves listings/ on localhost and opens
 * the page in the browser pane beside the chat (the default browser if the
 * pane is unavailable).
 */
async function openPage($: Engine) {
  try {
    await scan($)
    const root = await listingsDir($)
    await $.fs.write(
      `${root}/${PAGE}`,
      buildPage(await read($, videos), await $.clock.now()),
    )
    serverPort ??= startServer($, root)
    const url = `http://localhost:${await serverPort}/${PAGE}`
    if (await openInPane($, url)) return
    const { exitCode, stderr } = await $.process.run(['open', url])
    if (exitCode !== 0) $.ui.toast(`เปิด browser ไม่ได้: ${stderr.trim() || url}`)
  } catch (error) {
    serverPort = undefined
    $.ui.toast(`เปิด browser ไม่ได้: ${String(error)}`)
  }
}

export const register: Register = on => {
  on('session.start', async ($, e, next) => {
    const started = await next(e)
    await $.command.register({
      name: 'videos',
      description: 'Open a page of every finished listing video in the browser',
    })
    void scan($)
    return started
  })

  on('command.run', { command: 'videos' }, async $ => {
    await openPage($)
    return { text: 'เปิดหน้ารวมวีดีโอใน browser แล้ว' }
  })

  // A new video usually appears at the end of a turn (the editor's build).
  on('turn.complete', async ($, e, next) => {
    const done = await next(e)
    void scan($)
    return done
  })

  on('ui.render', { component: 'AbovePrompt' }, async ($, e, next) => {
    if (e.props.hasSurvey) return next(e)
    const { Box, Button } = $.ui.resolve(e)

    return (
      <Box flexDirection="row" justifyContent="flex-end">
        <Button
          key="open-videos"
          label={`🎬 ${TITLE}`}
          onPress={() => openPage($)}
        />
      </Box>
    )
  })

  // Same line as session-role's band, at its end: take our own row out
  // of the stack and draw the button beside the rest. Without a session-role
  // row, our own row (above) stands alone.
  on('ui.render', { component: 'AbovePromptList' }, async ($, e, next) => {
    const rows = e.props.rows
    const mine = rows.find(row => row.plugin === 'video-list')
    const hasRole = rows.some(row => row.plugin === 'session-role')
    if (!mine || !hasRole || e.props.hasSurvey) return next(e)

    const rest = await next({
      ...e,
      props: { ...e.props, rows: rows.filter(row => row !== mine) },
    })
    const { Box, Button } = $.ui.resolve(e)

    return (
      <Box flexDirection="row" alignItems="flex-start" columnGap={1}>
        <Box flexDirection="column" flexGrow={1} flexShrink={1}>
          {rest}
        </Box>
        <Button
          key="open-videos"
          label={`🎬 ${TITLE}`}
          plain
          onPress={() => openPage($)}
        />
      </Box>
    )
  })
}
