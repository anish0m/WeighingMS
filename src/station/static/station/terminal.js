// Operator terminal: Alpine.js view state for the header, status bar,
// View 1 · Select batch and View 2 · Weigh (weigh.js, merged in below). It
// holds no scenario data and applies no business rule (FR-21): operators,
// batches, recipes and device states come from the APIs through the
// per-integration clients; the server decides whether a batch opens
// (ADR-001), who the operator is (ADR-005) and every weighing step (ADR-008).
(function () {
  'use strict';

  const ORGATEX_CHECK_MS = 10000; // queue re-read = ORGATEX status (plan Decision 3)
  const CLOCK_MS = 1000;
  const STATE_TEXT = {
    ready: 'READY',
    disconnected: 'DISCONNECTED',
    unavailable: 'UNAVAILABLE',
    error: 'ERROR',
  };

  function pad(number) {
    return String(number).padStart(2, '0');
  }

  function hhmm(date) {
    return pad(date.getHours()) + ':' + pad(date.getMinutes());
  }

  function hhmmss(date) {
    return hhmm(date) + ':' + pad(date.getSeconds());
  }

  function terminal() {
    const api = window.WeighingMS;

    return Object.assign(api.weighView(), {
      view: 'loading', // 'loading' | 'operator' | 'queue' | 'weigh'
      clock: hhmmss(new Date()),
      operator: null,
      operators: [],
      queue: [],
      queueReceivedAt: '',
      queueError: '',
      message: '',
      busy: false,
      batch: null,
      recipe: null,
      devices: [],
      orgatex: { state: 'checking', at: '' },
      scanWatch: null,

      async init() {
        setInterval(() => {
          this.clock = hhmmss(new Date());
        }, CLOCK_MS);
        this.startDeviceStatus();
        await this.loadQueue();
        setInterval(() => this.loadQueue(), ORGATEX_CHECK_MS);
        await this.loadOperator();
      },

      // ── Operator (ADR-005) ──────────────────────────────────────────
      async loadOperator() {
        try {
          this.operator = await api.station.currentOperator();
        } catch (failure) {
          this.operator = null;
        }
        if (this.operator) {
          await this.resumeOrQueue();
        } else {
          await this.askOperator();
        }
      },

      // Resume (NFR-6): an open session reopens View 2 at its active
      // component; otherwise View 1 is shown.
      async resumeOrQueue() {
        let session = null;
        try {
          session = await api.station.currentSession();
        } catch (failure) {
          session = null;
        }
        if (!session) {
          this.showQueue();
          return;
        }
        let batch = { batchId: session.batchId };
        let recipe = null;
        try {
          batch = await api.orgatex.fetchBatch(session.batchId);
          recipe = await api.orgatex.fetchRecipe(session.batchId);
        } catch (failure) {
          this.queueError = failure.message || 'OrgaTEX unavailable';
        }
        await this.openWeigh(batch, recipe, session.sessionId);
      },

      async askOperator() {
        this.stopScanWatch();
        this.stopWeigh();
        this.operator = null;
        this.view = 'operator';
        try {
          this.operators = await api.station.listOperators();
          this.message = '';
        } catch (failure) {
          this.operators = [];
          this.message = failure.message;
        }
      },

      async chooseOperator(operatorId) {
        try {
          this.operator = await api.station.chooseOperator(operatorId);
          this.message = '';
          await this.resumeOrQueue();
        } catch (failure) {
          this.message = failure.message;
        }
      },

      // ── View 1 · Select batch ───────────────────────────────────────
      showQueue() {
        this.stopWeigh();
        this.view = 'queue';
        this.batch = null;
        this.recipe = null;
        this.startScanWatch();
      },

      async loadQueue() {
        try {
          const data = await api.orgatex.fetchQueue();
          this.queue = data.batches;
          this.queueReceivedAt = hhmm(new Date(data.receivedAt));
          this.queueError = '';
          this.orgatex = { state: 'linked', at: this.queueReceivedAt };
        } catch (failure) {
          this.queue = [];
          this.queueReceivedAt = '';
          this.queueError = failure.message || 'OrgaTEX unavailable';
          this.orgatex = { state: 'unavailable', at: '' };
        }
      },

      startScanWatch() {
        if (this.scanWatch) {
          return;
        }
        this.scanWatch = api.scanner.watchScans(
          (scan) => {
            if (scan.kind === 'batch' && this.view === 'queue') {
              this.select(scan.code, 'scan');
            } else if (scan.kind === 'dyestuff' && this.view === 'weigh') {
              this.onDyestuffScan(scan);
            }
          },
          () => {
            // The status bar shows the scanner failure; touch still works.
          },
        );
      },

      stopScanWatch() {
        if (this.scanWatch) {
          this.scanWatch.stop();
          this.scanWatch = null;
        }
      },

      // Server decides first (ADR-001); the browser then reads the batch and
      // recipe from OrgaTEX for display and opens view 2.
      async select(batchId, method) {
        if (this.busy) {
          return;
        }
        this.busy = true;
        this.message = '';
        try {
          const selection = await api.station.selectBatch(batchId, method);
          const session = await api.station.startSession(selection.selectionId);
          const batch = await api.orgatex.fetchBatch(selection.batch.batchId);
          const recipe = await api.orgatex.fetchRecipe(selection.batch.batchId);
          await this.openWeigh(batch, recipe, session.sessionId);
        } catch (failure) {
          if (failure.code === 'OPERATOR_REQUIRED') {
            await this.askOperator();
          }
          this.message = failure.message || 'OrgaTEX unavailable';
        } finally {
          this.busy = false;
        }
      },

      // ── View 2 · Weigh (weigh.js) ───────────────────────────────────
      // The scanner keeps being watched: View 2 takes dyestuff scans.
      async openWeigh(batch, recipe, sessionId) {
        this.batch = batch;
        this.recipe = recipe;
        this.view = 'weigh';
        this.startScanWatch();
        await this.openSession(sessionId);
      },

      // ── Status bar ──────────────────────────────────────────────────
      startDeviceStatus() {
        const status = api.devices.createDeviceStatus((devices) => {
          this.devices = Object.keys(devices).map((key) => ({
            key,
            label: devices[key].label,
            state: devices[key].state,
          }));
        });
        this.devices = Object.keys(status.devices).map((key) => ({
          key,
          label: status.devices[key].label,
          state: status.devices[key].state,
        }));
        status.start();
      },

      deviceText(device) {
        return device.label + ' · ' + (STATE_TEXT[device.state] || 'UNAVAILABLE');
      },

      orgatexText() {
        if (this.orgatex.state === 'linked') {
          return 'ORGATEX · LINKED ' + this.orgatex.at;
        }
        if (this.orgatex.state === 'checking') {
          return 'ORGATEX · CHECKING';
        }
        return 'ORGATEX · UNAVAILABLE';
      },
    });
  }

  window.terminal = terminal;
})();
