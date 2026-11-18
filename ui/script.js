const evalData = {
  "All":      ["14", "14/14", "0/7", "0/3", "4/4"],
  "Dev":      ["10", "10/10", "0/5", "0/2", "3/3"],
  "Held-out": ["4",  "4/4",   "0/2", "0/1", "1/1"]
};

const tableHeaders = [
  "Split", "Cases", "Exact match",
  "False pass (defects)", "False block (valid)", "Incomplete correct"
];

const tabsDiv = document.getElementById("tabs");
const evalTable = document.getElementById("evalTable");

function showSplit(name) {
  const buttons = tabsDiv.querySelectorAll("button");
  buttons.forEach(function (btn) {
    if (btn.textContent === name) {
      btn.classList.add("active");
    } else {
      btn.classList.remove("active");
    }
  });


  evalTable.innerHTML = "";
  const headerRow = evalTable.insertRow();
  tableHeaders.forEach(function (text) {
    const th = document.createElement("th");
    th.textContent = text;
    headerRow.appendChild(th);
  });

 
  const dataRow = evalTable.insertRow();
  const values = [name].concat(evalData[name]);
  values.forEach(function (text) {
    dataRow.insertCell().textContent = text;
  });
}

Object.keys(evalData).forEach(function (name) {
  const btn = document.createElement("button");
  btn.textContent = name;
  btn.addEventListener("click", function () {
    showSplit(name);
  });
  tabsDiv.appendChild(btn);
});

showSplit("All"); 

const barData = [
  { label: "Baseline (steps 1-2)",    score: 10, style: "baseline" },
  { label: "Ablation (workflow off)", score: 12, style: "ablation" },
  { label: "Final",                   score: 14, style: "" }
];

function drawBars() {
  const barsDiv = document.getElementById("bars");

  barData.forEach(function (item) {
    const row = document.createElement("div");
    row.className = "bar-row";

    const label = document.createElement("span");
    label.textContent = item.label;

    const bg = document.createElement("div");
    bg.className = "bar-bg";

    const fill = document.createElement("div");
    fill.className = "bar-fill " + item.style;
    fill.style.width = (item.score / 14) * 100 + "%";
    bg.appendChild(fill);

    const score = document.createElement("b");
    score.textContent = item.score + "/14";

    row.appendChild(label);
    row.appendChild(bg);
    row.appendChild(score);
    barsDiv.appendChild(row);
  });
}

drawBars();

const fileInput = document.getElementById("fileInput");
const outputDiv = document.getElementById("output");

fileInput.addEventListener("change", function (event) {
  outputDiv.innerHTML = "";
  const file = event.target.files[0];
  if (!file) return;

  const reader = new FileReader();

  reader.onload = function () {
    let report;
    try {
      report = JSON.parse(reader.result);
    } catch (error) {
      outputDiv.textContent = "This file is not valid JSON.";
      return;
    }

    const status = report.status || report.result;
    if (typeof status === "string") {
      const pill = document.createElement("span");
      pill.className = "pill " + status;
      pill.textContent = status;
      outputDiv.appendChild(pill);
    }


    let findings = null;
    if (Array.isArray(report)) {
      findings = report;
    } else if (report.findings) {
      findings = report.findings;
    }

    if (!Array.isArray(findings) || findings.length === 0 || typeof findings[0] !== "object") {
      const pre = document.createElement("pre");
      pre.textContent = JSON.stringify(report, null, 2);
      outputDiv.appendChild(pre);
      return;
    }

    showFindingsTable(findings);
  };

  reader.readAsText(file);
});

function showFindingsTable(findings) {
  const columns = [];
  findings.forEach(function (item) {
    Object.keys(item).forEach(function (key) {
      if (!columns.includes(key)) columns.push(key);
    });
  });

  const box = document.createElement("div");
  box.className = "table-box";
  box.style.marginTop = "10px";

  const table = document.createElement("table");
  const headerRow = table.insertRow();
  columns.forEach(function (key) {
    const th = document.createElement("th");
    th.textContent = key;
    headerRow.appendChild(th);
  });

  findings.forEach(function (item) {
    const row = table.insertRow();
    columns.forEach(function (key) {
      let value = item[key];
      if (value === undefined) value = "";
      if (typeof value === "object" && value !== null) value = JSON.stringify(value);
      row.insertCell().textContent = value;
    });
  });

  box.appendChild(table);
  outputDiv.appendChild(box);
}