// Device status for the status bar (FR-20, IR-13, IR-18), plus the shared
// DeviceError and request helper used by the device clients. Load this file
// before scale-client.js, scanner-client.js and printer-client.js.
// It knows no device paths: it asks each client for its status.
(function () {
  'use strict';

  const STATUS_POLL_MS = 1000; // a disconnection shows within 2 s (IR-13)

  class DeviceError extends Error {
    // kind: 'disconnected' | 'unavailable' | 'error' | 'rejected'
    constructor(kind, code, message) {
      super(message);
      this.name = 'DeviceError';
      this.kind = kind;
      this.code = code;
    }
  }

  const KIND_BY_CODE = {
    SCALE_DISCONNECTED: 'disconnected',
    SCANNER_UNAVAILABLE: 'unavailable',
    PRINTER_ERROR: 'error',
  };

  async function requestJson(method, url, body) {
    const options = { method, headers: { Accept: 'application/json' } };
    if (body !== undefined) {
      options.headers['Content-Type'] = 'application/json';
      options.body = JSON.stringify(body);
    }
    let response;
    try {
      response = await fetch(url, options);
    } catch (networkError) {
      throw new DeviceError('unavailable', 'DEVICE_UNREACHABLE', 'Device unavailable');
    }
    let data = null;
    try {
      data = await response.json();
    } catch (parseError) {
      throw new DeviceError('unavailable', 'MALFORMED_RESPONSE', 'Device unavailable');
    }
    if (response.ok) {
      return data;
    }
    const error = (data && data.error) || {};
    const code = error.code || 'HTTP_' + response.status;
    const kind = KIND_BY_CODE[code] || (response.status === 400 ? 'rejected' : 'unavailable');
    throw new DeviceError(kind, code, error.message || 'Device unavailable');
  }

  // Status bar devices: label, how to read the status, which states are valid.
  const DEVICES = {
    scale3kg: { label: 'SCALE 3 kg', read: (d) => d.scale.readStatus('scale-3kg') },
    scale32kg: { label: 'SCALE 32 kg', read: (d) => d.scale.readStatus('scale-32kg') },
    scanner: { label: 'SCANNER', read: (d) => d.scanner.readStatus() },
    printer: { label: 'PRINTER', read: (d) => d.printer.readStatus() },
  };
  const STATES = ['ready', 'disconnected', 'unavailable', 'error'];

  // Polls every device's status; a failed or unexpected answer is never 'ready'.
  function createDeviceStatus(onChange) {
    const devices = {};
    Object.keys(DEVICES).forEach((key) => {
      devices[key] = { label: DEVICES[key].label, state: 'unavailable', since: null };
    });
    let timer = null;
    let polling = false;

    function update(key, state) {
      const device = devices[key];
      if (device.state !== state || device.since === null) {
        device.state = state;
        device.since = new Date();
        return true;
      }
      return false;
    }

    async function poll() {
      if (polling) {
        return;
      }
      polling = true;
      const clients = window.WeighingMS;
      const results = await Promise.all(
        Object.keys(DEVICES).map(async (key) => {
          try {
            const status = await DEVICES[key].read(clients);
            return [key, STATES.includes(status) ? status : 'unavailable'];
          } catch (failure) {
            const kind = failure instanceof DeviceError ? failure.kind : 'unavailable';
            return [key, kind === 'rejected' ? 'unavailable' : kind];
          }
        }),
      );
      polling = false;
      const changed = results.map(([key, state]) => update(key, state)).some(Boolean);
      if (changed && onChange) {
        onChange(devices);
      }
    }

    return {
      devices,
      start() {
        if (timer === null) {
          poll();
          timer = setInterval(poll, STATUS_POLL_MS);
        }
      },
      stop() {
        clearInterval(timer);
        timer = null;
      },
      poll,
    };
  }

  window.WeighingMS = window.WeighingMS || {};
  window.WeighingMS.devices = { DeviceError, requestJson, createDeviceStatus };
})();
