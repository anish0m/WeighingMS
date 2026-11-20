// Printer browser client: the only JS file that knows the printer paths (IR-07).
// It calls the Dummy Printer training contract, not the real ticket printer.
// A ticket counts as printed only when the printer returns a ticket ID.
(function () {
  'use strict';

  const BASE = '/api';
  const { requestJson } = window.WeighingMS.devices;

  async function readStatus() {
    const data = await requestJson('GET', BASE + '/printer/status');
    return data.status;
  }

  // Resolves to {ticketId, content, batchId, printedAt}; rejects with a
  // DeviceError (kind 'error', code 'PRINTER_ERROR' when the printer fails).
  function printTicket(content, batchId) {
    const body = batchId ? { content, batchId } : { content };
    return requestJson('POST', BASE + '/tickets', body);
  }

  window.WeighingMS.printer = { readStatus, printTicket };
})();
