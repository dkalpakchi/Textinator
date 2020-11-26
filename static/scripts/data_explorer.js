$(document).ready(function() {
  $("[id^=item-context-]").accordion({
    collapsible: true,
    active: false
  });

  $("#flaggedCollapse").accordion({
    collapsible: true,
    active: false,
    icons: false,
    
  });
})