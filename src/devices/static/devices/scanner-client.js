// Scanner browser client: the only JS file that knows the scanner paths (IR-07).
// It calls the Dummy Scanner training contract, not the real scanner (A-10).
(function () {
  'use strict';

  const BASE = '/api';
  const SCAN_POLL_MS = 250;
  const { requestJson } = window.WeighingMS.devices;

  async function readStatus() {
    const data = await requestJson('GET', BASE + '/scanner/status');
    return data.status;
  }

  function readLatestScan() {
    return requestJson('GET', BASE + '/scanner/scans/latest').then((data) => data.scan);
  }

  // Calls onScan({scanId, kind, code, scannedAt}) once per new scan. A scan
  // that already existed when watching started is ignored. Failures go to
  // onFailure(DeviceError) and change nothing; watching continues.
  function watchScans(onScan, onFailure) {
    let stopped = false;
    let timer = null;
    let baselineTaken = false;
    let lastScanId = null;

    async function tick() {
      try {
        const scan = await readLatestScan();
        if (!stopped) {
          const isNew = scan && (lastScanId === null || scan.scanId > lastScanId);
          if (scan && isNew) {
            lastScanId = scan.scanId;
            if (baselineTaken) {
              onScan(scan);
            }
          }
          baselineTaken = true;
        }
      } catch (failure) {
        if (!stopped && onFailure) {
          onFailure(failure);
        }
      }
      if (!stopped) {
        timer = setTimeout(tick, SCAN_POLL_MS);
      }
    }

    tick();
    return {
      stop() {
        stopped = true;
        clearTimeout(timer);
      },
    };
  }

  // Training only (story 008, DB-8): the Dummy Scanner records a scan as if
  // the code had been read. Resolves to {scanId, kind, code, scannedAt}.
  function simulateScan(kind, code) {
    return requestJson('POST', BASE + '/training/scanner/scans', { kind, code });
  }

  window.WeighingMS.scanner = { readStatus, readLatestScan, watchScans, simulateScan };
})();
