// WeighingMS station API client: the only JS file that knows the
// /station/api/ paths (ADR-002). The server is the authority for selection
// (ADR-001), the current operator (ADR-005) and every weighing decision
// (ADR-008, ADR-010); this client only sends requests and reports the
// server's answer.
(function () {
  'use strict';

  const BASE = '/station/api';

  class StationError extends Error {
    // code: the server's error code (e.g. BATCH_NOT_FOUND, OPERATOR_REQUIRED);
    // message: the text to show the operator.
    constructor(status, code, message) {
      super(message);
      this.name = 'StationError';
      this.status = status;
      this.code = code;
    }
  }

  function csrfToken() {
    const meta = document.querySelector('meta[name="csrf-token"]');
    return meta ? meta.content : '';
  }

  async function request(method, path, body) {
    const options = { method, headers: { Accept: 'application/json' } };
    if (method !== 'GET') {
      options.headers['X-CSRFToken'] = csrfToken();
    }
    if (body !== undefined) {
      options.headers['Content-Type'] = 'application/json';
      options.body = JSON.stringify(body);
    }
    let response;
    try {
      response = await fetch(BASE + path, options);
    } catch (networkError) {
      throw new StationError(0, 'STATION_UNREACHABLE', 'WeighingMS unavailable');
    }
    if (response.status === 204) {
      return null;
    }
    let data = null;
    try {
      data = await response.json();
    } catch (parseError) {
      data = null;
    }
    if (response.ok && data !== null) {
      return data;
    }
    const error = (data && data.error) || {};
    throw new StationError(
      response.status,
      error.code || 'HTTP_' + response.status,
      error.message || 'WeighingMS unavailable',
    );
  }

  function sessionPath(sessionId) {
    return '/sessions/' + encodeURIComponent(sessionId);
  }

  function componentPath(sessionId, sequence, action) {
    return sessionPath(sessionId) + '/components/' + encodeURIComponent(sequence) + '/' + action;
  }

  // OrgaTEX write-back (bolt 014, FR-17): the server supplies the body and the
  // idempotency key, the OrgaTEX client posts it, and the server decides the
  // status by reading OrgaTEX itself. Resolves to the server's writeBack.
  async function writeBack(sessionId) {
    const path = sessionPath(sessionId) + '/write-back';
    const started = await request('POST', path, {});
    if (started.writeBack.status === 'confirmed') {
      return started.writeBack;
    }
    let report;
    try {
      await window.WeighingMS.orgatex.postConsumption(started.batchId, started.body);
      report = { posted: true, reason: '' };
    } catch (error) {
      report = { posted: false, reason: error.message || 'OrgaTEX unavailable' };
    }
    const result = await request('POST', path + '/result', report);
    return result.writeBack;
  }

  window.WeighingMS = window.WeighingMS || {};
  window.WeighingMS.station = {
    StationError,
    listOperators: () => request('GET', '/operators').then((d) => d.operators),
    currentOperator: () => request('GET', '/operator').then((d) => d.operator),
    chooseOperator: (operatorId) =>
      request('PUT', '/operator', { operatorId }).then((d) => d.operator),
    selectBatch: (batchId, method) => request('POST', '/selections', { batchId, method }),
    startSession: (selectionId) => request('POST', '/sessions', { selectionId }),
    // View 2 · Weigh (bolt 011)
    currentSession: () => request('GET', '/current-session').then((d) => d.session),
    progress: (sessionId) => request('GET', sessionPath(sessionId) + '/progress'),
    sessionComponents: (sessionId) =>
      request('GET', sessionPath(sessionId) + '/components').then((d) => d.components),
    // net and unit are the scale's decimal strings, passed on unchanged.
    evaluate: (sessionId, sequence, net, unit) =>
      request(
        'GET',
        componentPath(sessionId, sequence, 'evaluation') +
          '?net=' + encodeURIComponent(net) + '&unit=' + encodeURIComponent(unit),
      ),
    verifyIdentity: (sessionId, sequence, scanId) =>
      request('POST', componentPath(sessionId, sequence, 'identity'), { scanId }),
    // activate, tare, quit resolve to the session progress; confirm resolves
    // to {record, progress}.
    activate: (sessionId, sequence) =>
      request('POST', componentPath(sessionId, sequence, 'activate'), {}),
    tare: (sessionId, sequence) =>
      request('POST', componentPath(sessionId, sequence, 'tare'), {}),
    quit: (sessionId, sequence) =>
      request('POST', componentPath(sessionId, sequence, 'quit'), {}),
    confirm: (sessionId, sequence) =>
      request('POST', componentPath(sessionId, sequence, 'confirm'), {}),
    // OrgaTEX write-back (bolt 014)
    writeBackStatus: (sessionId) =>
      request('GET', sessionPath(sessionId) + '/write-back').then((d) => d.writeBack),
    writeBack,
  };
})();
