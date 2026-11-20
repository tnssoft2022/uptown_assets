import type { On, RenderElement } from 'claude-code'
import { expect, test } from 'claude-code/testing'

import {
  buildPage,
  codeOf,
  dayLabel,
  downloadName,
  formatLength,
  formatSize,
  groupByDay,
  groupByListing,
  infoOf,
  listingOf,
  parseSteps,
  tagOf,
} from './register'

const BAND = {
  plugin: 'video-list',
  component: 'AbovePrompt',
  props: {
    hasSurvey: false,
    isCollapsed: false,
    isWorking: false,
    maxRows: 10,
    bodyColumns: 80,
    scroll: { offset: 0, bodyRows: 10 },
    view: {},
  },
} as const

const dir = (name: string) =>
  ({ name, kind: 'dir', size: 0, mtimeMs: 0, isLink: false }) as const
const file = (name: string, mtimeMs: number) =>
  ({ name, kind: 'file', size: 5 * 1024 * 1024, mtimeMs, isLink: false }) as const

/**
 * A project with two listings, one video each, plus a non-video file;
 * with a progress table, A01-condo's output/ also holds progress.md.
 */
const project = (on: On, progress?: string) => {
  on('fs.exists', () => ({ value: true }))
  on('fs.list', (_, e) => {
    const path = e.path
    if (path.endsWith('/listings')) {
      return {
        value: [
          dir('A01-condo'),
          dir('B02-house'),
          file('.gitignore', 1),
        ],
      }
    }
    if (path.endsWith('/listings/A01-condo/output')) {
      return {
        value: [
          file('final.mp4', 2000),
          file('build.sh', 3000),
          ...(progress ? [file('progress.md', 9000)] : []),
        ],
      }
    }
    if (path.endsWith('/listings/B02-house/output')) {
      return { value: [file('tiktok.mp4', 5000)] }
    }
    return { value: [] }
  })
  // B02-house has no listing.md heading: its title falls back to the folder.
  on('fs.read', (_, e) => {
    if (progress && e.path === '/project/listings/A01-condo/output/progress.md') {
      return { value: progress }
    }
    if (e.path === '/project/listings/A01-condo/listing.md') {
      return {
        value: '# คอนโด อโศก ห้อง 12/34\n\n- รหัสทรัพย์: A01\n- ประเภททรัพย์: คอนโด\n- ประเภทประกาศ: ขาย\n',
      }
    }
    throw new Error(`no file ${e.path}`)
  })
  on('process.run', () => ({
    value: {
      exitCode: 0,
      stdout: '31.4\n',
      stderr: '',
      isStdoutTruncated: false,
      isStderrTruncated: false,
    },
  }))
  on('command.register', () => ({ value: { command: 'videos' } }))
  on('session.start', (_, e) => ({ cwd: e.cwd }))
  on('session.root', () => ({ value: '/project' }))
  on('clock.now', () => ({ value: Date.UTC(2026, 10, 20, 11, 0) }))
  on('ui.toast', (_, e) => {
    throw new Error(`unexpected toast: ${JSON.stringify(e)}`)
  })
}

test('the band shows the button without a count', async ($, on) => {
  project(on)
  await $.session.start({ cwd: '/', surface: 'desktop', isInteractive: true })

  for (const surface of ['terminal', 'desktop'] as const) {
    const ui = await $.ui.mount({ ...BAND, surface })
    await ui.press({ key: 'open-videos' })
    const button = await ui.find({ type: 'Button', key: 'open-videos' })
    expect(button?.text).toBe('🎬 วีดีโอทั้งหมด')
    const steps = await ui.find({ type: 'Button', key: 'toggle-steps' })
    expect(steps?.text).toBe('📋 เปิด/ปิดขั้นตอน')
    await ui.unmount()
  }
})

test('the button writes the page, serves it and opens it in the browser pane', async ($, on) => {
  project(on)
  const writes: { path: string; text: string }[] = []
  on('fs.write', (_, e) => {
    writes.push(e)
    return { value: undefined }
  })
  const spawns: string[][] = []
  on('process.spawn', async function* (_, e) {
    spawns.push([...e.argv])
    yield { stream: 'stdout', text: 'PORT 4321\n' }
    return { value: { code: 0, signal: null } }
  })
  on('mcp.connect', () => ({
    value: { isConnected: true, server: 'Claude Browser' },
  }))
  const calls: { server: string; tool: string; args: Record<string, unknown> }[] = []
  on('mcp.call', (_, e) => {
    calls.push(e)
    if (e.tool === 'tabs_context') {
      const text = JSON.stringify({ browserOpen: false, tabs: [] })
      return { value: { content: [{ type: 'text', text }], isError: false } }
    }
    return { value: { content: [], isError: false } }
  })
  // A shell cd moved the cwd into a listing's output/; the root stays put.
  on('session.cwd', () => ({ value: '/project/listings/A01-condo/output' }))
  await $.session.start({ cwd: '/project', surface: 'desktop', isInteractive: true })

  const band = await $.ui.mount({ ...BAND, surface: 'desktop' })
  await band.press({ key: 'open-videos' })
  await band.unmount()

  const page = writes.find(w => w.path === '/project/listings/videos.html')
  expect(page).toBeTruthy()
  expect(page!.text).toContain('2 วีดีโอ · 2 ทรัพย์')
  expect(page!.text).toContain('src="A01-condo/output/final.mp4"')
  expect(page!.text).not.toContain('build.sh')
  expect(page!.text).toContain('class="title" href="A01-condo/output/final.mp4" target="_blank">คอนโด อโศก ห้อง 12/34</a>')
  expect(page!.text).toContain('download="คอนโด อโศก ห้อง 12-34.mp4"')
  expect(page!.text).toContain('รหัสทรัพย์ A01')
  expect(page!.text).toContain('>B02-house</a>')
  expect(page!.text).toContain('<small>คอนโด · ขาย · รหัสทรัพย์ A01</small>')
  expect(page!.text).toContain('<span class="tag">คอนโด · ขาย</span>')
  expect(page!.text).toContain('data-kind="คอนโด" aria-pressed="false">คอนโด</button>')
  // B02-house has no type: no tag, and no filter button for it.
  expect(page!.text).toContain('<small>รหัสทรัพย์ B02</small>')
  expect(page!.text.split('<span class="tag">').length - 1).toBe(2)
  expect(page!.text).toContain('id="search"')
  expect(page!.text).toContain('data-view="day"')
  // Each video shows once per view; the day view starts hidden.
  expect(page!.text.split('src="A01-condo/output/final.mp4"').length - 1).toBe(2)
  expect(page!.text).toContain('<div class="view" id="view-day" hidden>')
  expect(page!.text.indexOf('B02-house')).toBeLessThan(page!.text.indexOf('A01-condo'))
  expect(spawns[0]?.[0]).toBe('python3')
  expect(spawns[0]?.[2]).toBe('/project/listings')
  expect(calls).toContainEqual({
    server: 'Claude Browser',
    tool: 'preview_start',
    args: { url: 'http://localhost:4321/videos.html' },
  })
})

test('the page escapes names and links', () => {
  const html = buildPage(
    [
      {
        listing: 'A&B <x>',
        title: 'บ้าน "สวย" & ใหม่',
        kind: 'บ้าน<เดี่ยว>',
        deal: '',
        name: 'ไฟนอล 1.mp4',
        path: '',
        sizeBytes: 0,
        mtimeMs: 0,
        seconds: 12,
      },
    ],
    0,
  )
  expect(html).toContain('<h2>บ้าน &quot;สวย&quot; &amp; ใหม่ <small>บ้าน&lt;เดี่ยว&gt;</small></h2>')
  expect(html).toContain('download="บ้าน -สวย- &amp; ใหม่.mp4"')
  expect(html).toContain(
    `src="${encodeURIComponent('A&B <x>')}/output/${encodeURIComponent('ไฟนอล 1.mp4')}"`,
  )
  expect(buildPage([], 0)).toContain('ยังไม่มีวีดีโอ')
  expect(html).toContain('<span class="tag">บ้าน&lt;เดี่ยว&gt;</span>')
  expect(buildPage([], 0)).not.toContain('id="search"')
})

test('formatting helpers', () => {
  expect(formatLength(31.4)).toBe('0:31')
  expect(formatLength(75)).toBe('1:15')
  expect(formatLength(null)).toBe('-')
  expect(formatSize(5 * 1024 * 1024)).toBe('5.0 MB')
  const v = (listing: string, mtimeMs: number) => ({
    listing,
    title: listing,
    kind: '',
    deal: '',
    name: 'x.mp4',
    path: '',
    sizeBytes: 0,
    mtimeMs,
    seconds: null,
  })
  expect(groupByListing([v('A', 1), v('B', 3), v('A', 2)]).map(g => g[0])).toEqual([
    'B',
    'A',
  ])
  const at = (y: number, m: number, d: number, h: number) => new Date(y, m - 1, d, h).getTime()
  expect(
    groupByDay([v('A', at(2026, 11, 19, 9)), v('B', at(2026, 11, 20, 8)), v('C', at(2026, 11, 20, 18))]).map(
      ([day, items]) => [day, items.map(i => i.listing)],
    ),
  ).toEqual([
    ['20/11/2026', ['C', 'B']],
    ['19/11/2026', ['A']],
  ])
  const now = at(2026, 11, 20, 12)
  expect(dayLabel('20/11/2026', now)).toBe('วันนี้ · 20/11/2026')
  expect(dayLabel('19/11/2026', now)).toBe('เมื่อวาน · 19/11/2026')
  expect(dayLabel('01/11/2026', now)).toBe('01/11/2026')
  expect(codeOf('1069-ladprao64-house-131')).toBe('1069')
  expect(codeOf('nocode')).toBe('')
  const video = { ...v('A', 1), title: 'ห้อง 888/71', name: 'final.v2.mp4' }
  expect(downloadName(video, true)).toBe('ห้อง 888-71.mp4')
  expect(downloadName(video, false)).toBe('ห้อง 888-71 (final.v2).mp4')
  expect(infoOf('# บ้าน 131\n\n- ประเภททรัพย์: บ้านเดี่ยว\n- ประเภทประกาศ: เช่า\n', 'f')).toEqual({
    title: 'บ้าน 131',
    kind: 'บ้านเดี่ยว',
    deal: 'เช่า',
  })
  expect(infoOf('- ประเภททรัพย์: ถามผู้ใช้\n- ประเภทประกาศ:  -\n', 'f')).toEqual({ title: 'f', kind: '', deal: '' })
  expect(tagOf({ ...video, kind: 'คอนโด', deal: '' })).toBe('คอนโด')
  expect(tagOf({ ...video, kind: '', deal: 'เช่า' })).toBe('เช่า')
})

test('beside a session-role row, the button joins that line', async ($, on) => {
  project(on)
  await $.session.start({ cwd: '/', surface: 'desktop', isInteractive: true })

  for (const surface of ['terminal', 'desktop'] as const) {
    const band = await $.ui.mount({ ...BAND, surface })
    await band.press({ key: 'open-videos' })
    await band.unmount()

    const ui = await $.ui.mount({
      plugin: 'video-list',
      component: 'AbovePromptList',
      surface,
      props: {
        ...BAND.props,
        rows: [
          { plugin: 'session-role', tree: h('Text', {}, 'Role director ↻') as RenderElement },
          { plugin: 'video-list', tree: h('Text', {}, 'own row') as RenderElement },
        ],
      },
    })
    expect((await ui.find({ type: 'Text', text: /Role director/ }))?.text).toBe(
      'Role director ↻',
    )
    expect(await ui.find({ type: 'Text', text: 'own row' })).toBeFalsy()
    const button = await ui.find({ type: 'Button', key: 'open-videos' })
    expect(button?.text).toBe('🎬 วีดีโอทั้งหมด')
    const steps = await ui.find({ type: 'Button', key: 'toggle-steps' })
    expect(steps?.text).toBe('📋 เปิด/ปิดขั้นตอน')
    await ui.unmount()
  }
})

const PROGRESS = `# ความคืบหน้า

| # | ขั้นตอน | สถานะ | ใช้เวลา |
|---|---|---|---|
| 1 | ดึงประกาศ | ✅ เสร็จ | 42 วิ |
| 2 | เลือกสไตล์ | ⏸ รอคุณ | |
| 3 | เขียนบรีฟ | ⬜ รอ | |
`

test('progress.md rows become steps', () => {
  expect(parseSteps(PROGRESS)).toEqual([
    { number: '1', name: 'ดึงประกาศ', status: '✅ เสร็จ', time: '42 วิ' },
    { number: '2', name: 'เลือกสไตล์', status: '⏸ รอคุณ', time: '' },
    { number: '3', name: 'เขียนบรีฟ', status: '⬜ รอ', time: '' },
  ])
  expect(parseSteps('no table')).toEqual([])
})

test('a tool call names its listing by the progress.md path', () => {
  expect(listingOf({ file_path: '/project/listings/A01-condo/output/progress.md' })).toBe('A01-condo')
  expect(listingOf({ command: "cat 'listings/B02-house/output/progress.md'" })).toBe('B02-house')
  expect(listingOf({ file_path: '/project/listings/A01-condo/brief.md' })).toBeNull()
  expect(listingOf({ command: 'ls' })).toBeNull()
})

test('the steps pane opens when the work starts, and the button closes and reopens it', async ($, on) => {
  project(on, PROGRESS)
  // The surface's pane record: what open adds and close takes away.
  const open = new Map<string, string>()
  on('ui.panes', () => ({
    value: [...open].map(([id, title]) => ({
      id,
      title,
      isShown: true,
      isFocused: false,
      isPlaced: true,
    })),
  }))
  on('ui.open', (_, e) => {
    open.set(e.id, e.title ?? e.id)
    return { value: { isPlaced: true } }
  })
  on('ui.close', (_, e) => {
    open.delete(e.id)
    return { value: undefined }
  })
  on('tool.call', () => ({ result: {} }))
  await $.session.start({ cwd: '/project', surface: 'desktop', isInteractive: true })
  await $.tool.call({
    tool: 'Edit',
    file_path: '/project/listings/A01-condo/output/progress.md',
    old_string: 'a',
    new_string: 'b',
  })

  // The first progress.md this session touches opens the pane by itself.
  expect([...open]).toEqual([['steps', 'ขั้นตอนการทำงาน']])

  const band = await $.ui.mount({ ...BAND, surface: 'desktop' })
  await band.press({ key: 'toggle-steps' })
  expect(open.size).toBe(0)
  // Later updates of the same table leave a closed pane closed.
  await $.tool.call({
    tool: 'Edit',
    file_path: '/project/listings/A01-condo/output/progress.md',
    old_string: 'b',
    new_string: 'c',
  })
  expect(open.size).toBe(0)
  await band.press({ key: 'toggle-steps' })
  expect([...open]).toEqual([['steps', 'ขั้นตอนการทำงาน']])

  const pane = await $.ui.mount({
    plugin: 'video-list',
    component: 'Pane',
    requestId: 'steps',
    surface: 'desktop',
    props: {
      title: 'ขั้นตอนการทำงาน',
      isFocused: false,
      bodyColumns: 60,
      placement: 'dock',
      scroll: { offset: 0, bodyRows: 20 },
      view: {},
    },
  })
  expect((await pane.find({ type: 'Text', text: 'คอนโด อโศก ห้อง 12/34' }))?.text).toBe('คอนโด อโศก ห้อง 12/34')
  expect(await pane.find({ type: 'Text', text: /เสร็จ 1\/3 ขั้นตอน/ })).toBeTruthy()
  expect(await pane.find({ type: 'Text', text: '⏸ รอคุณ เลือกสไตล์' })).toBeTruthy()
  expect(await pane.find({ type: 'Text', text: '42 วิ' })).toBeTruthy()
  await pane.unmount()

  await band.press({ key: 'toggle-steps' })
  expect(open.size).toBe(0)
  await band.unmount()
})

test('a progress table this session never touched stays out of its pane', async ($, on) => {
  // A01-condo has a progress.md, written by another session.
  project(on, PROGRESS)
  await $.session.start({ cwd: '/project', surface: 'desktop', isInteractive: true })
  const pane = await $.ui.mount({
    plugin: 'video-list',
    component: 'Pane',
    requestId: 'steps',
    surface: 'desktop',
    props: {
      title: 'ขั้นตอนการทำงาน',
      isFocused: false,
      bodyColumns: 60,
      placement: 'dock',
      scroll: { offset: 0, bodyRows: 20 },
      view: {},
    },
  })
  expect(await pane.find({ type: 'Text', text: 'ยังไม่มีขั้นตอนการทำงานใน session นี้' })).toBeTruthy()
  await pane.unmount()
})
