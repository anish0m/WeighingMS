// View 2 · Weigh (bolt 011): recipe rail, component header, scan dyestuff
// step, live readout, tolerance bar, status line and the F1 / F2 / F4 keys.
// Merged into the terminal() Alpine component by terminal.js.
//
// The server makes every weighing decision (ADR-008, ADR-010, ADR-011): the
// zone, still to weigh, whether OK is allowed, the scale, tare, the record
// and the next component. This file only shows the APIs' answers and does no
// arithmetic on quantities (NFR-16, FR-21); weights stay decimal strings.
(function () {
  'use strict';

  const KEY_ACTIONS = { F1: 'confirmWeighing', F2: 'retare', F4: 'quitComponent' };

  function weighView() {
    const api = window.WeighingMS;

    return {
      session: null, // progress JSON: weighed, total, progressText, active, components
      components: [], // component JSON: header, identity, rules, bar
      reading: null, // last scale reading {netWeight, unit}
      evaluation: null, // evaluation JSON of the last reading
      scaleFault: '', // device message while the active scale fails
      weighMessage: '', // the server's answer to the last action or scan
      weighBusy: false,
      scaleWatch: null,
      watchedScaleId: null,
      evaluating: false,
      evaluateAgain: false,
      heldScan: null, // a dyestuff scan that arrived while a request was running

      // ── Session ─────────────────────────────────────────────────────
      // Opens the session at its active component; with none active, the
      // first pending component is activated (and tared by the server).
      async openSession(sessionId) {
        this.weighMessage = '';
        this.weighBusy = true;
        try {
          let progress = await api.station.progress(sessionId);
          if (!progress.active && progress.nextPending) {
            progress = await api.station.activate(sessionId, progress.nextPending);
          }
          await this.applyProgress(progress);
        } catch (failure) {
          this.weighFailure(failure);
        } finally {
          this.endBusy();
        }
      },

      // Components are read first, so the rail, header and training panel
      // switch to the new state together.
      async applyProgress(progress) {
        const components = await api.station.sessionComponents(progress.sessionId);
        this.session = progress;
        this.components = components;
        if (!this.activeSequence() || !this.evaluation ||
            this.evaluation.sequence !== this.activeSequence()) {
          this.evaluation = null;
        }
        this.watchActiveScale();
        this.announceActive();
        this.evaluateReading();
      },

      async reloadComponents() {
        if (this.session) {
          this.components = await api.station.sessionComponents(this.session.sessionId);
        }
      },

      stopWeigh() {
        this.stopScaleWatch();
        this.heldScan = null;
        this.session = null;
        this.components = [];
        this.evaluation = null;
        this.reading = null;
        this.announceActive();
      },

      // ── Lookups for the template ────────────────────────────────────
      activeSequence() {
        return this.session && this.session.active ? this.session.active.sequence : null;
      },

      activeComponent() {
        const sequence = this.activeSequence();
        return this.components.find((c) => c.sequence === sequence) || null;
      },

      progressOf(sequence) {
        if (!this.session) {
          return null;
        }
        return this.session.components.find((c) => c.sequence === sequence) || null;
      },

      rowState(sequence) {
        const progress = this.progressOf(sequence);
        return progress ? progress.state : 'pending';
      },

      isTared() {
        return Boolean(this.session && this.session.active && this.session.active.tared);
      },

      needsScan() {
        const component = this.activeComponent();
        return Boolean(component && component.identity.status !== 'verified');
      },

      zone() {
        return this.evaluation ? this.evaluation.zone : 'under';
      },

      canConfirm() {
        const component = this.activeComponent();
        return Boolean(
          !this.weighBusy &&
            component &&
            component.materialReady &&
            this.isTared() &&
            !this.scaleFault &&
            this.evaluation &&
            this.evaluation.sequence === component.sequence &&
            this.evaluation.withinTolerance,
        );
      },

      // ── Live readout ────────────────────────────────────────────────
      watchActiveScale() {
        const component = this.activeComponent();
        const scaleId = component ? component.scale.scaleId : null;
        if (scaleId === this.watchedScaleId) {
          return;
        }
        this.stopScaleWatch();
        if (!scaleId) {
          return;
        }
        this.watchedScaleId = scaleId;
        this.scaleWatch = api.scale.watchWeight(
          scaleId,
          (reading) => this.onReading(reading),
          (failure) => {
            this.scaleFault = failure.message || 'Scale unavailable';
            this.reading = null;
            this.evaluation = null;
          },
        );
      },

      stopScaleWatch() {
        if (this.scaleWatch) {
          this.scaleWatch.stop();
        }
        this.scaleWatch = null;
        this.watchedScaleId = null;
        this.scaleFault = '';
      },

      onReading(reading) {
        this.scaleFault = '';
        const same =
          this.reading &&
          this.reading.netWeight === reading.netWeight &&
          this.reading.unit === reading.unit;
        this.reading = reading;
        if (!same || !this.evaluation) {
          this.evaluateReading();
        }
      },

      // At most one evaluation request is in flight; the latest reading wins.
      async evaluateReading() {
        const component = this.activeComponent();
        if (!component || !this.reading) {
          return;
        }
        if (this.evaluating) {
          this.evaluateAgain = true;
          return;
        }
        this.evaluating = true;
        try {
          const reading = this.reading;
          const evaluation = await api.station.evaluate(
            this.session.sessionId,
            component.sequence,
            reading.netWeight,
            reading.unit,
          );
          if (evaluation.sequence === this.activeSequence()) {
            this.evaluation = evaluation;
          }
        } catch (failure) {
          this.evaluation = null;
        } finally {
          this.evaluating = false;
        }
        if (this.evaluateAgain) {
          this.evaluateAgain = false;
          this.evaluateReading();
        }
      },

      // ── Rail ────────────────────────────────────────────────────────
      // A done or active row does nothing; a pending row is activated.
      touchRow(sequence) {
        if (this.rowState(sequence) !== 'pending') {
          return;
        }
        this.runAction(() => api.station.activate(this.session.sessionId, sequence));
      },

      // ── Scan dyestuff step (OQ-8) ───────────────────────────────────
      // The scanner reports each scan once, so a scan that arrives while a
      // request is running is held and checked when that request ends.
      async onDyestuffScan(scan) {
        if (this.weighBusy) {
          this.heldScan = scan;
          return;
        }
        const component = this.activeComponent();
        if (!component || !this.needsScan()) {
          return;
        }
        this.weighBusy = true;
        try {
          const check = await api.station.verifyIdentity(
            this.session.sessionId,
            component.sequence,
            scan.scanId,
          );
          this.weighMessage = check.result === 'verified' ? '' : check.message;
          await this.reloadComponents();
        } catch (failure) {
          this.weighFailure(failure);
        } finally {
          this.endBusy();
        }
      },

      endBusy() {
        this.weighBusy = false;
        const held = this.heldScan;
        this.heldScan = null;
        if (held) {
          this.onDyestuffScan(held);
        }
      },

      // ── Actions: OK · Confirm F1, Re-tare F2, Quit F4 ───────────────
      confirmWeighing() {
        if (!this.canConfirm()) {
          return;
        }
        const sequence = this.activeSequence();
        this.runAction(async () => {
          const result = await api.station.confirm(this.session.sessionId, sequence);
          return result.progress;
        });
      },

      retare() {
        const sequence = this.activeSequence();
        if (sequence) {
          this.runAction(() => api.station.tare(this.session.sessionId, sequence));
        }
      },

      quitComponent() {
        const sequence = this.activeSequence();
        if (sequence) {
          this.runAction(() => api.station.quit(this.session.sessionId, sequence));
        }
      },

      async runAction(call) {
        if (this.weighBusy || !this.session) {
          return;
        }
        this.weighBusy = true;
        this.weighMessage = '';
        try {
          const progress = await call();
          this.evaluation = null;
          await this.applyProgress(progress);
        } catch (failure) {
          this.weighFailure(failure);
        } finally {
          this.endBusy();
        }
      },

      weighFailure(failure) {
        if (failure.code === 'OPERATOR_REQUIRED') {
          this.askOperator();
        }
        this.weighMessage = failure.message || 'WeighingMS unavailable';
      },

      // F1 / F2 / F4 run exactly what the buttons run (NFR-9).
      onKey(event) {
        const action = KEY_ACTIONS[event.key];
        if (!action || this.view !== 'weigh') {
          return;
        }
        event.preventDefault();
        this[action]();
      },

      // The training panel (outside the operator screen) follows the active
      // component through this event; the operator screen never reads it back.
      announceActive() {
        const component = this.activeComponent();
        window.dispatchEvent(
          new CustomEvent('weigh-active', {
            detail: component && {
              sequence: component.sequence,
              code: component.code,
              unit: component.scale.unit,
              scaleId: component.scale.scaleId,
              target: component.target,
              tolerance: component.tolerance.tolerance,
            },
          }),
        );
      },
    };
  }

  window.WeighingMS = window.WeighingMS || {};
  window.WeighingMS.weighView = weighView;
})();
