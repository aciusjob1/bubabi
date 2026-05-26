// BUBABI Admin Panel — Self-contained toggle + search + SMS
(function() {
  // Run immediately if DOM already loaded, otherwise wait
  function init() {
    if (document.readyState === 'loading') return;
    setupToggles();
    setupSliders();
    setupSmsCounter();
    setupSearch();
    setupSmsConfirm();
    setupKeyboard();
  }

  // Try immediately
  init();
  // And on DOMContentLoaded
  document.addEventListener('DOMContentLoaded', init);
  // And on load as final fallback
  window.addEventListener('load', init);

  function setupToggles() {
    document.querySelectorAll('.toggle-header').forEach(function(header) {
      // Skip if already initialized
      if (header.dataset.toggleReady) return;
      header.dataset.toggleReady = '1';

      var targetId = header.getAttribute('data-target');
      if (!targetId) return;

      var body = document.getElementById(targetId);
      var arrow = document.getElementById(targetId + '-arrow');
      if (!body || !arrow) return;

      // Restore saved state
      var saved = localStorage.getItem('section_' + targetId);
      if (saved === 'false') {
        body.classList.remove('open');
        arrow.classList.remove('open');
        header.setAttribute('aria-expanded', 'false');
      }

      // Click handler
      header.addEventListener('click', function() {
        var isOpen = body.classList.toggle('open');
        arrow.classList.toggle('open');
        header.setAttribute('aria-expanded', isOpen);
        localStorage.setItem('section_' + targetId, isOpen);
      });
    });
  }

  function setupKeyboard() {
    document.querySelectorAll('.toggle-header[tabindex]').forEach(function(header) {
      if (header.dataset.keyReady) return;
      header.dataset.keyReady = '1';
      header.addEventListener('keydown', function(e) {
        if (e.key === 'Enter' || e.key === ' ') {
          e.preventDefault();
          header.click();
        }
      });
    });
  }

  function setupSliders() {
    document.querySelectorAll('.table-slider-btn').forEach(function(btn) {
      if (btn.dataset.sliderReady) return;
      btn.dataset.sliderReady = '1';
      btn.addEventListener('click', function() {
        var table = document.getElementById(btn.dataset.table);
        if (table) {
          table.scrollBy({ 
            left: parseInt(btn.dataset.direction) * 300, 
            behavior: 'smooth' 
          });
        }
      });
    });
  }

  function setupSmsCounter() {
    var smsText = document.getElementById('smsText');
    if (!smsText || smsText.dataset.counterReady) return;
    smsText.dataset.counterReady = '1';
    
    smsText.addEventListener('input', function() {
      var len = this.value.length;
      var segments = getSmsSegments(this.value);
      var charEl = document.getElementById('charCount');
      var segEl = document.getElementById('smsSegments');
      if (charEl) charEl.textContent = len;
      if (segEl) segEl.textContent = segments;
    });
  }

  function getSmsSegments(text) {
    if (!text) return 1;
    var isUnicode = /[^\x00-\x7F]/.test(text);
    var singleLimit = isUnicode ? 70 : 160;
    var multiLimit = isUnicode ? 67 : 153;
    if (text.length <= singleLimit) return 1;
    return Math.ceil(text.length / multiLimit);
  }

  var searchTimeout;
  function setupSearch() {
    var searchInput = document.getElementById('memberSearch');
    if (!searchInput || searchInput.dataset.searchReady) return;
    searchInput.dataset.searchReady = '1';
    
    searchInput.addEventListener('input', function() {
      clearTimeout(searchTimeout);
      var query = this.value;
      searchTimeout = setTimeout(function() {
        filterMembers(query);
      }, 200);
    });
  }

  function filterMembers(query) {
    var table = document.getElementById('memberTable');
    if (!table) return;
    var q = query.toLowerCase().trim();
    table.querySelectorAll('tbody tr').forEach(function(row) {
      var data = row.getAttribute('data-search') || '';
      row.style.display = data.includes(q) ? '' : 'none';
    });
  }

  var pendingForm = null;
  function setupSmsConfirm() {
    var form = document.querySelector('form[action*="send-bulk-sms"]');
    if (!form || form.dataset.confirmReady) return;
    form.dataset.confirmReady = '1';
    
    form.addEventListener('submit', function(e) {
      e.preventDefault();
      pendingForm = form;
      var msg = document.getElementById('smsText').value;
      var preview = msg.substring(0, 60) + (msg.length > 60 ? '...' : '');
      var segments = getSmsSegments(msg);
      var mc = document.querySelector('[data-member-count]');
      var memberCount = mc ? mc.dataset.memberCount : '?';
      
      var msgEl = document.getElementById('confirmMessage');
      if (msgEl) {
        msgEl.textContent = 'Sending to ' + memberCount + ' active members: "' + preview + '" (' + segments + ' SMS segment' + (segments > 1 ? 's' : '') + ')';
      }
      
      var overlay = document.getElementById('confirmOverlay');
      if (overlay) overlay.classList.add('active');
    });

    var closeBtn = document.getElementById('closeConfirm');
    if (closeBtn) {
      closeBtn.addEventListener('click', function() {
        var overlay = document.getElementById('confirmOverlay');
        if (overlay) overlay.classList.remove('active');
        pendingForm = null;
      });
    }

    var sendBtn = document.getElementById('confirmSendBtn');
    if (sendBtn) {
      sendBtn.addEventListener('click', function() {
        if (pendingForm) {
          sendBtn.textContent = 'Sending...';
          sendBtn.disabled = true;
          pendingForm.submit();
        }
      });
    }
  }
})();
