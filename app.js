const WORKER = String.fromCharCode(104,116,116,112,115,58,47,47,100,97,114,107,45,104,111,114,105,122,111,110,45,97,105,46,100,122,109,105,109,111,51,46,119,111,114,107,101,114,115,46,100,101,118);
let history = [], attData = null, attType = null, attName = "";

function toggleMenu() {
  const m = document.getElementById("plusMenu");
  m.style.display = (m.style.display === "flex") ? "none" : "flex";
}

function quickFill(t) {
  const q = document.getElementById("q");
  q.value = t;
  q.focus();
  document.getElementById("plusMenu").style.display = "none";
}

function clearAttach() {
  attData = null; attType = null; attName = "";
  const fi = document.getElementById("fileInp");
  if (fi) fi.value = "";
  document.getElementById("previewBar").style.display = "none";
}

function addMsg(h, c) {
  const w = document.getElementById("welcomeBox");
  if (w) w.remove();
  const ch = document.getElementById("chat");
  const d = document.createElement("div");
  d.className = "msg " + c;
  d.innerHTML = h;
  ch.appendChild(d);
  ch.scrollTop = ch.scrollHeight;
  return d;
}

async function smartPost(path, payload) {
  try {
    const ctrl = new AbortController();
    const tid = setTimeout(() => ctrl.abort(), 16000);
    const res = await fetch(WORKER + path, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(payload),
      signal: ctrl.signal
    });
    clearTimeout(tid);
    if (res.ok) return await res.json();
  } catch (e) {}
  return null;
}

async function generateUltraImage(rawPrompt) {
  const cleanP = rawPrompt.replace(/صمم لي صورة 8K واقعية لـ?|أنشئ مشهد أنمي سينمائي لـ?|صمم|صورة|ارسم|مشهد/g, "").trim() || "majestic Arabian horse in golden desert sunset, cinematic 8k";
  const enPrompt = cleanP + ", photorealistic, 8k resolution, natural cinematic lighting, sharp focus, masterpiece";

  // 1. المحركات الخارقة المباشرة بدون علامات مائية (FLUX.2 Pro / Imagen 4 Ultra / GPT Image 2.6)
  if (window.puter && puter.ai && puter.ai.txt2img) {
    const ultraModels = [
      "black-forest-labs/flux-2-pro",
      "google/imagen-4.0-ultra",
      "openai/gpt-image-2.6-flare"
    ];
    for (const mdl of ultraModels) {
      try {
        const imgEl = await puter.ai.txt2img(enPrompt, { model: mdl });
        if (imgEl && imgEl.src) return { url: imgEl.src, engine: mdl.split("/").pop() };
      } catch (e) {}
    }
  }


  // 2. الاحتياطي السحابي
  const res = await smartPost("/image", { prompt: enPrompt, width: 1024, height: 1024 });
  if (res && res.image_url && !res.image_url.includes("pollinations")) {
    return { url: res.image_url, engine: res.engine || "FLUX.1-dev" };
  }
  return null;
}

function speakArabic(text) {
  const clean = text.replace(/[*#|_~`(){}<>\/\\•\-:؛،."'!؟]/g, " ").trim();
  const audio = new Audio(WORKER + "/tts?t=" + encodeURIComponent(clean.slice(0, 220)));
  audio.play().catch(() => {
    if ("speechSynthesis" in window) {
      const u = new SpeechSynthesisUtterance(clean);
      u.lang = "ar-SA";
      window.speechSynthesis.speak(u);
    }
  });
}
async function buildCinemaVideo(promptTxt, uploadedImgUrl, targetBubble) {
  targetBubble.innerHTML = "🎬 جاري إخراج المشهد السينمائي وتوليد اللقطات والصوت...";
  let frames = [];

  if (uploadedImgUrl) {
    frames = [uploadedImgUrl];
  } else {
    const shots = [
      promptTxt + ", wide cinematic establishing shot, 8k",
      promptTxt + ", dramatic action close up, dynamic lighting, 8k"
    ];
    for (const s of shots) {
      const res = await generateUltraImage(s);
      if (res && res.url) frames.push(res.url);
    }
  }

  if (!frames.length) {
    targetBubble.innerHTML = "⚠️ تعذر توليد لقطات الفيديو حالياً، حاول وصفاً آخر.";
    return;
  }

  const canvas = document.createElement("canvas");
  canvas.width = 720;
  canvas.height = 720;
  const ctx = canvas.getContext("2d");

  const loadedImgs = await Promise.all(frames.map(src => new Promise(res => {
    const im = new Image();
    im.crossOrigin = "anonymous";
    im.onload = () => res(im);
    im.onerror = () => res(null);
    im.src = src;
  })));
  const validImgs = loadedImgs.filter(Boolean);
  if (!validImgs.length) {
    targetBubble.innerHTML = "⚠️ تعذر معالجة إطارات الفيديو.";
    return;
  }

  const stream = canvas.captureStream(24);
  const recorder = new MediaRecorder(stream, { mimeType: "video/webm" });
  const chunks = [];
  recorder.ondataavailable = e => { if (e.data.size > 0) chunks.push(e.data); };

  recorder.onstop = () => {
    const blob = new Blob(chunks, { type: "video/webm" });
    const vUrl = URL.createObjectURL(blob);
    targetBubble.innerHTML = `
      <div>🎬 تم إنتاج المشهد السينمائي المتحرك:</div>
      <video src="${vUrl}" controls autoplay loop playsinline></video>
      <div class="actions">
        <a class="act-btn" href="${vUrl}" download="DarkHorizon_Cinema.webm">⬇️ تحميل الفيديو</a>
        <button type="button" class="act-btn" onclick="speakArabic('${promptTxt.replace(/'/g, "")}')">🔊 تشغيل الصوت</button>
      </div>`;
    speakArabic(promptTxt);
  };

  recorder.start();
  const totalFrames = 96;
  let f = 0;
  const timer = setInterval(() => {
    const imgIdx = Math.floor((f / totalFrames) * validImgs.length);
    const img = validImgs[Math.min(imgIdx, validImgs.length - 1)];
    const progress = (f % (totalFrames / validImgs.length)) / (totalFrames / validImgs.length);
    const scale = 1.0 + progress * 0.12;
    const w = canvas.width * scale;
    const h = canvas.height * scale;
    const offsetX = (canvas.width - w) / 2;
    const offsetY = (canvas.height - h) * 0.25;
    ctx.clearRect(0, 0, canvas.width, canvas.height);
    ctx.drawImage(img, offsetX, offsetY, w, h);
    f++;
    if (f >= totalFrames) {
      clearInterval(timer);
      recorder.stop();
    }
  }, 1000 / 24);
}

async function send() {
  const inp = document.getElementById("q");
  const val = inp.value.trim();
  if (!val && !attData) return;

  const cd = attData, ct = attType, cn = attName;
  clearAttach();
  inp.value = "";

  let uh = val ? "<div>" + val.replace(/</g, "&lt;") + "</div>" : "";
  if (ct === "img" && cd) uh += "<img src='" + cd + "'>";
  if (ct === "doc") uh += "<div style='font-size:12px;margin-top:4px'>📄 " + cn + "</div>";
  addMsg(uh, "user");

  const isVideo = /(فيديو|مشهد|حرك|أنيميشن|video|animate)/i.test(val) || (ct === "img" && !val);
  const isImg = !isVideo && /(صمم|صورة|صور|ارسم|أنمي|انمي|image|draw)/i.test(val) && ct !== "doc";
  const wait = addMsg("<div class='loader'><span></span><span></span><span></span></div>", "bot");

  if (isVideo) {
    await buildCinemaVideo(val || "مشهد سينمائي متحرك", ct === "img" ? cd : null, wait);
    return;
  }

  if (isImg) {
    const imgObj = await generateUltraImage(val);
    if (imgObj && imgObj.url) {
      wait.innerHTML = `
        <div>🎨 تم التصميم بواسطة <b>${imgObj.engine}</b>:</div>
        <img src="${imgObj.url}" crossorigin="anonymous">
        <div class="actions">
          <a class="act-btn" href="${imgObj.url}" download="DarkHorizon_Ultra.png" target="_blank">⬇️ تحميل الصورة</a>
          <button type="button" class="act-btn" onclick="buildCinemaVideo('${val.replace(/'/g, "")}', '${imgObj.url}', this.closest('.msg'))">🎬 تحويل لفيديو</button>
        </div>`;
    } else {
      wait.innerHTML = "⚠️ تعذر توليد الصورة حالياً، تأكد من الاتصال وحاول مجدداً.";
    }
    return;
  }

  let fp = val;
  if (ct === "doc" && cd) {
    fp = "محتوى الملف (" + cn + "):\n" + String(cd).slice(0, 4000) + "\n\nالمطلوب: " + (val || "لخّص هذا الملف");
  }
  history.push({ role: "user", content: fp });

  let replyText = null;
  const d = await smartPost("/chat", { messages: history.slice(-6) });
  if (d && d.reply) replyText = d.reply;
  else if (window.puter && puter.ai && puter.ai.chat) {
    try {
      const pr = await puter.ai.chat(fp);
      replyText = (typeof pr === "string") ? pr : (pr?.message?.content || String(pr));
    } catch (e) {}
  }

    if (!replyText) {
    try {
      const cr = await fetch("https:" + "//" + "text." + "pollinations" + ".ai/" + encodeURIComponent(fp));
      if (cr.ok) {
        const ct = await cr.text();
        if (ct && ct.length > 2) replyText = ct.trim();
      }
    } catch (e) {}
  }
  if (replyText) {
    history.push({ role: "assistant", content: replyText });
    wait.innerHTML = `
      <div class="txt-body">${replyText.replace(/</g, "&lt;").replace(/\n/g, "<br>")}</div>
      <div class="actions">
        <button type="button" class="act-btn copy-btn">📋 نسخ النص</button>
        <button type="button" class="act-btn tts-btn">🔊 استماع</button>
      </div>`;
    wait.querySelector(".copy-btn").onclick = function() {
      navigator.clipboard.writeText(replyText);
      this.textContent = "✅ تم النسخ";
      setTimeout(() => this.textContent = "📋 نسخ النص", 1500);
    };
    wait.querySelector(".tts-btn").onclick = function() { speakArabic(replyText); };
  } else {
    wait.innerHTML = "⚠️ تعذر الاتصال بالخوادم حالياً، حاول مرة أخرى.";
  }
}

window.addEventListener("DOMContentLoaded", function() {
  document.getElementById("sendBtn").onclick = send;
  document.getElementById("plusBtn").onclick = function(e) { e.stopPropagation(); toggleMenu(); };
  document.getElementById("newBtn").onclick = function() { history = []; clearAttach(); document.getElementById("chat").innerHTML = ""; };
  document.getElementById("clearAttBtn").onclick = clearAttach;
  document.getElementById("q").onkeydown = function(e) { if (e.key === "Enter") { e.preventDefault(); send(); } };
  document.getElementById("pickImgBtn").onclick = function() { attType = "img"; document.getElementById("plusMenu").style.display = "none"; const f = document.getElementById("fileInp"); f.accept = "image/*"; f.click(); };
  document.getElementById("pickDocBtn").onclick = function() { attType = "doc"; document.getElementById("plusMenu").style.display = "none"; const f = document.getElementById("fileInp"); f.accept = ".txt,.py,.js,.json,.csv,.md,.html"; f.click(); };
  document.getElementById("fileInp").onchange = function() {
    const f = this.files;
    if (!f) return;
    attName = f.name;
    const r = new FileReader();
    r.onload = function(e) {
      attData = e.target.result;
      document.getElementById("prevName").textContent = (attType === "img" ? "🖼️ " : "📄 ") + attName;
      document.getElementById("previewBar").style.display = "flex";
    };
    if (attType === "doc") r.readAsText(f); else r.readAsDataURL(f);
  };
  document.querySelectorAll("[data-fill]").forEach(function(el) {
    el.onclick = function() { quickFill(this.getAttribute("data-fill")); };
  });
  document.addEventListener("click", function(e) {
    if (!e.target.closest("#plusBtn") && !e.target.closest("#plusMenu")) {
      document.getElementById("plusMenu").style.display = "none";
    }
  });
});
