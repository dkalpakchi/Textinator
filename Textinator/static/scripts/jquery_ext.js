(function ($) {
  $.fn.serializeObject = function () {
    let o = {};
    let a = this.serializeArray();
    $.each(a, function () {
      if (o[this.name] === undefined) {
        o[this.name] = [];
      }
      o[this.name].push(this.value || "");
    });
    return o;
  };
})(window.$);
