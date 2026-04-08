import { describe, expect, it } from 'vitest';
import { buildClubPerformanceMonitor } from './performanceMonitor';

describe('buildClubPerformanceMonitor', () => {
  it('marks the club as watch when load durations and traces are slow', () => {
    const monitor = buildClubPerformanceMonitor({
      selectedClub: { id: 'club-1', name: 'Robotics Club' },
      workspacePerformance: {
        updatedAt: '2026-04-06T08:00:00.000Z',
        directory: { status: 'healthy', durationMs: 420, loadedAt: '2026-04-06T08:00:00.000Z' },
        selectedClub: { status: 'healthy', durationMs: 2200, loadedAt: '2026-04-06T08:00:03.000Z' },
        traces: [
          { url: '/clubs/', status: 200, durationMs: 260 },
          { url: '/club-events/?club_id=club-1', status: 200, durationMs: 1480 },
          { url: '/clubs/club-1/analytics', status: 200, durationMs: 1620 }
        ]
      },
      members: new Array(60).fill({}),
      applications: new Array(15).fill({}),
      events: [{ status: 'archived' }, { status: 'archived' }, { status: 'open' }],
      eventRegistrations: new Array(30).fill({})
    });

    expect(monitor.status).toBe('watch');
    expect(monitor.slowTraceCount).toBe(2);
    expect(monitor.archivedEvents).toBe(2);
    expect(monitor.p95DurationMs).toBe(1620);
  });

  it('marks the club as critical when request failures are present', () => {
    const monitor = buildClubPerformanceMonitor({
      selectedClub: { id: 'club-2', name: 'Drama Club' },
      workspacePerformance: {
        updatedAt: '2026-04-06T08:00:00.000Z',
        directory: { status: 'error', durationMs: null, loadedAt: '2026-04-06T08:00:00.000Z' },
        selectedClub: { status: 'error', durationMs: 0, loadedAt: '2026-04-06T08:00:01.000Z' },
        traces: [
          { url: '/clubs/', status: 500, durationMs: 40 },
          { url: '/clubs/club-2/analytics', status: 0, durationMs: 0 }
        ]
      },
      members: [],
      applications: [],
      events: [],
      eventRegistrations: []
    });

    expect(monitor.status).toBe('critical');
    expect(monitor.errorTraceCount).toBe(2);
    expect(monitor.recommendations[0]).toContain('retry');
  });
});
