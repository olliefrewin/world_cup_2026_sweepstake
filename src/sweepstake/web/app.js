// Frontend logic. Communicates with the Python backend via window.pywebview.api.
// All api calls return Promises resolving to {ok, data} or {ok:false, error}.

(function () {
  'use strict';

  // -----------------------------------------------------------------------
  // Utilities
  // -----------------------------------------------------------------------

  function api(method, ...args) {
    // Wraps window.pywebview.api calls; waits for pywebview to be ready.
    return new Promise(function (resolve) {
      function attempt() {
        if (window.pywebview && window.pywebview.api && window.pywebview.api[method]) {
          window.pywebview.api[method](...args).then(resolve);
        } else {
          setTimeout(attempt, 80);
        }
      }
      attempt();
    });
  }

  function showAlert(id, message, type) {
    var el = document.getElementById(id);
    if (!el) return;
    el.className = 'alert alert-' + type;
    el.textContent = message;
    el.style.display = 'block';
  }

  function hideAlert(id) {
    var el = document.getElementById(id);
    if (el) el.style.display = 'none';
  }

  function escHtml(str) {
    if (str == null) return '';
    return String(str)
      .replace(/&/g, '&amp;')
      .replace(/</g, '&lt;')
      .replace(/>/g, '&gt;');
  }

  function dash(val) {
    return (val == null || val === '') ? '<span class="missing">--</span>' : escHtml(String(val));
  }

  // -----------------------------------------------------------------------
  // Tab switching
  // -----------------------------------------------------------------------

  var tabs = document.querySelectorAll('nav button[data-tab]');
  tabs.forEach(function (btn) {
    btn.addEventListener('click', function () {
      tabs.forEach(function (b) { b.classList.remove('active'); });
      btn.classList.add('active');
      document.querySelectorAll('.tab-panel').forEach(function (p) { p.classList.remove('active'); });
      document.getElementById('tab-' + btn.dataset.tab).classList.add('active');
      if (btn.dataset.tab === 'actuals')     { loadActuals(); loadApiStatus(); loadGoldenBootPending(); }
      if (btn.dataset.tab === 'submissions') { loadSubmissions(); }
      if (btn.dataset.tab === 'settings')    { loadSettings(); }
    });
  });

  // -----------------------------------------------------------------------
  // Leaderboard
  // -----------------------------------------------------------------------

  var leaderboardInterval = null;

  function loadLeaderboard() {
    api('get_leaderboard').then(function (res) {
      if (!res.ok) {
        showAlert('leaderboard-error', res.error, 'error');
        return;
      }
      hideAlert('leaderboard-error');
      renderLeaderboard(res.data);
    });
  }

  function renderLeaderboard(rows) {
    var tbody = document.getElementById('leaderboard-body');
    if (!rows || rows.length === 0) {
      tbody.innerHTML = '<tr><td colspan="7" class="text-muted" style="padding:20px;text-align:center">No participants yet. Upload some entries in the Submissions tab.</td></tr>';
      return;
    }
    tbody.innerHTML = rows.map(function (r) {
      var rankClass = r.rank <= 3 ? 'rank-' + r.rank : '';
      var p1 = r.part1_total != null ? r.part1_total : '<span class="missing">--</span>';
      var p2 = r.part2_total != null ? r.part2_total : '<span class="missing">--</span>';
      var tb = r.tiebreaker_pred != null ? r.tiebreaker_pred : '<span class="missing">--</span>';
      return '<tr class="' + rankClass + '">' +
        '<td class="rank">' + r.rank + '</td>' +
        '<td>' + escHtml(r.name) + '</td>' +
        '<td class="num">' + p1 + '</td>' +
        '<td class="num">' + p2 + '</td>' +
        '<td class="num"><strong>' + r.grand_total + '</strong></td>' +
        '<td class="num">' + tb + '</td>' +
        '<td><button class="link-btn" data-pid="' + r.participant_id + '" data-name="' + escHtml(r.name) + '">Breakdown</button></td>' +
        '</tr>';
    }).join('');

    // Breakdown buttons
    tbody.querySelectorAll('.link-btn').forEach(function (btn) {
      btn.addEventListener('click', function () {
        openBreakdown(parseInt(btn.dataset.pid), btn.dataset.name);
      });
    });
  }

  // Auto-refresh every 5 seconds
  leaderboardInterval = setInterval(function () {
    var active = document.querySelector('nav button.active');
    if (active && active.dataset.tab === 'leaderboard') {
      loadLeaderboard();
    }
  }, 5000);
  loadLeaderboard();

  // -----------------------------------------------------------------------
  // Score breakdown modal
  // -----------------------------------------------------------------------

  function openBreakdown(participantId, name) {
    document.getElementById('breakdown-title').textContent = 'Score Breakdown: ' + name;
    document.getElementById('breakdown-content').innerHTML = '<p class="text-muted">Loading...</p>';
    document.getElementById('breakdown-modal').classList.add('open');

    api('get_score_breakdown', participantId).then(function (res) {
      if (!res.ok) {
        document.getElementById('breakdown-content').innerHTML = '<p class="alert alert-error">' + escHtml(res.error) + '</p>';
        return;
      }
      var d = res.data;
      var html = '';

      if (d.part1) {
        html += '<p class="section-title">Part 1 - Group Stage &amp; Picks</p>';
        html += breakdownRow('Group Winners (x10)', d.part1.group_winners);
        html += breakdownRow('Group Runners-Up (x5)', d.part1.group_runners_up);
        html += breakdownRow('Finalists (x15 each)', d.part1.finalists);
        html += breakdownRow('World Cup Winner (x25)', d.part1.winner);
        html += breakdownRow('Golden Boot (x15)', d.part1.golden_boot);
        html += breakdownRow('Part 1 Total', d.part1.total, true);
      } else {
        html += '<p class="text-muted">No Part 1 submission.</p>';
      }

      if (d.part2) {
        html += '<hr>';
        html += '<p class="section-title">Part 2 - Knockout Bracket</p>';
        html += breakdownRow('Round of 32 (x3 each)', d.part2.r32);
        html += breakdownRow('Round of 16 (x5 each)', d.part2.r16);
        html += breakdownRow('Quarter-Finals (x8 each)', d.part2.qf);
        html += breakdownRow('Semi-Finals (x12 each)', d.part2.sf);
        html += breakdownRow('Champion (x20)', d.part2.champion);
        html += breakdownRow('Part 2 Total', d.part2.total, true);
      } else {
        html += '<hr><p class="text-muted">No Part 2 submission.</p>';
      }

      var grand = (d.part1 ? d.part1.total : 0) + (d.part2 ? d.part2.total : 0);
      html += '<hr>' + breakdownRow('Grand Total', grand, true);

      document.getElementById('breakdown-content').innerHTML = html;
    });
  }

  function breakdownRow(label, value, bold) {
    return '<div class="breakdown-row">' +
      '<span' + (bold ? ' style="font-weight:700"' : '') + '>' + escHtml(label) + '</span>' +
      '<span' + (bold ? ' style="font-weight:700"' : '') + '>' + escHtml(String(value)) + '</span>' +
      '</div>';
  }

  document.getElementById('breakdown-close').addEventListener('click', function () {
    document.getElementById('breakdown-modal').classList.remove('open');
  });
  document.getElementById('breakdown-modal').addEventListener('click', function (e) {
    if (e.target === this) this.classList.remove('open');
  });

  // -----------------------------------------------------------------------
  // Submissions
  // -----------------------------------------------------------------------

  function loadSubmissions() {
    api('list_submissions').then(function (res) {
      if (!res.ok) return;
      var tbody = document.getElementById('submissions-body');
      var rows = res.data;
      if (!rows || rows.length === 0) {
        tbody.innerHTML = '<tr><td colspan="6" class="text-muted" style="padding:20px;text-align:center">No submissions yet.</td></tr>';
        return;
      }
      tbody.innerHTML = rows.map(function (r) {
        var p1 = r.part1;
        var p2 = r.part2;
        return '<tr>' +
          '<td>' + escHtml(r.name) + '</td>' +
          '<td>' + dash(p1 && p1.uploaded_at) + '</td>' +
          '<td>' + dash(p1 && p1.filename) + '</td>' +
          '<td>' + dash(p2 && p2.uploaded_at) + '</td>' +
          '<td>' + dash(p2 && p2.filename) + '</td>' +
          '<td>' +
            (p1 ? '<button class="btn btn-danger btn-sm" data-pid="' + r.participant_id + '" data-part="part1">Remove P1</button> ' : '') +
            (p2 ? '<button class="btn btn-danger btn-sm" data-pid="' + r.participant_id + '" data-part="part2">Remove P2</button>' : '') +
          '</td>' +
          '</tr>';
      }).join('');

      tbody.querySelectorAll('.btn-danger').forEach(function (btn) {
        btn.addEventListener('click', function () {
          var pid = parseInt(btn.dataset.pid);
          var part = btn.dataset.part;
          if (!confirm('Remove this submission? This cannot be undone.')) return;
          api('remove_submission', pid, part).then(function (res) {
            if (res.ok) loadSubmissions();
            else alert('Error: ' + res.error);
          });
        });
      });
    });
  }

  // File upload
  document.getElementById('browse-btn').addEventListener('click', function () {
    api('open_file_dialog').then(function (res) {
      if (!res.ok || !res.data) return;
      stageFile(res.data);
    });
  });

  // Drag and drop
  var zone = document.getElementById('upload-zone');
  zone.addEventListener('dragover', function (e) { e.preventDefault(); zone.classList.add('drag-over'); });
  zone.addEventListener('dragleave', function () { zone.classList.remove('drag-over'); });
  zone.addEventListener('drop', function (e) {
    e.preventDefault();
    zone.classList.remove('drag-over');
    var file = e.dataTransfer.files[0];
    if (file) stageFile(file.path || file.name);
  });

  function stageFile(path) {
    hideAlert('upload-error');
    hideAlert('upload-success');
    hideAlert('upload-warning');
    api('stage_upload', path).then(function (res) {
      if (!res.ok) {
        showAlert('upload-error', res.error, 'error');
        return;
      }
      var d = res.data;
      var partLabel = d.kind === 'part1' ? 'Part 1 (Group Stage)' : 'Part 2 (Knockout Bracket)';
      document.getElementById('confirm-title').textContent = 'Confirm upload: ' + partLabel;
      document.getElementById('preview-area').innerHTML = renderPreview(d.kind, d.preview);
      if (d.warnings && d.warnings.length > 0) {
        document.getElementById('warnings-area').innerHTML =
          '<div class="alert alert-warning" style="margin-top:10px">' + escHtml(d.warnings.join('\n')) + '</div>';
      } else {
        document.getElementById('warnings-area').innerHTML = '';
      }
      document.getElementById('confirm-panel').style.display = 'block';
    });
  }

  function renderPreview(kind, p) {
    if (kind === 'part1') {
      var groupRows = Object.entries(p.group_picks || {}).map(function (entry) {
        return '<tr><td>Group ' + entry[0] + '</td><td>' + escHtml(entry[1].winner) + '</td><td>' + escHtml(entry[1].runner_up) + '</td></tr>';
      }).join('');
      return '<dl class="preview-grid">' +
        '<dt>Name</dt><dd>' + escHtml(p.name) + '</dd>' +
        '<dt>Submitted on</dt><dd>' + dash(p.submitted_on) + '</dd>' +
        '<dt>Finalist 1</dt><dd>' + dash(p.finalist_1) + '</dd>' +
        '<dt>Finalist 2</dt><dd>' + dash(p.finalist_2) + '</dd>' +
        '<dt>Winner</dt><dd>' + dash(p.winner) + '</dd>' +
        '<dt>Golden Boot</dt><dd>' + dash(p.golden_boot) + '</dd>' +
        '</dl>' +
        '<p style="margin-top:10px;font-size:12px;color:var(--text-muted)">Group picks: all 12 groups parsed.</p>';
    } else {
      return '<dl class="preview-grid">' +
        '<dt>Name</dt><dd>' + escHtml(p.name) + '</dd>' +
        '<dt>Champion</dt><dd>' + dash(p.champion) + '</dd>' +
        '<dt>Tiebreaker (final goals)</dt><dd>' + dash(p.tiebreaker) + '</dd>' +
        '</dl>' +
        '<p style="margin-top:10px;font-size:12px;color:var(--text-muted)">Bracket picks: all rounds parsed.</p>';
    }
  }

  document.getElementById('confirm-btn').addEventListener('click', function () {
    api('confirm_upload').then(function (res) {
      if (!res.ok) {
        showAlert('upload-error', res.error, 'error');
      } else {
        showAlert('upload-success', res.data, 'success');
        document.getElementById('confirm-panel').style.display = 'none';
        loadSubmissions();
      }
    });
  });

  document.getElementById('cancel-btn').addEventListener('click', function () {
    api('cancel_upload').then(function () {
      document.getElementById('confirm-panel').style.display = 'none';
      hideAlert('upload-error');
    });
  });

  // -----------------------------------------------------------------------
  // Actuals
  // -----------------------------------------------------------------------

  function loadApiStatus() {
    api('get_api_status').then(function (res) {
      if (!res.ok) return;
      var d = res.data;
      document.getElementById('calls-today').textContent = d.calls_today;
      document.getElementById('last-refresh').textContent = d.last_refresh;
      var pct = Math.min(100, Math.round(d.calls_today / d.quota * 100));
      document.getElementById('quota-bar').style.width = pct + '%';
      document.getElementById('refresh-btn').disabled = !d.api_key_set;
    });
  }

  document.getElementById('refresh-btn').addEventListener('click', function () {
    hideAlert('actuals-error');
    hideAlert('actuals-success');
    var btn = this;
    btn.disabled = true;
    btn.textContent = 'Refreshing...';
    api('refresh_now').then(function (res) {
      btn.textContent = '↻ Refresh Now';
      btn.disabled = false;
      if (res.ok) {
        showAlert('actuals-success', res.data, 'success');
        loadActuals();
        loadApiStatus();
      } else {
        showAlert('actuals-error', res.error, 'error');
      }
    });
  });

  function loadActuals() {
    api('get_actuals_grid').then(function (res) {
      if (!res.ok) return;
      var tbody = document.getElementById('actuals-body');
      var rows = res.data;
      if (!rows || rows.length === 0) {
        tbody.innerHTML = '<tr><td colspan="5" class="text-muted" style="padding:16px;text-align:center">No actuals yet.</td></tr>';
        return;
      }
      tbody.innerHTML = rows.map(function (r) {
        return '<tr>' +
          '<td><code>' + escHtml(r.key) + '</code></td>' +
          '<td>' + dash(r.api_value) + '</td>' +
          '<td>' + dash(r.override_value) + '</td>' +
          '<td><strong>' + escHtml(r.effective || '') + '</strong></td>' +
          '<td>' +
            '<button class="btn btn-sm btn-secondary edit-override-btn" data-key="' + escHtml(r.key) + '" data-val="' + escHtml(r.override_value || '') + '">Edit</button>' +
            (r.override_value != null ? ' <button class="btn btn-sm btn-danger del-override-btn" data-key="' + escHtml(r.key) + '">Remove</button>' : '') +
          '</td>' +
          '</tr>';
      }).join('');

      tbody.querySelectorAll('.edit-override-btn').forEach(function (btn) {
        btn.addEventListener('click', function () {
          var key = btn.dataset.key;
          var cur = btn.dataset.val;
          var val = prompt('Override value for "' + key + '":', cur);
          if (val === null) return;
          var note = prompt('Note (optional):') || '';
          api('set_override', key, val, note).then(function (res) {
            if (res.ok) loadActuals();
            else showAlert('actuals-error', res.error, 'error');
          });
        });
      });

      tbody.querySelectorAll('.del-override-btn').forEach(function (btn) {
        btn.addEventListener('click', function () {
          if (!confirm('Remove override for "' + btn.dataset.key + '"?')) return;
          api('delete_override', btn.dataset.key).then(function (res) {
            if (res.ok) loadActuals();
            else showAlert('actuals-error', res.error, 'error');
          });
        });
      });
    });
  }

  document.getElementById('add-override-btn').addEventListener('click', function () {
    var key   = document.getElementById('new-key-input').value.trim();
    var value = document.getElementById('new-value-input').value.trim();
    var note  = document.getElementById('new-note-input').value.trim();
    if (!key) { showAlert('actuals-error', 'Key cannot be empty.', 'error'); return; }
    api('add_manual_actual', key, value, note).then(function (res) {
      if (res.ok) {
        document.getElementById('new-key-input').value = '';
        document.getElementById('new-value-input').value = '';
        document.getElementById('new-note-input').value = '';
        hideAlert('actuals-error');
        loadActuals();
      } else {
        showAlert('actuals-error', res.error, 'error');
      }
    });
  });

  // -----------------------------------------------------------------------
  // Golden Boot
  // -----------------------------------------------------------------------

  function loadGoldenBootPending() {
    api('get_golden_boot_pending').then(function (res) {
      if (!res.ok) return;
      var area = document.getElementById('gb-pending-area');
      var rows = res.data;
      if (!rows || rows.length === 0) {
        area.innerHTML = '<p class="text-muted" style="font-size:13px">No pending Golden Boot matches.</p>';
        return;
      }
      area.innerHTML = '<p class="section-title" style="margin-bottom:10px">Pending matches (' + rows.length + ')</p>' +
        rows.map(function (r) {
          return '<div style="display:flex;align-items:center;gap:12px;padding:8px 0;border-bottom:1px solid var(--border)">' +
            '<span style="flex:1"><strong>' + escHtml(r.participant_name) + '</strong> wrote: <em>' + escHtml(r.raw_text) + '</em></span>' +
            '<button class="btn btn-primary btn-sm gb-match-btn" data-pid="' + r.participant_id + '">Match</button>' +
            '<button class="btn btn-secondary btn-sm gb-reject-btn" data-pid="' + r.participant_id + '">No match</button>' +
            '</div>';
        }).join('');

      area.querySelectorAll('.gb-match-btn').forEach(function (btn) {
        btn.addEventListener('click', function () {
          api('resolve_golden_boot', parseInt(btn.dataset.pid), true).then(function (res) {
            if (res.ok) loadGoldenBootPending();
            else showAlert('actuals-error', res.error, 'error');
          });
        });
      });
      area.querySelectorAll('.gb-reject-btn').forEach(function (btn) {
        btn.addEventListener('click', function () {
          api('resolve_golden_boot', parseInt(btn.dataset.pid), false).then(function (res) {
            if (res.ok) loadGoldenBootPending();
            else showAlert('actuals-error', res.error, 'error');
          });
        });
      });
    });
  }

  document.getElementById('gb-set-btn').addEventListener('click', function () {
    var canonical = document.getElementById('gb-canonical-input').value.trim();
    if (!canonical) return;
    api('set_golden_boot_canonical', canonical).then(function (res) {
      if (res.ok) {
        var d = res.data;
        showAlert('actuals-success', 'Golden Boot set to "' + canonical + '". Pending: ' + d.pending + ', auto-rejected: ' + d.auto_rejected + '.', 'success');
        loadGoldenBootPending();
      } else {
        showAlert('actuals-error', res.error, 'error');
      }
    });
  });

  // -----------------------------------------------------------------------
  // Settings
  // -----------------------------------------------------------------------

  function loadSettings() {
    api('get_settings').then(function (res) {
      if (!res.ok) return;
      document.getElementById('api-key-input').value = res.data.api_key;
      document.getElementById('db-path-display').value = res.data.db_path;
    });
    api('get_version').then(function (res) {
      if (res.ok) document.getElementById('version-display').textContent = res.data;
    });
  }

  document.getElementById('save-key-btn').addEventListener('click', function () {
    var key = document.getElementById('api-key-input').value;
    api('save_api_key', key).then(function (res) {
      if (res.ok) showAlert('settings-success', res.data, 'success');
      else showAlert('settings-error', res.error, 'error');
    });
  });

  document.getElementById('test-key-btn').addEventListener('click', function () {
    hideAlert('settings-error');
    hideAlert('settings-success');
    api('test_api_connection').then(function (res) {
      if (res.ok) showAlert('settings-success', res.data, 'success');
      else showAlert('settings-error', res.error, 'error');
    });
  });

  document.getElementById('export-btn').addEventListener('click', function () {
    api('export_csv').then(function (res) {
      if (!res.ok) showAlert('settings-error', res.error, 'error');
      else if (res.data) showAlert('settings-success', res.data, 'success');
    });
  });

})();
