importScripts("install_config.js", "capture_flow.js");

function extractRenderedArticle() {
  const sourceUrl = new URL(window.location.href);
  sourceUrl.hash = "";
  if (sourceUrl.protocol !== "https:" || sourceUrl.hostname !== "mp.weixin.qq.com" || !sourceUrl.pathname.startsWith("/s/")) {
    throw new Error("UNSUPPORTED_PAGE");
  }

  const article = document.querySelector("#js_content");
  const title = (document.querySelector("#activity-name")?.textContent || document.title || "").trim();
  if (!article || !title) throw new Error("ARTICLE_NOT_RENDERED");

  const clone = article.cloneNode(true);
  clone.querySelectorAll("script,style,noscript,template,iframe,form,button").forEach((node) => node.remove());
  clone.querySelectorAll("img").forEach((image) => {
    const renderedSource = image.getAttribute("data-src") || image.getAttribute("src") || "";
    if (renderedSource) image.setAttribute("src", renderedSource);
  });

  const clean = (value) => value.replace(/[\t\f\v ]+/g, " ").replace(/\n[ \t]+/g, "\n");
  const renderChildren = (node) => Array.from(node.childNodes).map(render).join("");
  const renderTable = (table) => {
    const rows = Array.from(table.querySelectorAll("tr")).map((row) =>
      Array.from(row.querySelectorAll(":scope > th, :scope > td")).map((cell) => clean(cell.innerText || cell.textContent || "").trim())
    ).filter((row) => row.length);
    if (!rows.length) return "";
    const width = Math.max(...rows.map((row) => row.length));
    const normalized = rows.map((row) => [...row, ...Array(width - row.length).fill("")]);
    return `\n\n| ${normalized[0].join(" | ")} |\n| ${Array(width).fill("---").join(" | ")} |\n${normalized.slice(1).map((row) => `| ${row.join(" | ")} |`).join("\n")}\n\n`;
  };
  const render = (node) => {
    if (node.nodeType === Node.TEXT_NODE) return clean(node.textContent || "");
    if (node.nodeType !== Node.ELEMENT_NODE) return "";
    const tag = node.tagName.toLowerCase();
    if (tag === "br") return "\n";
    if (/^h[1-6]$/.test(tag)) return `\n\n${"#".repeat(Number(tag[1]))} ${clean(node.innerText || "").trim()}\n\n`;
    if (tag === "img") {
      const src = node.getAttribute("src") || "";
      const alt = clean(node.getAttribute("alt") || "图片").trim();
      return src ? `\n\n![${alt}](${src})\n\n` : "";
    }
    if (tag === "a") {
      const label = clean(node.innerText || node.textContent || "").trim();
      const href = node.getAttribute("href") || "";
      return href && label ? `[${label}](${href})` : label;
    }
    if (tag === "table") return renderTable(node);
    if (tag === "pre") return `\n\n\`\`\`\n${node.innerText || node.textContent || ""}\n\`\`\`\n\n`;
    if (tag === "blockquote") return `\n\n${clean(node.innerText || "").trim().split("\n").map((line) => `> ${line}`).join("\n")}\n\n`;
    if (tag === "li") return `\n- ${renderChildren(node).trim()}`;
    const content = renderChildren(node);
    if (["p", "div", "section", "article", "ul", "ol"].includes(tag)) return `\n\n${content.trim()}\n\n`;
    return content;
  };

  const markdown = `# ${title}\n\n${renderChildren(clone)}`.replace(/\n{3,}/g, "\n\n").trim();
  if (markdown.length <= title.length + 3) throw new Error("EMPTY_ARTICLE");
  return {source_url: sourceUrl.toString(), title, markdown, source_channel: "rendered_dom"};
}

async function setBadge(text, color) {
  await chrome.action.setBadgeBackgroundColor({color});
  await chrome.action.setBadgeText({text});
}

async function submitCapture(capture) {
  const response = await fetch("http://127.0.0.1:18431/capture", {
    method: "POST",
    headers: {
      "Authorization": `Bearer ${globalThis.LEARNING_ANALYSIS_INSTALL_TOKEN}`,
      "X-Learning-Analysis-Extension-Id": chrome.runtime.id,
      "Content-Type": "application/json",
    },
    body: JSON.stringify(capture),
  });
  if (response.ok) return;
  if (response.status === 401 || response.status === 403) {
    throw new CaptureFlow.CaptureFlowError("AUTH");
  }
  if (response.status === 404 || response.status === 408 || response.status === 409) {
    throw new CaptureFlow.CaptureFlowError("TIME");
  }
  if (response.status === 400 || response.status === 413) {
    throw new CaptureFlow.CaptureFlowError("PAGE");
  }
  throw new CaptureFlow.CaptureFlowError("SEND");
}

chrome.action.onClicked.addListener(async (tab) => {
  try {
    if (!tab.id) throw new Error("NO_ACTIVE_TAB");
    await setBadge("WAIT", "#1a73e8");
    const sourceUrl = CaptureFlow.normalizeSourceUrl(tab.url);
    await CaptureFlow.runCaptureFlow(sourceUrl, {
      token: globalThis.LEARNING_ANALYSIS_INSTALL_TOKEN,
      extensionId: chrome.runtime.id,
      extractFn: async () => {
        const [{result}] = await chrome.scripting.executeScript({
          target: {tabId: tab.id},
          func: extractRenderedArticle,
        });
        return result;
      },
      submitFn: submitCapture,
    });
    await setBadge("OK", "#188038");
  } catch (error) {
    const code = error instanceof CaptureFlow.CaptureFlowError ? error.code : "SEND";
    const badge = ["PAGE", "AUTH", "URL", "TIME", "SEND"].includes(code) ? code : "SEND";
    await setBadge(badge, "#b3261e");
  }
});
