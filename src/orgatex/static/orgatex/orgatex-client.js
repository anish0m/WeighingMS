// OrgaTEX browser client: the only JS file that knows the OrgaTEX paths (IR-07).
// It calls the Dummy OrgaTEX training contract over HTTP; that contract is
// defined by this project and is not the real OrgaTEX interface.
// Quantities stay decimal strings; the browser does no arithmetic on them.
(function () {
  'use strict';

  const BASE = '/api';

  class OrgatexError extends Error {
    // kind: 'not-found' (batch or recipe missing) or 'unavailable'.
    constructor(kind, code, message) {
      super(message);
      this.name = 'OrgatexError';
      this.kind = kind;
      this.code = code;
    }
  }

  async function errorBody(response) {
    try {
      const body = await response.json();
      if (body && body.error && body.error.code) {
        return body.error;
      }
    } catch (ignored) {
      // Not the contract's error body; handled as unavailable below.
    }
    return null;
  }

  async function get(path) {
    let response;
    try {
      response = await fetch(BASE + path, { headers: { Accept: 'application/json' } });
    } catch (networkError) {
      throw new OrgatexError('unavailable', 'ORGATEX_UNREACHABLE', 'OrgaTEX unavailable');
    }
    if (response.ok) {
      try {
        return await response.json();
      } catch (parseError) {
        throw new OrgatexError('unavailable', 'MALFORMED_RESPONSE', 'OrgaTEX unavailable');
      }
    }
    const error = await errorBody(response);
    if (response.status === 404 && error) {
      throw new OrgatexError('not-found', error.code, error.message);
    }
    const code = error ? error.code : 'HTTP_' + response.status;
    throw new OrgatexError('unavailable', code, 'OrgaTEX unavailable');
  }

  function batchPath(batchId) {
    return '/batches/' + encodeURIComponent(batchId);
  }

  window.WeighingMS = window.WeighingMS || {};
  window.WeighingMS.orgatex = {
    OrgatexError,
    fetchQueue: () => get('/batches'),
    fetchBatch: (batchId) => get(batchPath(batchId)),
    fetchRecipe: (batchId) => get(batchPath(batchId) + '/recipe'),
  };
})();
