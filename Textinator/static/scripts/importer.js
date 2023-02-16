(function () {
  const utils = {
    mime: {
      json: "application/json",
    },
  };

  const ui = {
    widgets: {
      fileLoader: null,
    },
    init: function () {
      this.widgets.fileLoader = document.querySelector(
        'input[type="file"]#dataSourceFile'
      );
      this.initEvents();
    },
    initEvents: function () {
      this.widgets.fileLoader.addEventListener(
        "change",
        function (e) {
          let target = e.target;
          let files = target.files;

          for (let i = 0, len = files.length; i < len; i++) {
            if (files[i].type == utils.mime.json) {
              importer.importFromJsonFile(files[i]);
              break;
            }
          }
        },
        false
      );

      document.addEventListener(importer.events.enq, function (e) {
        console.log(e.detail);
      });
    },
  };

  const importer = {
    queue: [],
    events: {
      enq: "ENQUEUE",
    },
    init: function () {
      ui.init();
    },
    importFromJsonFile: function (f) {
      let ctx = this;
      const fr = new FileReader();
      fr.addEventListener("load", function () {
        let item = JSON.parse(fr.result);
        ctx.queue.push(item);
        const enqEvent = new CustomEvent(ctx.events.enq, { detail: item });
        document.dispatchEvent(enqEvent);
      });

      fr.readAsText(f);
    },
    getLatest: function () {
      return this.queue[this.queue.length - 1];
    },
  };

  document.addEventListener(
    "DOMContentLoaded",
    function () {
      importer.init();
      window.ui = ui;
    },
    false
  );
})();
