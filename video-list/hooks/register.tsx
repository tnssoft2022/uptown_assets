import { atom, read, update } from 'claude-code'
import type { EngineInterface, Register } from 'claude-code'

import type { Video } from '../types'

const PANE = 'video-list'
const TITLE = 'วีดีโอทั้งหมด'
const ROOT = 'listings'
const EXTENSIONS = ['.mp4', '.mov', '.m4v']

// Change the tag when Video's fields change: it declines what an earlier
// version stored, which outlives a reload.
const videos = atom({ plugin: 'video-list', key: 'videos' } as const, [], {
  shape: 'videos-1',
})
const isScanning = atom(
  { plugin: 'video-list', key: 'isScanning' } as const,
  false,
)

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

async function scan($: Engine) {
  await update($, isScanning, () => true)
  try {
    const known = new Map(
      (await read($, videos)).map(v => [`${v.path}:${v.mtimeMs}`, v]),
    )
    const found: Video[] = []
    if (await $.fs.exists(ROOT)) {
      for (const listing of await $.fs.list(ROOT)) {
        if (listing.kind !== 'dir') continue
        const output = `${ROOT}/${listing.name}/output`
        if (!(await $.fs.exists(output))) continue
        for (const file of await $.fs.list(output)) {
          if (file.kind !== 'file' || !isVideo(file.name)) continue
          const path = `${output}/${file.name}`
          const cached = known.get(`${path}:${file.mtimeMs}`)
          found.push({
            listing: listing.name,
            name: file.name,
            path,
            sizeBytes: file.size,
            mtimeMs: file.mtimeMs,
            seconds: cached ? cached.seconds : await lengthOf($, path),
          })
        }
      }
    }
    await update($, videos, () => found)
  } finally {
    await update($, isScanning, () => false)
  }
}

async function openPane($: Engine) {
  await $.ui.open({ id: PANE, title: TITLE })
  await scan($)
}

async function openFile($: Engine, path: string, inFinder: boolean) {
  const { exitCode, stderr } = await $.process.run(
    inFinder ? ['open', '-R', path] : ['open', path],
  )
  if (exitCode !== 0) $.ui.toast(`เปิดไม่ได้: ${stderr.trim() || path}`)
}

export const register: Register = on => {
  on('session.start', async ($, e, next) => {
    const started = await next(e)
    await $.command.register({
      name: 'videos',
      description: 'Show every finished listing video in a pane',
    })
    void scan($)
    return started
  })

  on('command.run', { command: 'videos' }, async $ => {
    await openPane($)
    return { text: 'เปิดรายการวีดีโอทั้งหมดแล้ว' }
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
    const count = (await read($, videos)).length

    return (
      <Box flexDirection="row" justifyContent="flex-end">
        <Button
          key="open-videos"
          label={`🎬 ${TITLE} (${count})`}
          onPress={() => openPane($)}
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
    const count = (await read($, videos)).length

    return (
      <Box flexDirection="row" alignItems="flex-start" columnGap={1}>
        <Box flexDirection="column" flexGrow={1} flexShrink={1}>
          {rest}
        </Box>
        <Button
          key="open-videos"
          label={`🎬 ${TITLE} (${count})`}
          plain
          onPress={() => openPane($)}
        />
      </Box>
    )
  })

  on('ui.render', { component: 'Pane', requestId: PANE }, async ($, e) => {
    const { Box, Button, Text } = $.ui.resolve(e)
    const list = await read($, videos)
    const scanning = await read($, isScanning)

    if (e.props.placement === 'widget') {
      return <Text>🎬 {list.length} วีดีโอ</Text>
    }

    const groups = groupByListing(list)

    return (
      <Box flexDirection="column" gap={1}>
        <Box flexDirection="row" justifyContent="space-between">
          <Text dimColor>
            {scanning ? 'กำลังโหลด…' : `${list.length} วีดีโอ · ${groups.length} ทรัพย์`}
          </Text>
          <Button key="refresh" label="↻ โหลดใหม่" onPress={() => scan($)} />
        </Box>
        {list.length === 0 && !scanning && (
          <Text dimColor>ยังไม่มีวีดีโอใน {ROOT}/*/output/</Text>
        )}
        {groups.map(([listing, items]) => (
          <Box flexDirection="column">
            <Text bold>{listing}</Text>
            {items.map(video => (
              <Box flexDirection="column" paddingLeft={2}>
                <Text>{video.name}</Text>
                <Box flexDirection="row" gap={1}>
                  <Text dimColor>
                    {formatLength(video.seconds)} · {formatSize(video.sizeBytes)} ·{' '}
                    {formatDate(video.mtimeMs)}
                  </Text>
                  <Button
                    key={`open:${video.path}`}
                    label="เปิด"
                    onPress={() => openFile($, video.path, false)}
                  />
                  <Button
                    key={`finder:${video.path}`}
                    label="Finder"
                    dimColor
                    onPress={() => openFile($, video.path, true)}
                  />
                </Box>
              </Box>
            ))}
          </Box>
        ))}
      </Box>
    )
  })
}
