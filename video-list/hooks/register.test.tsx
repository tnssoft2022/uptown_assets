import type { On, RenderElement } from 'claude-code'
import { expect, test } from 'claude-code/testing'

import { formatLength, formatSize, groupByListing } from './register'

const PANE = {
  plugin: 'video-list',
  component: 'Pane',
  requestId: 'video-list',
  props: {
    title: 'วีดีโอทั้งหมด',
    isFocused: false,
    bodyColumns: 60,
    placement: 'dock',
    scroll: { offset: 0, bodyRows: 30 },
    view: {},
  },
} as const

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

/** A project with two listings, one video each, plus a non-video file. */
const project = (on: On) => {
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
      return { value: [file('final.mp4', 2000), file('build.sh', 3000)] }
    }
    if (path.endsWith('/listings/B02-house/output')) {
      return { value: [file('tiktok.mp4', 5000)] }
    }
    return { value: [] }
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
  on('ui.open', () => ({ value: { isPlaced: true } }))
  on('session.start', (_, e) => ({ cwd: e.cwd }))
}

test('the band shows the button with the video count', async ($, on) => {
  project(on)
  await $.session.start({ cwd: '/', surface: 'desktop', isInteractive: true })

  for (const surface of ['terminal', 'desktop'] as const) {
    const ui = await $.ui.mount({ ...BAND, surface })
    await ui.press({ key: 'open-videos' })
    const button = await ui.find({ type: 'Button', key: 'open-videos' })
    expect(button?.text).toContain('วีดีโอทั้งหมด (2)')
    await ui.unmount()
  }
})

test('the pane lists videos grouped by listing, newest first', async ($, on) => {
  project(on)
  await $.session.start({ cwd: '/', surface: 'desktop', isInteractive: true })

  for (const surface of ['terminal', 'desktop'] as const) {
    const band = await $.ui.mount({ ...BAND, surface })
    await band.press({ key: 'open-videos' })
    await band.unmount()
    const ui = await $.ui.mount({ ...PANE, surface })
    expect((await ui.find({ type: 'Text', text: /2 วีดีโอ/ }))?.text).toContain(
      '2 ทรัพย์',
    )
    expect(await ui.find({ type: 'Text', text: 'B02-house' })).toBeTruthy()
    expect(await ui.find({ type: 'Text', text: 'final.mp4' })).toBeTruthy()
    expect(await ui.find({ type: 'Text', text: 'build.sh' })).toBeFalsy()
    expect(
      await ui.find({
        type: 'Button',
        key: 'open:listings/A01-condo/output/final.mp4',
      }),
    ).toBeTruthy()
    await ui.unmount()
  }
})

test('formatting helpers', () => {
  expect(formatLength(31.4)).toBe('0:31')
  expect(formatLength(75)).toBe('1:15')
  expect(formatLength(null)).toBe('-')
  expect(formatSize(5 * 1024 * 1024)).toBe('5.0 MB')
  const v = (listing: string, mtimeMs: number) => ({
    listing,
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
    expect(button?.text).toContain('วีดีโอทั้งหมด (2)')
    await ui.unmount()
  }
})
