$(document).ready(function() {
  var chunks = [],
      selectorArea = document.querySelector('.selector'),
      resetTextHTML = selectorArea.innerHTML,
      resetText = selectorArea.innerHTML.replace(/<br>/gi, '\n'),
      contextSize = $('#taskArea').data('context'),
      qStart = new Date();

  function previousTextLength(node) {
    var len = 0;
    var prev = node.previousSibling;
    while (prev != null) {
      if (prev.nodeType == 1) {
        if (prev.tagName == "BR") {
          // if newline
          len += 1
        } else if (prev.tagName == "SPAN" && prev.classList.contains("tag")) {
          // if there is a label
          len += prev.innerText.length
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

  $('.marker.tags').on('click', function() {
    var chunk = chunks[chunks.length - 1],
        idc = chunks.length - 1
        color = this.getAttribute('data-color'),
        leftTextNode = document.createTextNode(chunk['text'].slice(0, chunk['start'])),
        markedSpan = document.createElement('span'),
        deleteMarkedBtn = document.createElement('button'),
        rightTextNode = document.createTextNode(chunk['text'].slice(chunk['end'])),
        parent = chunk['node'].parentNode;
    markedSpan.className = "tag is-" + color + " is-medium";
    markedSpan.textContent = chunk['text'].slice(chunk['start'], chunk['end']);
    deleteMarkedBtn.className = 'delete is-small';
    deleteMarkedBtn.addEventListener('click', function(e) {
      e.stopPropagation();
      var el = e.target,
          parent = el.parentNode; // actual span

      chunks.splice(idc, 1);
      mergeWithNeighbors(parent);
      window.chunks = chunks;
    }, true);
    markedSpan.appendChild(deleteMarkedBtn)

    parent.replaceChild(leftTextNode, chunk['node']);
    parent.insertBefore(markedSpan, leftTextNode.nextSibling);
    parent.insertBefore(rightTextNode, markedSpan.nextSibling);
    chunk['marked'] = true;
    chunk['label'] = this.querySelector('span.tag:first-child').textContent;
    delete chunk['node']
    window.chunks = chunks;
  });

  function updateChunk() {
    var selection = window.getSelection(),
        chunk = {};

    if (selection) {
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
        chunk['context'] = resetText;
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

      if (chunks.length == 0 || (chunks.length > 0 && chunks[chunks.length - 1] !== undefined && chunks[chunks.length - 1]['marked'])) {
        chunks.push(chunk);
      } else {
        chunks[chunks.length - 1] = chunk;
      }
    }
  }

  $('.selector').on('mouseup', function(e) {
    var isRightMB;
    e = e || window.event;

    if ("which" in e)  // Gecko (Firefox), WebKit (Safari/Chrome) & Opera
        isRightMB = e.which == 3; 
    else if ("button" in e)  // IE, Opera 
        isRightMB = e.button == 2;

    if (!$(e.target).hasClass('delete') && !isRightMB) {
      updateChunk();
    }
  })

  $(document).on("keyup", function(e) {
    var selection = window.getSelection();
    if (selection) {
      var isArticleParent = selection.anchorNode.parentNode == document.querySelector('.selector');
      if (e.shiftKey && e.which >= 37 && e.which <= 40 && isArticleParent) {
        updateChunk();
      } else {
        var $shortcut = $('[data-shortcut="' + String.fromCharCode(e.which) + '"]');
        if ($shortcut.length > 0) {
          $shortcut.click();
        }
      }
    }
  });

  $('#inputForm .submit.button').on('click', function(e) {
    e.preventDefault();

    var $inputForm = $('#inputForm'),
        $qInput = $inputForm.find('input.question'),
        $questionBlock = $('article.question');

    $qInput.prop("disabled", false);

    var inputFormData = $inputForm.serializeObject(),
        underReview = $questionBlock.prop('review') || false;
    inputFormData['chunks'] = JSON.stringify(chunks);
    inputFormData['is_review'] = underReview;
    inputFormData['time'] = Math.round(((new Date()).getTime() - qStart.getTime()) / 1000, 1);

    $.ajax({
      method: "POST",
      url: inputForm.action,
      dataType: "json",
      data: inputFormData,
      success: function(data) {
        if (data['error'] == false) {
          var articleNode = document.querySelector('.selector'),
              $title = $questionBlock.find('.message-header p');
          if (data['input'] == null) {
            // no review task
            resetArticle();
            $questionBlock.removeClass('is-warning');
            $questionBlock.addClass('is-primary');
            $questionBlock.prop('review', false);

            $title.html("Your question");

            $qInput.prop("disabled", false);
            $qInput.val('');
            $qInput.focus();
          } else {
            // review task
            removeAllChildren(articleNode);
            articleNode.innerHTML = data['input']['context'];

            $questionBlock.removeClass('is-primary');
            $questionBlock.addClass('is-warning');
            $questionBlock.prop('review', true);

            $title.html("Review question");

            $qInput.val(data['input']['content']);
            $qInput.prop("disabled", true);
          }
          if ('aat' in data)
            $('#aat').html(data['aat'] + "s");
        }
        var $inpSmaller = (data['inp_points'] >= 1000) ? $('<span class="smaller">kp</span>') : $('<span class="smaller">p</span>'),
            $inpPts = $('#inputPoints'),
            $peerSmaller = (data['peer_points'] >= 1000) ? $('<span class="smaller">kp</span>') : $('<span class="smaller">p</span>'),
            $peerPts = $('#peerPoints');
        
        $inpPts.text(data['inp_points']);
        $inpPts.append($inpSmaller);
        
        $peerPts.text(data['peer_points']);
        $peerPts.append($peerSmaller);
        
        chunks = [];
        qStart = new Date();
        $('.countdown').trigger('cdAnimateStop').trigger('cdAnimate');
      },
      error: function() {
        console.log("ERROR!")
        if (underReview)
          $qInput.prop("disabled", true)
        else {
          $qInput.val('');
          $qInput.prop('disabled', false);
        }
        qStart = new Date();
        $('.countdown').trigger('cdAnimateReset').trigger('cdAnimate');
      }
    })

    resetArticle();
  })

  $('#getNewArticle').on('click', function(e) {
    e.preventDefault();

    var confirmation = chunks.length > 0 ? confirm("All your unsubmitted labels will be removed. Are you sure?") : true;

    if (confirmation) {
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
    }
  });
});