$(document).ready(function() {
  var chunks = [],
      selectorArea = document.querySelector('.selector'),
      resetTextHTML = selectorArea.innerHTML,
      resetText = selectorArea.innerHTML.replace(/<br>/gi, '\n'),
      contextSize = $('#taskArea').data('context');

  function previousTextLength(node) {
    var len = 0;
    var prev = node.previousSibling;
    while (prev != null) {
      if (prev.nodeType == 1) {
        if (prev.tagName == "BR") {
          len += 1
        }
      } else if (prev.nodeType == 3) {
        len += prev.length
      }
      prev = prev.previousSibling
    }
    return len;
  }

  function mergeWithNeighbors(node) {
    // check if text node
    var next = node.nextSibling,
        prev = node.previousSibling,
        parent = node.parentNode;

    if (prev.nodeType == 3 && next.nodeType == 3) {
      parent.replaceChild(document.createTextNode(prev.data + node.textContent + next.data), prev);
      parent.removeChild(node);
      parent.removeChild(next);
    } else if (prev.nodeType == 3) {
      parent.replaceChild(document.createTextNode(prev.data + node.textContent), prev);
      parent.removeChild(node);
    } else if (next.nodeType == 3) {
      parent.replaceChild(document.createTextNode(node.textContent + next.data), node);
      parent.removeChild(next);
    }
  }

  function removeAllChildren(node) {
    while (node.firstChild) {
      node.removeChild(node.firstChild);
    }
  }

  function resetArticle() {
    var node = document.querySelector('.selector');
    removeAllChildren(node);
    node.innerHTML = resetTextHTML;
  }

  $('.marker.tag').on('click', function() {
    var chunk = chunks[chunks.length - 1],
        idc = chunks.length - 1
        cls = this.className.split(' ').filter(c => c != 'marker').join(' '),
        leftTextNode = document.createTextNode(chunk['text'].slice(0, chunk['start'])),
        markedSpan = document.createElement('span'),
        deleteMarkedBtn = document.createElement('button'),
        rightTextNode = document.createTextNode(chunk['text'].slice(chunk['end'])),
        parent = chunk['node'].parentNode;
    markedSpan.className = cls + " is-medium";
    markedSpan.textContent = chunk['text'].slice(chunk['start'], chunk['end']);
    deleteMarkedBtn.className = 'delete is-small';
    deleteMarkedBtn.addEventListener('click', function(e) {
      e.stopPropagation();
      var el = e.target,
          parent = el.parentNode; // actual span

      delete chunks[idc];
      mergeWithNeighbors(parent);
      window.chunks = chunks;
    }, true);
    markedSpan.appendChild(deleteMarkedBtn)

    parent.replaceChild(leftTextNode, chunk['node']);
    parent.insertBefore(markedSpan, leftTextNode.nextSibling);
    parent.insertBefore(rightTextNode, markedSpan.nextSibling);
    chunk['marked'] = true;
    chunk['label'] = this.textContent;
    delete chunk['node']
    window.chunks = chunks;
  });

  $('.selector').on('mouseup', function(e) {
    var isRightMB;
    e = e || window.event;

    if ("which" in e)  // Gecko (Firefox), WebKit (Safari/Chrome) & Opera
        isRightMB = e.which == 3; 
    else if ("button" in e)  // IE, Opera 
        isRightMB = e.button == 2; 

    if (!$(e.target).hasClass('delete') && !isRightMB) {
      var selection = window.getSelection(),
          chunk = {};
      chunk['node'] = selection.anchorNode;
      chunk['text'] = selection.anchorNode.data;
      if (selection.anchorOffset > selection.focusOffset) {
        chunk['start'] = selection.focusOffset;
        chunk['end'] = selection.anchorOffset;
      } else {
        chunk['start'] = selection.anchorOffset;
        chunk['end'] = selection.focusOffset;
      }
      if (contextSize == 'p') {
        // paragraph
        chunk['context'] = chunk['text']
        chunk['lengthBefore'] = 0;
      } else if (contextSize == 't') {
        // text
        chunk['context'] = $('.selector').html().replace(/<br>/gi, '\n');
        chunk['lengthBefore'] = previousTextLength(selection.anchorNode);
      } else if (contextSize == 's') {
        // TODO sentence

      } else if (contextSize == 'no') {
        chunk['context'] = null;
        chunk['lengthBefore'] = null;
      } else {
        // not implemented
        console.error("Context size " + contextSize + " is not implemented");
        return;
      }

      chunk['marked'] = false;
      chunk['label'] = null;

      if (chunks.length == 0 || (chunks.length > 0 && chunks[chunks.length - 1]['marked'])) {
        chunks.push(chunk);
      } else {
        chunks[chunks.length - 1] = chunk;
      }
    }
  })

  $('#inputForm .submit.button').on('click', function(e) {
    e.preventDefault();

    var $inputForm = $('#inputForm'),
        $qInput = $inputForm.find('input.question'),
        inputFormData = $inputForm.serializeObject();
    inputFormData['chunks'] = JSON.stringify(chunks);

    $.ajax({
      method: "POST",
      url: inputForm.action,
      dataType: "json",
      data: inputFormData,
      success: function(data) {
        console.log("SUCCESS!")
        if (data['error'] == false) {
          var curLevel = $.trim($('.tt-level .tt-header').text()).split(' ')[1]
          if (curLevel != data['level']) {
            $('.tt-label').html(data['next_level_points'] - data['level_points'] + '<span class="smaller">p</span>');
          }
          var ratio = Math.round((data['points'] - data['level_points']) * 100 / (data['next_level_points'] - data['level_points']));
          if (ratio >= 100) {
            ratio -= 100;
          }
          var $pie = $('.tt-pie-wrapper');
          $pie.removeClass(function (index, className) {
            return (className.match(/(^|\s)progress-\S+/g) || []).join(' ');
          });
          $pie.addClass('progress-' + ratio);
          $('#leaderboard').html(data['leaderboard_template']);
          $qInput.val('');
          $qInput.focus();
        }
        chunks = [];
      },
      error: function() {
        console.log("ERROR!")
      }
    })

    resetArticle();
  })

  $('#getNewArticle').on('click', function(e) {
    e.preventDefault();

    var el = $('.selector.element');
    el.addClass('is-loading');

    $.ajax({
      type: "POST",
      url: $(this).attr('href'),
      dataType: "json",
      data: {
        "csrfmiddlewaretoken": $('input[name="csrfmiddlewaretoken"]').val()
      },
      success: function(d) {
        $('.selector').html(d.text);
        chunks = [];
        resetTextHTML = selectorArea.innerHTML;
        resetText = selectorArea.innerHTML.replace(/<br>/gi, '\n');
        el.removeClass('is-loading');
      },
      error: function() {
        console.log("ERROR!")
        el.removeClass('is-loading');
      }
    })
  });
});