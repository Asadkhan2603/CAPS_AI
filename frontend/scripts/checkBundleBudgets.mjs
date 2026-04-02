import { promises as fs } from 'node:fs';
import path from 'node:path';

const DIST_DIR = path.resolve(process.cwd(), 'dist');
const ASSETS_DIR = path.join(DIST_DIR, 'assets');
const REPORT_PATH = path.join(DIST_DIR, 'bundle-budget-report.json');

const FILE_BUDGETS = [
  { label: 'charts-vendor', prefix: 'charts-vendor-', ext: '.js', maxKiB: 390 },
  { label: 'react-vendor', prefix: 'react-vendor-', ext: '.js', maxKiB: 180 },
  { label: 'motion-vendor', prefix: 'motion-vendor-', ext: '.js', maxKiB: 140 },
  { label: 'app-entry', prefix: 'index-', ext: '.js', maxKiB: 90 },
  { label: 'app-styles', prefix: 'index-', ext: '.css', maxKiB: 95 },
];

const TOTAL_BUDGETS = [
  { label: 'total-js', ext: '.js', maxKiB: 1400 },
  { label: 'total-css', ext: '.css', maxKiB: 100 },
];

function formatKiB(bytes) {
  return Number((bytes / 1024).toFixed(2));
}

async function listAssetFiles() {
  const names = await fs.readdir(ASSETS_DIR);
  const files = await Promise.all(
    names.map(async (name) => {
      const filePath = path.join(ASSETS_DIR, name);
      const stats = await fs.stat(filePath);
      return {
        name,
        path: filePath,
        sizeBytes: stats.size,
        sizeKiB: formatKiB(stats.size),
      };
    }),
  );
  return files.filter((file) => file.name.endsWith('.js') || file.name.endsWith('.css'));
}

function findBudgetFile(files, budget) {
  return files.find((file) => file.name.startsWith(budget.prefix) && file.name.endsWith(budget.ext)) || null;
}

async function main() {
  const files = await listAssetFiles();
  const fileChecks = FILE_BUDGETS.map((budget) => {
    const matched = findBudgetFile(files, budget);
    if (!matched) {
      return {
        label: budget.label,
        status: 'missing',
        maxKiB: budget.maxKiB,
      };
    }
    return {
      label: budget.label,
      file: matched.name,
      sizeKiB: matched.sizeKiB,
      maxKiB: budget.maxKiB,
      status: matched.sizeKiB <= budget.maxKiB ? 'pass' : 'fail',
    };
  });

  const totalChecks = TOTAL_BUDGETS.map((budget) => {
    const matchingFiles = files.filter((file) => file.name.endsWith(budget.ext));
    const totalBytes = matchingFiles.reduce((sum, file) => sum + file.sizeBytes, 0);
    const sizeKiB = formatKiB(totalBytes);
    return {
      label: budget.label,
      sizeKiB,
      maxKiB: budget.maxKiB,
      status: sizeKiB <= budget.maxKiB ? 'pass' : 'fail',
    };
  });

  const report = {
    generatedAt: new Date().toISOString(),
    files,
    fileChecks,
    totalChecks,
  };

  await fs.writeFile(REPORT_PATH, `${JSON.stringify(report, null, 2)}\n`, 'utf8');

  const failures = [...fileChecks, ...totalChecks].filter((check) => check.status === 'fail');

  console.log('Bundle budget report written to dist/bundle-budget-report.json');
  for (const check of [...fileChecks, ...totalChecks]) {
    if (check.status === 'missing') {
      console.log(`[warn] ${check.label}: expected bundle was not found`);
      continue;
    }
    const measured = typeof check.sizeKiB === 'number' ? `${check.sizeKiB.toFixed(2)} KiB` : 'n/a';
    console.log(`[${check.status}] ${check.label}: ${measured} (budget ${check.maxKiB} KiB)`);
  }

  if (failures.length) {
    console.error('Bundle budget check failed.');
    process.exit(1);
  }
}

main().catch((error) => {
  console.error(error);
  process.exit(1);
});
