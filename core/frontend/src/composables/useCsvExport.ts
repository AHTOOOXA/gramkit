/**
 * Column definition for a CSV export: a header label + a value accessor.
 */
export interface CsvColumn<T> {
  /** Header cell text. */
  header: string;
  /** Extracts the cell value for a row. */
  accessor: (row: T) => unknown;
}

/**
 * useCsvExport — turns rows + column defs into a CSV file and triggers a
 * client-side download. No backend round-trip (v1). SSG-safe: it never touches
 * `window`/`document` at module scope, only inside `exportCsv`, which is only
 * ever called from a user-initiated handler in the browser.
 *
 * @example
 * const { exportCsv } = useCsvExport();
 * exportCsv(rows, [{ header: 'Action', accessor: (r) => r.action }], 'audit-log');
 */
export function useCsvExport(): {
  exportCsv: <T>(rows: T[], columns: CsvColumn<T>[], filename?: string) => void;
} {
  const escapeCell = (value: unknown): string => {
    if (value === null || value === undefined) return '';
    let str: string;
    if (typeof value === 'object') {
      str = JSON.stringify(value);
    } else {
      str = String(value);
    }
    // Spreadsheet formula injection: a cell starting with = + - @ (or tab / CR)
    // runs as a formula in Excel / Sheets. Prefix it so it stays text.
    if (/^[=+\-@\t\r]/.test(str)) {
      str = `'${str}`;
    }
    // RFC-4180: wrap in quotes and double any embedded quotes when the cell
    // contains a comma, quote or newline.
    if (/[",\n\r]/.test(str)) {
      return `"${str.replace(/"/g, '""')}"`;
    }
    return str;
  };

  const exportCsv = <T>(rows: T[], columns: CsvColumn<T>[], filename = 'export'): void => {
    if (typeof document === 'undefined') return;

    const headerLine = columns.map((c) => escapeCell(c.header)).join(',');
    const bodyLines = rows.map((row) =>
      columns.map((c) => escapeCell(c.accessor(row))).join(','),
    );
    // Prepend a BOM so Excel reads UTF-8 (Cyrillic) correctly.
    const csv = '﻿' + [headerLine, ...bodyLines].join('\r\n');

    const blob = new Blob([csv], { type: 'text/csv;charset=utf-8;' });
    const url = URL.createObjectURL(blob);
    const link = document.createElement('a');
    link.href = url;
    link.download = filename.endsWith('.csv') ? filename : `${filename}.csv`;
    document.body.appendChild(link);
    link.click();
    document.body.removeChild(link);
    URL.revokeObjectURL(url);
  };

  return { exportCsv };
}
