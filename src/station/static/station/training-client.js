// Training failure switches (story 008, DB-4, DB-7, DB-8, DB-9): the only JS
// file that knows the /training/modes paths. Training controls drive the
// Dummy APIs only; they are not part of any integration contract and would be
// removed together with the Dummies.
(function () {
  'use strict';

  const BASE = '/api/training/modes';
  const { requestJson } = window.WeighingMS.devices;

  window.WeighingMS.training = {
    // Resolves to {target: mode}, e.g. {orgatex: 'ok', 'scale-3kg': 'disconnected'}.
    readModes: () => requestJson('GET', BASE).then((d) => d.modes),
    setMode: (target, mode) =>
      requestJson('PUT', BASE + '/' + encodeURIComponent(target), { mode }).then(
        (d) => d.modes,
      ),
  };
})();
