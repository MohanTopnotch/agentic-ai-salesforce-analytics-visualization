const API_URL = "/api/v1/query";
const questionInput = document.getElementById("question");
const runButton = document.getElementById("run-query");
const btnSpinner = document.getElementById("btn-spinner");
const statusLabel = document.getElementById("request-status");
const statusBeacon = document.getElementById("status-beacon");
const errorBox = document.getElementById("error-box");
const errorMessage = document.getElementById("error-message");
const exportButton = document.getElementById("export-csv");
const kpiBanner = document.getElementById("kpi-banner");
const kpiCount = document.getElementById("kpi-count");
const kpiSum = document.getElementById("kpi-sum");
const tableRowBadge = document.getElementById("table-row-badge");
const copyReqIdBtn = document.getElementById("copy-req-id");
const themeToggleBtn = document.getElementById("theme-toggle");
const themeText = document.getElementById("theme-text");

let currentRows = [];
let currentResponse = null;

// =====================================================================
// LIGHT / DARK THEME TOGGLE CONTROLLER
// =====================================================================
function applyTheme(theme) {
  document.documentElement.setAttribute("data-theme", theme);
  localStorage.setItem("sf_analytics_theme", theme);
  if (themeText) {
    themeText.textContent = theme === "light" ? "Light" : "Dark";
  }
  // Re-render chart if it is already displayed so its colors adapt
  if (currentResponse) {
    const data = currentResponse.data || {};
    const chart = data.chart || data.visualization || data.visualization_spec;
    if (chart) renderChart(chart);
  }
}

const savedTheme = localStorage.getItem("sf_analytics_theme") || "dark";
applyTheme(savedTheme);

if (themeToggleBtn) {
  themeToggleBtn.addEventListener("click", () => {
    const currentTheme = document.documentElement.getAttribute("data-theme") || "dark";
    const nextTheme = currentTheme === "dark" ? "light" : "dark";
    applyTheme(nextTheme);
  });
}

// Chip prompt selection
document.querySelectorAll(".chip").forEach((chip) => {
  chip.addEventListener("click", () => {
    questionInput.value = chip.textContent.trim();
    questionInput.focus();
  });
});

// Event listeners
runButton.addEventListener("click", runAnalysis);
exportButton.addEventListener("click", exportCsv);
questionInput.addEventListener("keydown", (event) => {
  if ((event.ctrlKey || event.metaKey) && event.key === "Enter") runAnalysis();
});

if (copyReqIdBtn) {
  copyReqIdBtn.addEventListener("click", () => {
    const reqId = document.getElementById("request-id").textContent;
    if (reqId && reqId !== "—") {
      navigator.clipboard.writeText(reqId).then(() => {
        copyReqIdBtn.title = "Copied!";
        setTimeout(() => { copyReqIdBtn.title = "Copy Request ID"; }, 2000);
      });
    }
  });
}

function setText(id, value, fallback = "—") {
  const el = document.getElementById(id);
  if (el) el.textContent = value ?? fallback;
}

function findRows(payload) {
  const candidates = [
    payload?.data?.rows,
    payload?.data?.records,
    payload?.data?.table?.rows,
    payload?.data?.results,
    payload?.data?.data,
  ];
  return candidates.find(Array.isArray) || [];
}

function showError(message) {
  if (errorBox) errorBox.hidden = false;
  if (errorMessage) {
    errorMessage.textContent = message || "The API returned an unexpected error. Please check service logs.";
  } else if (errorBox) {
    errorBox.textContent = message;
  }
}

function clearError() {
  if (errorBox) errorBox.hidden = true;
  if (errorMessage) errorMessage.textContent = "";
}

function setStatusState(state, text) {
  if (statusLabel) statusLabel.textContent = text;
  if (statusBeacon) {
    statusBeacon.className = `status-beacon status-${state}`;
  }
}

async function runAnalysis() {
  const question = questionInput.value.trim();
  if (!question) {
    showError("Please enter an analytical question before submitting.");
    questionInput.focus();
    return;
  }

  clearError();
  runButton.disabled = true;
  if (btnSpinner) btnSpinner.hidden = false;
  setStatusState("busy", "Executing agents & SOQL query…");

  try {
    const response = await fetch(API_URL, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ question }),
    });

    const payload = await response.json().catch(() => ({}));
    currentResponse = payload;

    if (!response.ok) {
      throw new Error(payload?.detail || `API Request failed with HTTP status ${response.status}.`);
    }

    if (payload.status !== "success") {
      updateAudit(payload);
      throw new Error(payload.message || payload.error_code || "Workflow failed during execution.");
    }

    updateAudit(payload);
    renderResults(payload);
    setStatusState("idle", "Analysis completed");
  } catch (error) {
    showError(error.message);
    setStatusState("err", "Analysis failed");
    currentRows = [];
    exportButton.disabled = true;
    if (kpiBanner) kpiBanner.hidden = true;
  } finally {
    runButton.disabled = false;
    if (btnSpinner) btnSpinner.hidden = true;
  }
}

function updateAudit(payload) {
  const verified = payload.verified === true;
  const badge = document.getElementById("verification-badge");
  if (badge) {
    badge.className = `badge ${verified ? "pass" : "fail"}`;
    badge.textContent = verified ? "✓ Verified Clean" : "✕ Not verified / Failed";
  }
  
  setText("request-id", payload.request_id);
  setText("verified-value", verified ? "100% Deterministic checks passed" : "Verification flagged discrepancy");
  setText("checked-at", new Date().toLocaleTimeString() + " (" + new Date().toLocaleDateString() + ")");
  setText("workflow-state", payload.state || "completed");

  const lineageData = payload.data?.lineage ?? payload.data?.provenance ?? payload.data?.audit ?? {
    error_code: payload.error_code,
    message: payload.message,
    validation_status: payload.data?.validation_status,
    note: "Comprehensive lineage tracked across Query Understanding -> SOQL -> Data Analysis -> Auditor Agents.",
  };
  
  const lineageEl = document.getElementById("lineage");
  if (lineageEl) {
    lineageEl.textContent = JSON.stringify(lineageData, null, 2);
  }
}

function renderResults(payload) {
  const data = payload.data || {};
  setText("result-title", data.title || "Interactive Analysis Results");

  const chart = data.chart || data.visualization || data.visualization_spec;
  renderChart(chart);

  currentRows = findRows(payload);
  renderTable(currentRows);
  updateKPIs(currentRows);
  exportButton.disabled = currentRows.length === 0;
}

function updateKPIs(rows) {
  if (!kpiBanner) return;
  if (!rows || rows.length === 0) {
    kpiBanner.hidden = true;
    if (tableRowBadge) tableRowBadge.textContent = "0 rows";
    return;
  }

  kpiBanner.hidden = false;
  if (tableRowBadge) tableRowBadge.textContent = `${rows.length} rows`;
  if (kpiCount) kpiCount.textContent = rows.length.toLocaleString();

  // Find first numeric column to calculate summary KPI
  if (rows.length > 0 && kpiSum) {
    const firstRow = rows[0];
    const numericKeys = Object.keys(firstRow).filter((key) => {
      const val = firstRow[key];
      return typeof val === "number" || (!isNaN(Number(val)) && val !== "");
    });

    if (numericKeys.length > 0) {
      const primaryKey = numericKeys[0];
      const sum = rows.reduce((acc, row) => acc + (Number(row[primaryKey]) || 0), 0);
      const isCurrency = primaryKey.toLowerCase().includes("revenue") ||
                         primaryKey.toLowerCase().includes("amount") ||
                         primaryKey.toLowerCase().includes("sales");
      
      kpiSum.textContent = isCurrency
        ? `$${sum.toLocaleString(undefined, { maximumFractionDigits: 0 })}`
        : sum.toLocaleString();
    } else {
      kpiSum.textContent = `${rows.length} groups`;
    }
  }
}

function renderChart(spec) {
  const target = document.getElementById("chart");
  if (!spec || typeof spec !== "object") {
    target.innerHTML = '<div class="empty-state"><h3>No Chart Specification</h3><p>Query completed but returned tabular data only.</p></div>';
    return;
  }

  // Dynamic Theme configuration for Plotly (adapts to light or dark)
  const isLight = document.documentElement.getAttribute("data-theme") === "light";
  const themeLayout = {
    paper_bgcolor: 'transparent',
    plot_bgcolor: 'transparent',
    font: {
      family: "'Plus Jakarta Sans', -apple-system, sans-serif",
      color: isLight ? '#475569' : '#94a3b8',
      size: 12
    },
    colorway: isLight
      ? ['#0284c7', '#6366f1', '#059669', '#db2777', '#d97706', '#7c3aed']
      : ['#38bdf8', '#818cf8', '#34d399', '#f472b6', '#fbbf24', '#a78bfa', '#2dd4bf'],
    xaxis: {
      gridcolor: isLight ? 'rgba(0, 0, 0, 0.06)' : 'rgba(255, 255, 255, 0.06)',
      zerolinecolor: isLight ? 'rgba(0, 0, 0, 0.12)' : 'rgba(255, 255, 255, 0.1)',
      tickfont: { color: isLight ? '#475569' : '#94a3b8' }
    },
    yaxis: {
      gridcolor: isLight ? 'rgba(0, 0, 0, 0.06)' : 'rgba(255, 255, 255, 0.06)',
      zerolinecolor: isLight ? 'rgba(0, 0, 0, 0.12)' : 'rgba(255, 255, 255, 0.1)',
      tickfont: { color: isLight ? '#475569' : '#94a3b8' }
    },
    margin: { t: 40, r: 24, b: 60, l: 65 },
    autosize: true
  };

  let figure;
  const titleColor = isLight ? '#0f172a' : '#f8fafc';
  if (Array.isArray(spec.data)) {
    figure = {
      data: spec.data,
      layout: {
        ...themeLayout,
        title: {
          text: spec.layout?.title?.text || spec.layout?.title || spec.title || "",
          font: { color: titleColor, size: 15, weight: 700 }
        },
        ...spec.layout
      }
    };
  } else {
    const type = spec.type || spec.chart_type || "bar";
    const traceType = type === "line" ? "scatter" : type === "pie" ? "pie" : "bar";
    const trace = traceType === "scatter"
      ? {
          type: "scatter",
          mode: "lines+markers",
          x: spec.x || spec.labels || [],
          y: spec.y || spec.values || [],
          name: spec.name || "",
          line: { color: isLight ? '#0284c7' : '#38bdf8', width: 3 },
          marker: { color: isLight ? '#4f46e5' : '#818cf8', size: 8 }
        }
      : traceType === "pie"
        ? {
            type: "pie",
            labels: spec.labels || spec.x || [],
            values: spec.values || spec.y || [],
            hole: 0.45,
            marker: { colors: themeLayout.colorway }
          }
        : {
            type: "bar",
            x: spec.x || spec.labels || [],
            y: spec.y || spec.values || [],
            name: spec.name || "",
            marker: {
              color: isLight ? '#0284c7' : '#38bdf8',
              opacity: 0.9
            }
          };

    figure = {
      data: [trace],
      layout: {
        ...themeLayout,
        title: {
          text: spec.title || "",
          font: { color: titleColor, size: 15, weight: 700 }
        }
      }
    };
  }

  if (!figure.data?.length) {
    target.innerHTML = '<div class="empty-state"><h3>Chart Data Empty</h3><p>The returned specification did not contain plotted points.</p></div>';
    return;
  }

  Plotly.newPlot(target, figure.data, figure.layout || {}, {
    responsive: true,
    displaylogo: false,
    modeBarButtonsToRemove: ['lasso2d', 'select2d']
  });
}

function renderTable(rows) {
  const head = document.getElementById("table-head");
  const body = document.getElementById("table-body");
  head.replaceChildren();
  body.replaceChildren();

  if (!rows.length) {
    const tr = document.createElement("tr");
    const td = document.createElement("td");
    td.className = "empty-table-cell";
    td.textContent = "No tabular rows returned. Check the chart view above.";
    tr.appendChild(td);
    body.appendChild(tr);
    return;
  }

  const first = rows[0];
  const columns = Array.isArray(first) ? first.map((_, i) => `Column ${i + 1}`) : Object.keys(first);
  const headerRow = document.createElement("tr");
  columns.forEach((column) => {
    const th = document.createElement("th");
    th.textContent = column;
    headerRow.appendChild(th);
  });
  head.appendChild(headerRow);

  rows.forEach((row) => {
    const values = Array.isArray(row) ? row : columns.map((column) => row?.[column]);
    const tr = document.createElement("tr");
    values.forEach((value, idx) => {
      const td = document.createElement("td");
      if (typeof value === "number") {
        const colName = columns[idx]?.toLowerCase() || "";
        if (colName.includes("revenue") || colName.includes("amount") || colName.includes("sales")) {
          td.textContent = `$${value.toLocaleString()}`;
        } else {
          td.textContent = value.toLocaleString();
        }
      } else {
        td.textContent = value == null ? "—" : String(value);
      }
      tr.appendChild(td);
    });
    body.appendChild(tr);
  });
}

function exportCsv() {
  if (!currentRows.length) return;
  const first = currentRows[0];
  const columns = Array.isArray(first) ? first.map((_, i) => `Column ${i + 1}`) : Object.keys(first);
  const lines = [
    columns,
    ...currentRows.map((row) =>
      Array.isArray(row) ? row : columns.map((column) => row?.[column])
    ),
  ];

  const csv = lines
    .map((row) =>
      row
        .map((value) => {
          const text = value == null ? "" : String(value);
          return `"${text.replaceAll('"', '""')}"`;
        })
        .join(",")
    )
    .join("\r\n");

  const blob = new Blob([csv], { type: "text/csv;charset=utf-8;" });
  const url = URL.createObjectURL(blob);
  const anchor = document.createElement("a");
  anchor.href = url;
  anchor.download = `salesforce-analytics-${new Date().toISOString().slice(0, 10)}.csv`;
  anchor.click();
  URL.revokeObjectURL(url);
}
