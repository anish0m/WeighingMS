// View 3 · Confirm & print (bolt 017): the completed batch's summary, the
// OrgaTEX write-back status with Retry, the ticket preview and the F1 / F3
// keys. Merged into the terminal() Alpine component by terminal.js.
//
// Every value is the server's: the summary (bolt 015), the write-back status
// decided by the server after its own OrgaTEX read (bolt 014) and the ticket
// text and print result decided after its own printer read (bolt 016). The
// browser only formats the write-back time as hh:mm:ss.
(function () {
  'use strict';

  const DONE_KEY = 'weighingms.completedSession';

  function pad(number) {
    return String(number).padStart(2, '0');
  }

  function hhmmss(iso) {
    const date = new Date(iso);
    return pad(date.getHours()) + ':' + pad(date.getMinutes()) + ':' + pad(date.getSeconds());
  }

  function doneView() {
    const api = window.WeighingMS;

    return {
      done: null, // {summary, writeBack} of the completed session
      ticket: null, // ticket preview {content, reprint, printed, jobs}
      writing: false,
      printing: false,
      printMessage: '',
      printFailed: false,
      doneMessage: '',

      // ── Open ────────────────────────────────────────────────────────
      // From the last confirm's `completion`, or from GET summary on reload.
      async openDone(sessionId, completion) {
        this.stopWeigh();
        this.done = completion;
        this.ticket = null;
        this.printMessage = '';
        this.printFailed = false;
        this.doneMessage = '';
        this.view = 'done';
        this.rememberDone(sessionId);
        await this.loadTicket();
        if (!this.writeBackConfirmed()) {
          await this.writeBack();
        }
      },

      // Reload (plan Decision 2): reopen View 3 until Next batch.
      async resumeDone() {
        const sessionId = this.rememberedDone();
        if (!sessionId) {
          return false;
        }
        try {
          const completion = await api.station.summary(sessionId);
          try {
            // Header crumb and machine, read from OrgaTEX for display only.
            this.batch = await api.orgatex.fetchBatch(completion.summary.batchId);
          } catch (unavailable) {
            this.batch = { batchId: completion.summary.batchId };
          }
          await this.openDone(sessionId, completion);
          return true;
        } catch (failure) {
          this.forgetDone();
          return false;
        }
      },

      rememberDone(sessionId) {
        try {
          window.sessionStorage.setItem(DONE_KEY, String(sessionId));
        } catch (ignored) {
          // Without storage, a reload shows the queue.
        }
      },

      rememberedDone() {
        try {
          return window.sessionStorage.getItem(DONE_KEY);
        } catch (ignored) {
          return null;
        }
      },

      forgetDone() {
        try {
          window.sessionStorage.removeItem(DONE_KEY);
        } catch (ignored) {
          // Nothing remembered.
        }
      },

      doneSessionId() {
        return this.done ? this.done.summary.sessionId : null;
      },

      // ── Written to OrgaTEX (bolt 014) ───────────────────────────────
      writeBackConfirmed() {
        return Boolean(this.done && this.done.writeBack && this.done.writeBack.status === 'confirmed');
      },

      writeBackNotWritten() {
        return Boolean(
          !this.writing && this.done && this.done.writeBack &&
            this.done.writeBack.status === 'not_written',
        );
      },

      writeBackText() {
        if (this.writeBackConfirmed()) {
          return 'CONFIRMED ' + hhmmss(this.done.writeBack.confirmedAt);
        }
        if (this.writeBackNotWritten()) {
          return 'NOT WRITTEN';
        }
        return 'WRITING…';
      },

      async writeBack() {
        if (this.writing || !this.done) {
          return;
        }
        this.writing = true;
        this.doneMessage = '';
        try {
          this.done.writeBack = await api.station.writeBack(this.doneSessionId());
        } catch (failure) {
          this.doneMessage = failure.message || 'WeighingMS unavailable';
          try {
            this.done.writeBack = await api.station.writeBackStatus(this.doneSessionId());
          } catch (ignored) {
            // Keep the last known status.
          }
        } finally {
          this.writing = false;
        }
      },

      retryWriteBack() {
        if (this.writeBackNotWritten()) {
          this.writeBack();
        }
      },

      // ── Ticket (bolt 016) ───────────────────────────────────────────
      async loadTicket() {
        try {
          this.ticket = await api.station.ticketPreview(this.doneSessionId());
        } catch (failure) {
          this.ticket = null;
          this.printMessage = failure.message || 'Ticket unavailable';
          this.printFailed = true;
        }
      },

      async printTicket() {
        if (this.printing || !this.done) {
          return;
        }
        this.printing = true;
        this.printMessage = '';
        this.printFailed = false;
        try {
          const job = await api.station.printTicket(this.doneSessionId());
          if (job.status === 'printed') {
            this.printMessage = (job.reprint ? 'REPRINT printed ' : 'Ticket printed ') +
              hhmmss(job.printedAt);
          } else {
            this.printMessage = job.reason || 'Printer error: ticket not printed';
            this.printFailed = true;
          }
        } catch (failure) {
          this.printMessage = failure.message || 'Printer error: ticket not printed';
          this.printFailed = true;
        } finally {
          this.printing = false;
        }
        await this.loadTicket();
      },

      // ── Next batch F3 ───────────────────────────────────────────────
      nextBatch() {
        this.forgetDone();
        this.done = null;
        this.ticket = null;
        this.printMessage = '';
        this.doneMessage = '';
        this.showQueue();
      },
    };
  }

  window.WeighingMS = window.WeighingMS || {};
  window.WeighingMS.doneView = doneView;
})();
