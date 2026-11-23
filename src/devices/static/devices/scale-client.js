// Scale browser client: the only JS file that knows the scale paths (IR-07).
// It calls the Dummy Scale training contract, not the real indicator (A-05).
// Weights stay decimal strings; the browser does no arithmetic on them.
(function () {
  'use strict';

  const BASE = '/api';
  const TRAINING = '/api/training';
  const WEIGHT_POLL_MS = 200; // 5 Hz live weight (NFR-1)
  const { requestJson } = window.WeighingMS.devices;

  function scalePath(scaleId, action) {
    return BASE + '/scales/' + encodeURIComponent(scaleId) + '/' + action;
  }

  async function readStatus(scaleId) {
    const data = await requestJson('GET', scalePath(scaleId, 'status'));
    return data.status;
  }

  // Polls only the given scale until stop() is called. Each reading goes to
  // onReading({scaleId, netWeight, unit, status, readAt}); each failure goes
  // to onFailure(DeviceError) and polling continues, so recovery shows up.
  function watchWeight(scaleId, onReading, onFailure) {
    let stopped = false;
    let timer = null;

    async function tick() {
      const started = Date.now();
      try {
        const reading = await requestJson('GET', scalePath(scaleId, 'weight'));
        if (!stopped) {
          onReading(reading);
        }
      } catch (failure) {
        if (!stopped && onFailure) {
          onFailure(failure);
        }
      }
      if (!stopped) {
        timer = setTimeout(tick, Math.max(0, WEIGHT_POLL_MS - (Date.now() - started)));
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

  // Training only (story 008, DB-6): drive the Dummy Scale like the
  // prototype's buttons. body: {action: 'dispense' | 'overshoot', target,
  // tolerance, unit} | {action: 'set', weight, unit} | {action: 'reset'}.
  // The Dummy calculates the landing weight; the browser does not.
  function simulate(scaleId, body) {
    return requestJson(
      'POST',
      TRAINING + '/scales/' + encodeURIComponent(scaleId) + '/simulate',
      body,
    );
  }

  window.WeighingMS.scale = {
    readWeight: (scaleId) => requestJson('GET', scalePath(scaleId, 'weight')),
    readStatus,
    tare: (scaleId) => requestJson('POST', scalePath(scaleId, 'tare')),
    watchWeight,
    simulate,
  };
})();
