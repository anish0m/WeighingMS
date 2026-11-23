// Training panel (story 008): the prototype's Simulate dispense / overshoot /
// Reset, an exact weight, a simulated dyestuff scan and the failure switches.
// TRAINING ONLY: it drives the Dummy APIs, sits outside the operator screen
// and would be removed together with the Dummies. It follows the active
// component through the 'weigh-active' window event sent by View 2; the
// landing weights are calculated by the Dummy Scale, not here.
(function () {
  'use strict';

  // The failure mode each Dummy offers; anything not listed is a scale.
  const FAILURE_MODE = { orgatex: 'unavailable', scanner: 'unavailable', printer: 'error' };
  const SCALE_FAILURE = 'disconnected';

  function trainingPanel() {
    const api = window.WeighingMS;

    return {
      active: null, // {sequence, code, unit, scaleId, target, tolerance}
      modes: {}, // {target: mode} from the Dummies
      weight: '',
      scanCode: '',
      message: '',

      async init() {
        await this.loadModes();
      },

      onActive(detail) {
        const changed = !detail || !this.active || detail.sequence !== this.active.sequence;
        this.active = detail;
        if (changed) {
          this.scanCode = detail ? detail.code : '';
          this.weight = '';
        }
      },

      // ── Dummy Scale ─────────────────────────────────────────────────
      dispense() {
        this.simulate('dispense');
      },

      overshoot() {
        this.simulate('overshoot');
      },

      reset() {
        this.simulate('reset');
      },

      setWeight() {
        this.simulate('set');
      },

      async simulate(action) {
        if (!this.active) {
          return;
        }
        const { scaleId, unit, target, tolerance } = this.active;
        const bodies = {
          dispense: { action, target, tolerance, unit },
          overshoot: { action, target, tolerance, unit },
          reset: { action },
          set: { action, weight: this.weight, unit },
        };
        await this.attempt(() => api.scale.simulate(scaleId, bodies[action]));
      },

      // ── Dummy Scanner ───────────────────────────────────────────────
      async scan() {
        if (this.scanCode) {
          await this.attempt(() => api.scanner.simulateScan('dyestuff', this.scanCode));
        }
      },

      // ── Failure switches ────────────────────────────────────────────
      targets() {
        return Object.keys(this.modes);
      },

      failureMode(target) {
        return FAILURE_MODE[target] || SCALE_FAILURE;
      },

      isFailing(target) {
        return this.modes[target] !== 'ok';
      },

      switchText(target) {
        return target.toUpperCase() + ' · ' + this.failureMode(target).toUpperCase();
      },

      async toggle(target) {
        const mode = this.isFailing(target) ? 'ok' : this.failureMode(target);
        await this.attempt(async () => {
          this.modes = await api.training.setMode(target, mode);
        });
      },

      async loadModes() {
        await this.attempt(async () => {
          this.modes = await api.training.readModes();
        });
      },

      async attempt(call) {
        try {
          await call();
          this.message = '';
        } catch (failure) {
          this.message = failure.message || 'Dummy unavailable';
        }
      },
    };
  }

  window.trainingPanel = trainingPanel;
})();
