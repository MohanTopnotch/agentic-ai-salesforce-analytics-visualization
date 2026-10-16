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
const chartTypePicker = document.querySelector(".chart-type-picker");

let currentRows = [];
let currentResponse = null;
let selectedChartType = null;
let chartRenderVersion = 0;

document.querySelectorAll("[data-chart-type]").forEach((button) => {
  button.addEventListener("click", () => {
    selectedChartType = button.dataset.chartType;
    const data = currentResponse?.data || {};
    const chart = data.chart || data.visualization || data.visualization_spec;
    if (chart) renderChart(chart, selectedChartType);
  });
});

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
    if (chart) renderChart(chart, selectedChartType);
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

function readableField(field) {
  if (!field) return "Metric";
  const normalized = String(field).toLowerCase().replaceAll("_", "");
  const labels = {
    annualrevenue: "Annual Revenue",
    revenue: "Revenue",
    amount: "Sales Amount",
    region: "Region",
    industry: "Industry",
    leadsource: "Lead Source",
    stagename: "Stage",
    closedate: "Month",
    month: "Month",
  };
  return labels[normalized] || String(field).replaceAll("_", " ");
}

function findRows(payload) {
  const candidates = [
    payload?.data?.calculated_data,
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
  let serverReportedSuccess = false;
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
    serverReportedSuccess = response.ok && payload.status === "success";

    if (!response.ok) {
      throw new Error(payload?.detail || `API Request failed with HTTP status ${response.status}.`);
    }

    if (payload.status !== "success") {
      updateAudit(payload);
      if (payload.status === "needs_clarification") {
        renderClarification(payload.clarification_question || payload.data?.clarification_question);
        setStatusState("idle", "Clarification needed");
        return;
      }
      throw new Error(payload.message || payload.error_code || "Workflow failed during execution.");
    }

    updateAudit(payload);
    renderResults(payload);
    setStatusState("idle", "Analysis completed");
  } catch (error) {
    if (serverReportedSuccess) {
      showError(`The analysis succeeded, but the results could not be fully displayed: ${error.message}`);
      setStatusState("err", "Display error");
    } else {
      showError(error.message);
      setStatusState("err", "Analysis failed");
      currentRows = [];
      exportButton.disabled = true;
      if (kpiBanner) kpiBanner.hidden = true;
    }
  } finally {
    runButton.disabled = false;
    if (btnSpinner) btnSpinner.hidden = true;
  }
}

function updateAudit(payload) {
  const verified = payload.verified === true;
  const needsClarification = payload.status === "needs_clarification";
  const badge = document.getElementById("verification-badge");
  if (badge) {
    badge.className = `badge ${needsClarification ? "neutral" : verified ? "pass" : "fail"}`;
    badge.textContent = needsClarification
      ? "Needs clarification"
      : verified ? "✓ Verified Clean" : "✕ Not verified / Failed";
  }
  
  setText("request-id", payload.request_id);
  setText(
    "verified-value",
    needsClarification
      ? "No query executed"
      : verified ? "Grouped total matches raw total" : "Verification flagged discrepancy",
  );
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
  selectedChartType = null;

  currentRows = findRows(payload);
  renderTable(currentRows);
  updateKPIs(currentRows);
  exportButton.disabled = currentRows.length === 0;
  renderAnswer(data, chart, currentRows);
  renderChart(chart);
}

function renderAnswer(data, chart, rows) {
  const list = document.getElementById("analysis-insights");
  if (list) list.replaceChildren();

  const insights = Array.isArray(data.insights)
    ? data.insights
    : Array.isArray(data.insights?.insights)
      ? data.insights.insights
      : [];
  insights.forEach((insight) => {
    if (typeof insight !== "string" || !insight.trim()) return;
    const item = document.createElement("li");
    item.textContent = insight;
    list?.appendChild(item);
  });
  if (list) list.hidden = list.childElementCount === 0;

  const keys = Object.keys(rows[0] || {});
  const metric = chart?.y_field || keys.find((key) => (
    chart?.data?.[0]?.name &&
    key.toLowerCase() === chart.data[0].name.toLowerCase()
  )) || keys.find((key) => (
    rows.every((row) => row[key] != null && row[key] !== "" && Number.isFinite(Number(row[key])))
  ));
  const dimension = chart?.x_label || chart?.x_field || keys.find((key) => key !== metric);
  const sum = metric && rows.length
    ? rows.reduce((total, row) => total + Number(row[metric] || 0), 0)
    : null;
  const isCurrency = metric && ["revenue", "amount", "sales"].some(
    (term) => metric.toLowerCase().includes(term),
  );
  const dimensionName = dimension?.toLowerCase();
  const pluralDimension = {
    industry: "industries",
    month: "months",
    region: "regions",
    stage: "stages",
    "lead source": "lead sources",
  };
  const dimensionText = dimensionName
    ? rows.length === 1
      ? dimensionName
      : pluralDimension[dimensionName] || `${dimensionName}s`
    : "";
  const totalLabel = sum === null || !Number.isFinite(sum)
    ? "No matching records were returned."
    : `Verified ${chart?.y_label || readableField(metric)}: ${
        isCurrency ? "$" : ""
      }${sum.toLocaleString("en-US", { maximumFractionDigits: 2 })}${
        dimensionText
          ? ` across ${rows.length} ${dimensionText}`
          : ""
      }.`;
  setText("analysis-summary", totalLabel);
}

function renderClarification(message) {
  currentRows = [];
  selectedChartType = null;
  exportButton.disabled = true;
  if (kpiBanner) kpiBanner.hidden = true;
  if (tableRowBadge) tableRowBadge.textContent = "0 rows";
  renderTable([]);
  updateChartTypeButtons("bar", false);
  if (chartTypePicker) chartTypePicker.hidden = true;
  const target = document.getElementById("chart");
  if (target && typeof Plotly !== "undefined") Plotly.purge(target);
  if (target) {
    target.innerHTML = '<div class="empty-state"><h3>Let’s clarify your analysis</h3><p>Choose a supported Salesforce question to run a verified query.</p></div>';
  }
  const list = document.getElementById("analysis-insights");
  if (list) {
    list.replaceChildren();
    list.hidden = true;
  }
  setText(
    "analysis-summary",
    message || "I couldn’t safely match that question to a supported Salesforce analysis. Try one of the suggested prompts.",
  );
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
  if (kpiCount) kpiCount.textContent = rows.length.toLocaleString("en-US");

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
        ? `$${sum.toLocaleString("en-US", { maximumFractionDigits: 2 })}`
        : sum.toLocaleString("en-US");
    } else {
      kpiSum.textContent = `${rows.length} groups`;
    }
  }
}

function renderChart(spec, requestedType = null) {
  const renderVersion = ++chartRenderVersion;
  const target = document.getElementById("chart");
  if (!target) return;
  if (!spec || typeof spec !== "object") {
    if (chartTypePicker) chartTypePicker.hidden = true;
    target.innerHTML = '<div class="empty-state"><h3>No Chart Specification</h3><p>Query completed but returned tabular data only.</p></div>';
    return;
  }

  const sourceData = Array.isArray(spec.data) ? spec.data : [];
  const sourceTrace = sourceData.find((trace) => trace.type !== "table") || (
    spec.x || spec.y || spec.labels || spec.values
      ? {
          x: spec.x || spec.labels || [],
          y: spec.y || spec.values || [],
          name: spec.name || "",
        }
      : null
  );
  const chartType = normalizeChartType(
    requestedType || spec.chart_type || spec.type || "bar",
  );
  const canVisualize = Boolean(
    sourceTrace && sourceTrace.type !== "table" &&
    (sourceTrace.x || sourceTrace.labels) &&
    (sourceTrace.y || sourceTrace.values),
  );
  if (chartTypePicker) chartTypePicker.hidden = !canVisualize;
  updateChartTypeButtons(chartType, canVisualize);

  if (!canVisualize) {
    target.innerHTML = '<div class="empty-state"><h3>Tabular Results</h3><p>This result is best viewed in the verified data table below.</p></div>';
    return;
  }
  if (typeof Plotly === "undefined") {
    target.innerHTML = '<div class="empty-state"><h3>Chart library unavailable</h3><p>Reload the page or check your connection to load the interactive chart.</p></div>';
    return;
  }

  const labels = sourceTrace.labels || sourceTrace.x || [];
  const rawValues = sourceTrace.values || sourceTrace.y || [];
  if (!labels.length || labels.length !== rawValues.length) {
    target.innerHTML = '<div class="empty-state"><h3>Chart data is incomplete</h3><p>The chart needs one label for each verified metric value.</p></div>';
    return;
  }

  const values = rawValues.map(Number);
  const resultRows = findRows(currentResponse || {});
  const rowKeys = Object.keys(resultRows[0] || {});
  const metricField = spec.y_field || rowKeys.find((key) => (
    sourceTrace.name && key.toLowerCase() === sourceTrace.name.toLowerCase()
  )) || rowKeys.find((key) => (
    resultRows.every((row) => (
      row[key] != null && row[key] !== "" && Number.isFinite(Number(row[key]))
    ))
  ));
  const dimensionField = spec.x_field || rowKeys.find((key) => key !== metricField);
  const metricLabel = spec.y_label || readableField(metricField || sourceTrace.name);
  const dimensionLabel = spec.x_label || readableField(dimensionField);
  const isCurrency = ["revenue", "amount", "sales"].some(
    (term) => String(metricField || metricLabel).toLowerCase().includes(term),
  );
  if (values.some((value) => !Number.isFinite(value))) {
    target.innerHTML = '<div class="empty-state"><h3>Chart data is invalid</h3><p>One or more metric values could not be plotted.</p></div>';
    return;
  }
  if (["pie", "donut"].includes(chartType) && values.some((value) => value < 0)) {
    target.innerHTML = '<div class="empty-state"><h3>Pie charts need non-negative values</h3><p>Choose Bar or Line to compare data that includes negative values.</p></div>';
    return;
  }
  if (["pie", "donut"].includes(chartType) && values.every((value) => value === 0)) {
    target.innerHTML = '<div class="empty-state"><h3>No positive values to display</h3><p>Choose Bar or Line to inspect the verified zero totals.</p></div>';
    return;
  }

  const isLight = document.documentElement.getAttribute("data-theme") === "light";
  const themeLayout = {
    paper_bgcolor: "transparent",
    plot_bgcolor: "transparent",
    font: {
      family: "'Plus Jakarta Sans', -apple-system, sans-serif",
      color: isLight ? "#475569" : "#94a3b8",
      size: 12,
    },
    colorway: isLight
      ? ["#0284c7", "#6366f1", "#059669", "#db2777", "#d97706", "#7c3aed"]
      : ["#38bdf8", "#818cf8", "#34d399", "#f472b6", "#fbbf24", "#a78bfa", "#2dd4bf"],
    xaxis: {
      gridcolor: isLight ? "rgba(0, 0, 0, 0.06)" : "rgba(255, 255, 255, 0.06)",
      zerolinecolor: isLight ? "rgba(0, 0, 0, 0.12)" : "rgba(255, 255, 255, 0.1)",
      tickfont: { color: isLight ? "#475569" : "#94a3b8" },
    },
    yaxis: {
      gridcolor: isLight ? "rgba(0, 0, 0, 0.06)" : "rgba(255, 255, 255, 0.06)",
      zerolinecolor: isLight ? "rgba(0, 0, 0, 0.12)" : "rgba(255, 255, 255, 0.1)",
      tickfont: { color: isLight ? "#475569" : "#94a3b8" },
    },
    margin: { t: 48, r: 24, b: 64, l: 72 },
    autosize: true,
  };

  const titleColor = isLight ? '#0f172a' : '#f8fafc';
  const trace = chartType === "pie" || chartType === "donut"
    ? {
        type: "pie",
        labels,
        values,
        hole: chartType === "donut" ? 0.52 : 0,
        textinfo: "label+percent",
        sort: false,
        marker: { colors: themeLayout.colorway },
        hovertemplate: "%{label}<br>%{value:,.2f} (%{percent})<extra></extra>",
      }
    : chartType === "line"
      ? {
          type: "scatter",
          mode: "lines+markers",
          x: labels,
          y: values,
          name: metricLabel,
          line: { color: isLight ? "#0284c7" : "#38bdf8", width: 3 },
          marker: { color: isLight ? "#4f46e5" : "#818cf8", size: 8 },
          hovertemplate: "%{x}<br>%{y:,.2f}<extra></extra>",
        }
      : {
          type: "bar",
          x: labels,
          y: values,
          name: metricLabel,
          marker: { color: isLight ? "#0284c7" : "#38bdf8", opacity: 0.9 },
          hovertemplate: "%{x}<br>%{y:,.2f}<extra></extra>",
        };

  const layout = {
    ...themeLayout,
    ...spec.layout,
    title: {
      text: metricField && dimensionField
        ? `${metricLabel} by ${dimensionLabel}`
        : spec.layout?.title?.text || spec.layout?.title || spec.title || "",
      font: { color: titleColor, size: 16, weight: 700 },
    },
  };
  if (isCurrency && layout.yaxis) {
    layout.yaxis = {
      ...layout.yaxis,
      tickformat: ",.0f",
      tickprefix: "$",
      separatethousands: true,
    };
  }
  if (chartType === "pie" || chartType === "donut") {
    delete layout.xaxis;
    delete layout.yaxis;
    layout.showlegend = true;
    layout.margin = { t: 48, r: 24, b: 32, l: 24 };
  }

  Plotly.purge(target);
  target.replaceChildren();
  Plotly.newPlot(target, [trace], layout, {
    responsive: true,
    displaylogo: false,
    modeBarButtonsToRemove: ["lasso2d", "select2d"],
  }).then(() => {
    if (renderVersion !== chartRenderVersion) Plotly.purge(target);
  }).catch(() => {
    if (renderVersion === chartRenderVersion) {
      target.innerHTML = '<div class="empty-state"><h3>Chart could not be rendered</h3><p>The verified table below remains available for these results.</p></div>';
    }
  });
}

function normalizeChartType(type) {
  const normalized = String(type).toLowerCase();
  if (normalized === "doughnut" || normalized === "circular") return "donut";
  if (["bar", "line", "pie", "donut"].includes(normalized)) return normalized;
  return "bar";
}

function updateChartTypeButtons(activeType, enabled) {
  document.querySelectorAll("[data-chart-type]").forEach((button) => {
    button.setAttribute(
      "aria-pressed",
      String(enabled && button.dataset.chartType === activeType),
    );
    button.disabled = !enabled;
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
    th.textContent = readableField(column);
    headerRow.appendChild(th);
  });
  head.appendChild(headerRow);

  rows.forEach((row) => {
    const values = Array.isArray(row) ? row : columns.map((column) => row?.[column]);
    const tr = document.createElement("tr");
    values.forEach((value, idx) => {
      const td = document.createElement("td");
      const colName = columns[idx]?.toLowerCase() || "";
      const isCurrency = ["revenue", "amount", "sales"].some((term) => colName.includes(term));
      const isMetric = isCurrency || colName.includes("count") || colName.includes("employees");
      const numericValue = typeof value === "number"
        ? value
        : isMetric && value != null && value !== "" && Number.isFinite(Number(value))
          ? Number(value)
          : null;

      if (numericValue !== null) {
        if (isCurrency) {
          td.textContent = `$${numericValue.toLocaleString()}`;
        } else {
          td.textContent = numericValue.toLocaleString();
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
