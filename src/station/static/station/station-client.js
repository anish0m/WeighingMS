// WeighingMS station API client: the only JS file that knows the
// /station/api/ paths (ADR-002). The server is the authority for selection
// (ADR-001) and for the current operator (ADR-005); this client only sends
// requests and reports the server's answer.
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

  window.WeighingMS = window.WeighingMS || {};
  window.WeighingMS.station = {
    StationError,
    listOperators: () => request('GET', '/operators').then((d) => d.operators),
    currentOperator: () => request('GET', '/operator').then((d) => d.operator),
    chooseOperator: (operatorId) =>
      request('PUT', '/operator', { operatorId }).then((d) => d.operator),
    selectBatch: (batchId, method) => request('POST', '/selections', { batchId, method }),
    startSession: (selectionId) => request('POST', '/sessions', { selectionId }),
  };
})();
