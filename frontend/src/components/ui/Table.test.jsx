// @vitest-environment jsdom

import React, { act } from 'react';
import { createRoot } from 'react-dom/client';
import { afterEach, beforeEach, describe, expect, it } from 'vitest';
import Table from './Table';

let container = null;
let root = null;
const reactActEnvironment = globalThis;

function waitForTick() {
  return new Promise((resolve) => window.setTimeout(resolve, 0));
}

async function renderComponent(component) {
  container = document.createElement('div');
  document.body.appendChild(container);
  root = createRoot(container);

  await act(async () => {
    root.render(component);
    await waitForTick();
  });
}

describe('Table', () => {
  beforeEach(() => {
    reactActEnvironment.IS_REACT_ACT_ENVIRONMENT = true;
  });

  afterEach(async () => {
    await act(async () => {
      root?.unmount();
      await waitForTick();
    });
    root = null;
    if (container) {
      container.remove();
    }
    container = null;
    document.body.innerHTML = '';
    reactActEnvironment.IS_REACT_ACT_ENVIRONMENT = false;
  });

  it('keeps default table behavior unchanged when responsive mode is not enabled', async () => {
    await renderComponent(
      <Table
        columns={[
          { key: 'name', label: 'Name' },
          { key: 'status', label: 'Status' },
        ]}
        data={[{ id: 'row-1', name: 'Alpha', status: 'Active' }]}
      />
    );

    expect(document.querySelector('table')).toBeTruthy();
    expect(document.body.textContent).toContain('Name');
    expect(document.body.textContent).toContain('Alpha');
  });

  it('renders responsive card content when responsive mode and mobileCardRender are provided', async () => {
    await renderComponent(
      <Table
        responsive
        mobileBreakpoint="md"
        stickyActions
        columns={[
          { key: 'name', label: 'Name', priority: 'high' },
        ]}
        data={[{ id: 'row-1', name: 'Alpha' }]}
        rowActions={[{ key: 'open', label: 'Open', onClick: () => {} }]}
        mobileCardRender={(row, { renderRowActions }) => (
          <div>
            <p>Mobile card for {row.name}</p>
            {renderRowActions(row)}
          </div>
        )}
      />
    );

    expect(document.body.textContent).toContain('Mobile card for Alpha');
    expect(document.body.textContent).toContain('Open');
    expect(document.querySelector('table')).toBeTruthy();
  });

  it('keeps high-priority fields visible and low-priority fields available in responsive fallback cards', async () => {
    await renderComponent(
      <Table
        responsive
        columns={[
          { key: 'title', label: 'Title', priority: 'high' },
          { key: 'owner', label: 'Owner', priority: 'medium' },
          { key: 'notes', label: 'Notes', priority: 'low' },
        ]}
        data={[{ id: 'row-1', title: 'Governance Review', owner: 'Alice', notes: 'Needs second approver' }]}
        rowActions={[{ key: 'approve', label: 'Approve', onClick: () => {} }]}
      />
    );

    expect(document.body.textContent).toContain('Governance Review');
    expect(document.body.textContent).toContain('Alice');
    expect(document.body.textContent).toContain('Notes');
    expect(document.body.textContent).toContain('Needs second approver');
    expect(document.body.textContent).toContain('Approve');
  });
});
