const bridge = window.AstrBotPluginPage;
let logSubscriptionId = null;

async function init() {
  const context = await bridge.ready();
  document.title = bridge.t("pages.manager.title", "发烧AI管理面板");

  await refreshStats();
  await refreshUsers();

  document.getElementById("btn-refresh").addEventListener("click", async () => {
    await refreshStats();
    await refreshUsers();
  });

  document.getElementById("btn-reset-all").addEventListener("click", async () => {
    if (!confirm("确定要重置所有用户的发烧AI状态吗？")) return;
    try {
      const result = await bridge.apiPost("api/users/reset-all", {});
      alert(`已重置 ${result.count || 0} 个用户`);
      await refreshStats();
      await refreshUsers();
    } catch (e) {
      alert("重置失败: " + e.message);
    }
  });

  subscribeLogs();
}

async function refreshStats() {
  try {
    const stats = await bridge.apiGet("api/stats");
    document.getElementById("stat-active").textContent = stats.active_users ?? 0;
    document.getElementById("stat-total").textContent = stats.total_users ?? 0;
    document.getElementById("stat-msg").textContent = stats.today_messages ?? 0;
  } catch (e) {
    console.warn("Failed to fetch stats:", e);
  }
}

async function refreshUsers() {
  const tbody = document.getElementById("user-table-body");
  try {
    const users = await bridge.apiGet("api/users");
    if (!users || users.length === 0) {
      tbody.innerHTML = '<tr><td colspan="4" style="color:var(--text-secondary)">暂无活跃用户</td></tr>';
      return;
    }
    tbody.innerHTML = users.map(u => {
      let badgeClass = "badge-inactive";
      let badgeLabel = "未激活";
      if (u.state === "active") { badgeClass = "badge-active"; badgeLabel = u.persona || "活跃"; }
      else if (u.state !== "none") { badgeClass = "badge-pending"; badgeLabel = "设置中"; }
      return `<tr>
        <td>${esc(u.user_id)}</td>
        <td><span class="badge ${badgeClass}">${esc(badgeLabel)}</span></td>
        <td>${esc(u.persona || "-")}</td>
        <td>
          <button class="btn btn-danger" data-uid="${esc(u.user_id)}">重置</button>
        </td>
      </tr>`;
    }).join("");

    tbody.querySelectorAll("[data-uid]").forEach(btn => {
      btn.addEventListener("click", async () => {
        const uid = btn.dataset.uid;
        if (!confirm(`确定重置用户 ${uid} 吗？`)) return;
        try {
          await bridge.apiPost("api/users/reset", { user_id: uid });
          await refreshUsers();
          await refreshStats();
        } catch (e) {
          alert("重置失败: " + e.message);
        }
      });
    });
  } catch (e) {
    tbody.innerHTML = `<tr><td colspan="4" style="color:var(--danger)">加载失败: ${esc(e.message)}</td></tr>`;
  }
}

function subscribeLogs() {
  const logArea = document.getElementById("log-area");
  bridge.subscribeSSE("api/logs", {
    onOpen() {
      logArea.innerHTML = '<div class="log-entry log-info">日志连接已建立</div>';
    },
    onMessage(event) {
      const data = event.parsed || {};
      const level = data.level || "info";
      const msg = data.message || event.raw;
      const cls = level === "warn" ? "log-warn" : level === "error" ? "log-error" : "log-info";
      const entry = document.createElement("div");
      entry.className = `log-entry ${cls}`;
      entry.textContent = `[${level.toUpperCase()}] ${msg}`;
      logArea.appendChild(entry);
      logArea.scrollTop = logArea.scrollHeight;
      if (logArea.children.length > 200) {
        logArea.removeChild(logArea.firstChild);
      }
    },
    onError() {
      const entry = document.createElement("div");
      entry.className = "log-entry log-error";
      entry.textContent = "[ERROR] 日志连接断开";
      logArea.appendChild(entry);
    },
  }).then(id => { logSubscriptionId = id; });
}

function esc(s) {
  if (s == null) return "";
  return String(s).replace(/&/g, "&amp;").replace(/</g, "&lt;").replace(/>/g, "&gt;");
}

init().catch(console.error);
