(function(){
  var hist = [];
  try{ hist = JSON.parse(localStorage.getItem("dh_hist") || "[]"); }catch(e){ hist = []; }
  var sl = String.fromCharCode(47);
  var EDGE = "https:" + sl + sl + "hidden-bread-95eb.dz30007000.workers.dev";
  var q = document.getElementById("q");

  function saveH(){ try{ localStorage.setItem("dh_hist", JSON.stringify(hist.slice(-20))); }catch(e){} }
  hist.forEach(function(m){ window.DH_UI.addMsg(m.role === "user" ? "USER" : "AI", m.content); });

  function getDims(){
    var el = document.getElementById("aspectSel");
    var v = el ? el.value : "1:1";
    if(v === "16:9") return {w: 960, h: 540};
    if(v === "9:16") return {w: 540, h: 960};
    return {w: 768, h: 768};
  }

  function playClashSFX(actx, dest){
    try{
      var osc = actx.createOscillator(), g = actx.createGain();
      osc.type = "sawtooth"; osc.frequency.setValueAtTime(920, actx.currentTime);
      osc.frequency.exponentialRampToValueAtTime(110, actx.currentTime + 0.28);
      g.gain.setValueAtTime(0.18, actx.currentTime);
      g.gain.exponentialRampToValueAtTime(0.001, actx.currentTime + 0.3);
      osc.connect(g); g.connect(dest); g.connect(actx.destination);
      osc.start(); osc.stop(actx.currentTime + 0.3);
    }catch(e){}
  }

  async function askAI(msgs, imgData){
    var r = await fetch(EDGE + sl + "chat", {
      method: "POST", headers: {"Content-Type": "application/json"},
      body: JSON.stringify({messages: msgs.slice(-8), image: imgData || null})
    });
    if(r.ok){ var d = await r.json(); if(d && d.reply) return d.reply; }
    throw new Error("الخادم مشغول، أعد المحاولة");
  }
  function renderStudioScene(ctx, w, h, t, lp, idx, sc, talking, pts){
    ctx.save();
    // 1. كاميرا سينمائية تقترب من المتحدث وتهتز عند الذروة
    var focusX = (idx % 2 === 0) ? w * 0.36 : w * 0.64;
    var zoom = 1.06 + Math.sin(lp * Math.PI) * 0.14;
    var shake = (lp < 0.12) ? Math.sin(t * 60) * 7 : 0;
    ctx.translate(w/2 + shake, h/2 + shake);
    ctx.scale(zoom, zoom);
    ctx.translate(-focusX * 0.35 - w * 0.325, -h * 0.5);

    // 2. سماء وإضاءة حجمية متعددة الطبقات
    var sky = ctx.createLinearGradient(0, 0, 0, h);
    if(idx % 2 === 0){ sky.addColorStop(0, "#050b1a"); sky.addColorStop(0.6, "#13294b"); sky.addColorStop(1, "#1e3a5f"); }
    else { sky.addColorStop(0, "#14071c"); sky.addColorStop(0.6, "#3b0d36"); sky.addColorStop(1, "#5c1638"); }
    ctx.fillStyle = sky; ctx.fillRect(0, 0, w, h);

    // قمر عملاق وهالة ضوئية
    var moonX = w * 0.5 + Math.sin(t * 0.3) * 25, moonY = h * 0.24;
    var aura = ctx.createRadialGradient(moonX, moonY, 10, moonX, moonY, w * 0.28);
    aura.addColorStop(0, "rgba(255,250,230,0.95)"); aura.addColorStop(0.3, "rgba(147,197,253,0.25)"); aura.addColorStop(1, "rgba(0,0,0,0)");
    ctx.fillStyle = aura; ctx.fillRect(0, 0, w, h);

    // جبال وقمم معمارية يابانية
    ctx.fillStyle = "#090e1a";
    ctx.beginPath(); ctx.moveTo(0, h);
    for(var x = 0; x <= w; x += 30){
      ctx.lineTo(x, h * 0.64 - Math.sin(x * 0.012 + idx) * 42 - Math.cos(x * 0.025) * 20);
    }
    ctx.lineTo(w, h); ctx.fill();
    ctx.fillStyle = "#04070e"; ctx.fillRect(0, h * 0.74, w, h * 0.26);
    function drawHeroUnit(cx, cy, dir, capeCol, hairCol, eyeCol, isActive, actT){
      ctx.save();
      var hover = Math.sin(actT * 4.2) * (isActive ? 10 : 4);
      ctx.translate(cx, cy - hover);
      ctx.scale(dir, 1);

      // هالة طاقة حول الشخصية المتحدثة
      if(isActive){
        var hg = ctx.createRadialGradient(0, -50, 5, 0, -50, 115);
        hg.addColorStop(0, eyeCol + "55"); hg.addColorStop(1, "rgba(0,0,0,0)");
        ctx.fillStyle = hg; ctx.beginPath(); ctx.arc(0, -50, 115, 0, Math.PI*2); ctx.fill();
      }

      // عباءة متموجة بتظليل مزدوج
      ctx.fillStyle = capeCol;
      ctx.beginPath(); ctx.moveTo(-14, -78);
      ctx.bezierCurveTo(-65, -70, -85, -15 + Math.sin(actT*9)*16, -105, 22);
      ctx.lineTo(-18, -5); ctx.fill();

      // الأرجل بوضعية قتالية
      ctx.strokeStyle = "#0f172a"; ctx.lineWidth = 15; ctx.lineCap = "round";
      ctx.beginPath(); ctx.moveTo(-10, -14); ctx.lineTo(-28, 48); ctx.stroke();
      ctx.beginPath(); ctx.moveTo(12, -14); ctx.lineTo(34, 48); ctx.stroke();

      // الجذع والدرع بتظليل Cel-Shading
      ctx.fillStyle = isActive ? "#f8fafc" : "#cbd5e1";
      ctx.beginPath(); ctx.roundRect(-22, -84, 44, 72, 12); ctx.fill();
      ctx.fillStyle = capeCol; ctx.fillRect(-22, -52, 44, 14);

      // الرأس والوجه الأنمي
      ctx.save();
      ctx.translate(0, -110 + (isActive && talking ? Math.sin(actT * 24) * 2.5 : 0));
      ctx.fillStyle = "#ffedd5";
      ctx.beginPath(); ctx.moveTo(-22, -16); ctx.lineTo(22, -16); ctx.lineTo(20, 10); ctx.lineTo(4, 24); ctx.lineTo(-18, 12); ctx.fill();

      // عيون أنمي مفصلة ببؤبؤ ولمعان
      var blink = (Math.sin(actT * 2.1) > 0.96) ? 1.5 : 8;
      ctx.fillStyle = "#ffffff"; ctx.fillRect(4, -5, 12, blink);
      ctx.fillStyle = eyeCol; ctx.fillRect(8, -5, 7, blink);
      if(blink > 2){ ctx.fillStyle = "#ffffff"; ctx.fillRect(11, -4, 3, 3); }

      // فم متزامن مع الصوت (Lip-Sync)
      ctx.fillStyle = "#be123c";
      var mOpen = (isActive && talking) ? (3 + Math.abs(Math.sin(actT * 28)) * 7) : 2;
      ctx.beginPath(); ctx.ellipse(10, 12, 5, mOpen * 0.5, 0, 0, Math.PI*2); ctx.fill();

      // شعر أنمي متعدد الخصلات
      ctx.fillStyle = hairCol;
      ctx.beginPath(); ctx.moveTo(-26, -6); ctx.lineTo(-22, -40); ctx.lineTo(-6, -26);
      ctx.lineTo(4, -44); ctx.lineTo(16, -24); ctx.lineTo(29, -30); ctx.lineTo(25, -2);
      ctx.lineTo(10, -12); ctx.lineTo(-4, -4); ctx.fill();
      ctx.restore();

      // الذراع والسيف المتوهج + أثر Sakuga
      ctx.save();
      ctx.translate(14, -68);
      var sw = isActive ? (Math.sin(actT * 6.5) * 1.1 - 0.35) : -0.4;
      ctx.rotate(sw);
      ctx.strokeStyle = "#ffedd5"; ctx.lineWidth = 11;
      ctx.beginPath(); ctx.moveTo(0, 0); ctx.lineTo(42, 0); ctx.stroke();
      ctx.strokeStyle = eyeCol; ctx.lineWidth = 5; ctx.shadowColor = eyeCol; ctx.shadowBlur = 18;
      ctx.beginPath(); ctx.moveTo(42, 0); ctx.lineTo(148, -14); ctx.stroke();
      if(isActive){
        ctx.strokeStyle = "rgba(255,255,255,0.4)"; ctx.lineWidth = 18;
        ctx.beginPath(); ctx.arc(42, 0, 95, -0.55, 0.25); ctx.stroke();
      }
      ctx.restore();
      ctx.restore();
    }

    drawHeroUnit(w * 0.32, h * 0.68, 1, "#0284c7", "#0f172a", "#38bdf8", idx % 2 === 0, t);
    drawHeroUnit(w * 0.68, h * 0.68, -1, "#dc2626", "#f1f5f9", "#fb7185", idx % 2 === 1, t + 1.5);
    ctx.restore();

    // 3. شرارات طاقة ومؤثر وميض الصدمة
    pts.forEach(function(pt){
      pt.x += pt.vx; pt.y += pt.vy;
      if(pt.y < 0) pt.y = h; if(pt.x < 0) pt.x = w; if(pt.x > w) pt.x = 0;
      ctx.fillStyle = "rgba(253, 224, 71, " + pt.a + ")";
      ctx.beginPath(); ctx.arc(pt.x, pt.y, pt.r, 0, Math.PI*2); ctx.fill();
    });
    if(lp < 0.08){
      ctx.fillStyle = "rgba(255,255,255," + (0.45 * (1 - lp/0.08)) + ")";
      ctx.fillRect(0, 0, w, h);
    }
  }
  window.DH_ENGINE = {
    reset: function(){ hist = []; },
    send: async function(t){
      q.value = "";
      var cData = window.DH_UI.attData, cType = window.DH_UI.attType, cName = window.DH_UI.attName;
      window.DH_UI.clearAttachment();
      window.DH_UI.addMsg("USER", t || ("📎 ملف: " + cName), cType === "img" ? {user_img: cData} : null);
      var wait = window.DH_UI.addMsg("AI", "⚡ جاري التنفيذ...");
      var low = t.toLowerCase();
      var isAnime = low.indexOf("انمي") !== -1 || low.indexOf("أنمي") !== -1 || low.indexOf("كرتون") !== -1 || low.indexOf("anime") !== -1;

      try{
        if(low.indexOf("فيديو") !== -1 || low.indexOf("مقطع") !== -1 || low.indexOf("تحريك") !== -1 || low.indexOf("انمي") !== -1 || low.indexOf("أنمي") !== -1 || low.indexOf("حلقة") !== -1 || low.indexOf("video") !== -1){
          var actx = new (window.AudioContext || window.webkitAudioContext)();
          if(actx.state === "suspended") await actx.resume();
          var dest = actx.createMediaStreamDestination();
          var bgmGain = actx.createGain(); bgmGain.gain.value = 0.04; bgmGain.connect(dest); bgmGain.connect(actx.destination);
          var bgmOscs = [110.0, 164.81, 220.0].map(function(fq){ var o = actx.createOscillator(); o.type = "sine"; o.frequency.value = fq; o.connect(bgmGain); o.start(); return o; });

          var matchSec = t.match(/(\d+)\s*(ثاني|ثوان|sec|s)/i);
          var targetSec = matchSec ? Math.max(parseInt(matchSec.shift(), 10), 8) : 14;
          var cleanV = t.replace(/صمم لي فيديو|صمم فيديو|اصنع فيديو|انشئ فيديو|اصنع حلقة|فيديو|مقطع|\d+\s*(ثاني|ثوان|sec|s)/gi, "").trim() || "مواجهة بين البطل سيف والخصم كايتو";

          wait.innerHTML = "📝 <b>1/3:</b> تأليف السيناريو وتوزيع الأدوار...";
          var sp = 'أنت مخرج استوديو أنمي. اكتب 4 سطور حوارية مشوقة بالعربية الفصحى عن: "' + cleanV + '". التزم حرفياً بهذا التنسيق بدون ترقيم:\nاسم_الشخصية | الصوت(onyx أو nova أو echo) | الحوار_بالعربية(6 كلمات كحد أقصى)';
          var rawScript = await askAI([{role: "user", content: sp}]);
          var scenes = rawScript.split("\n").map(function(line){
            var p = line.split("|").map(function(x){ return x.replace(/[*#]/g, "").trim(); });
            if(p.length >= 3){
              var s0 = p.shift(), s1 = p.shift().toLowerCase(), s2 = p.shift();
              if(s1 !== "onyx" && s1 !== "nova" && s1 !== "echo") s1 = "onyx";
              if(s0 && s2) return {speaker: s0, voice: s1, line: s2};
            }
            return null;
          }).filter(Boolean).slice(0, 4);

          if(!scenes.length){
            scenes = [
              {speaker: "سيف", voice: "echo", line: "لن أسمح لك بتدمير هذا العالم!"},
              {speaker: "كايتو", voice: "onyx", line: "قوتك لن تصمد أمام نصلي المظلم!"},
              {speaker: "سيف", voice: "echo", line: "استعد للضربة القاضية الآن!"},
              {speaker: "كايتو", voice: "onyx", line: "مستحيل! هذه الطاقة لا تصدق!"}
            ];
          }

          wait.innerHTML = "🎙️ <b>2/3:</b> تسجيل الدبلجة العربية والمؤثرات الصوتية...";
          var audioClips = await Promise.all(scenes.map(function(sc){
            return fetch(EDGE + sl + "tts?t=" + encodeURIComponent(sc.line) + "&v=" + sc.voice)
              .then(function(r){ return r.ok ? r.arrayBuffer() : null; })
              .then(function(buf){ return (buf && buf.byteLength > 200) ? actx.decodeAudioData(buf) : null; })
              .catch(function(){ return null; });
          }));

          wait.innerHTML = "🎬 <b>3/3:</b> إخراج المشهد بالكاميرا السينمائية وتحريك الشخصيات...";
          var dm = getDims();
          var hud = document.createElement("canvas"); hud.width = dm.w; hud.height = dm.h;
          var hctx = hud.getContext("2d");
          var vStream = hud.captureStream(30); dest.stream.getAudioTracks().forEach(function(tr){ vStream.addTrack(tr); });
          var mimeOut = MediaRecorder.isTypeSupported("video/mp4") ? "video/mp4" : "video/webm";
          var rec = new MediaRecorder(vStream, {mimeType: mimeOut}), chunks = [];
          rec.ondataavailable = function(e){ if(e.data.size > 0) chunks.push(e.data); };
          var doneRec = new Promise(function(res){ rec.onstop = function(){ bgmOscs.forEach(function(o){try{o.stop();}catch(ex){}}); try{actx.close();}catch(ex){} res(URL.createObjectURL(new Blob(chunks, {type: mimeOut}))); }; });
          rec.start();

          var pts = Array.from({length: 45}, function(){ return {x: Math.random()*dm.w, y: Math.random()*dm.h, r: 1.5+Math.random()*2.5, vx: (Math.random()-0.5)*1.5, vy: -0.8-Math.random()*1.5, a: 0.45+Math.random()*0.5}; });
          var totalFrames = Math.max(targetSec, scenes.length * 4) * 30, perScene = Math.floor(totalFrames / scenes.length), fc = 0, lastSpokenIdx = -1;

          await new Promise(function(res){
            var tm = setInterval(function(){
              var idx = Math.min(Math.floor(fc / perScene), scenes.length - 1), lp = (fc % perScene) / perScene;
              if(idx !== lastSpokenIdx){
                lastSpokenIdx = idx; window._isTalking = false;
                playClashSFX(actx, dest);
                if(audioClips[idx]){ try{ var src = actx.createBufferSource(); src.buffer = audioClips[idx]; src.connect(dest); src.connect(actx.destination); window._isTalking = true; src.onended = function(){ window._isTalking = false; }; src.start(0); }catch(ex){} }
              }
              renderStudioScene(hctx, dm.w, dm.h, fc * 0.033, lp, idx, scenes[idx], window._isTalking, pts);
              var curSc = scenes[idx], grad = hctx.createLinearGradient(0, dm.h*0.72, 0, dm.h); grad.addColorStop(0, "rgba(0,0,0,0)"); grad.addColorStop(1, "rgba(0,0,0,0.94)");
              hctx.fillStyle = grad; hctx.fillRect(0, dm.h*0.72, dm.w, dm.h*0.28);
              hctx.fillStyle = curSc.voice === "nova" ? "#f472b6" : (curSc.voice === "echo" ? "#38bdf8" : "#fbbf24");
              hctx.fillRect(dm.w/2 - 110, dm.h*0.78, 220, 34); hctx.font = "bold 19px sans-serif"; hctx.textAlign = "center"; hctx.fillStyle = "#090a0f"; hctx.fillText("🎙️ " + curSc.speaker, dm.w/2, dm.h*0.78 + 24);
              hctx.font = "bold 28px sans-serif"; hctx.fillStyle = "#ffffff"; hctx.fillText(curSc.line, dm.w/2, dm.h*0.91);
              if(++fc >= totalFrames){ clearInterval(tm); rec.stop(); res(); }
            }, 33);
          });

          var fbVid = await doneRec, castSummary = scenes.map(function(x){ return "• <b>" + x.speaker + ":</b> " + x.line; }).join("<br>");
          wait.remove(); window.DH_UI.addMsg("AI", "🎬 <b>تم إنتاج المشهد الاستوديو بنجاح (تحريك مفاصل + كاميرا + مؤثرات صوتية):</b><br><br>" + castSummary, {vid: fbVid});
        } else if((low.indexOf("صورة") !== -1 || low.indexOf("صور") !== -1 || low.indexOf("ارسم") !== -1 || low.indexOf("صمم") !== -1 || low.indexOf("image") !== -1) && cType !== "img"){
          var cleanT = t.replace(/صمم لي صور|صمم لي صورة|صمم صورة|ارسم لي|ارسم|صور|صورة/gi, "").trim();
          var en = cleanT.length > 2 ? await askAI([{role: "user", content: "Write a short 8K English photo prompt (max 15 words, ONLY English): " + cleanT}]) : "majestic Arabian horse in golden Sahara desert at sunset, 8k";
          en = en.replace(/[^a-zA-Z0-9 ,.-]/g, "").trim().slice(0, 140) || "cinematic 8k landscape";
          if(isAnime) en += ", masterpiece Japanese anime key visual, Studio Ghibli style, 8k";
          var ir = await fetch(EDGE + sl + "image", {method: "POST", headers: {"Content-Type": "application/json"}, body: JSON.stringify({prompt: en, width: getDims().w, height: getDims().h})});
          var iData = await ir.json().catch(function(){ return {}; });
          if(!ir.ok || !iData.image_url) throw new Error("فشل توليد الصورة");
          wait.remove(); window.DH_UI.addMsg("AI", "🎨 <b>تم تصميم الصورة بدقة عالية:</b>", {img: iData.image_url});
        } else {
          var fullT = cType === "doc" ? (t + "\n\n[محتوى الملف " + cName + "]:\n" + String(cData).slice(0, 4000)) : (t || "مرحباً");
          hist.push({role: "user", content: fullT});
          var rep = await askAI(hist, cType === "img" ? cData : null);
          hist.push({role: "assistant", content: rep});
          saveH(); wait.remove(); window.DH_UI.addMsg("AI", rep);
        }
      } catch(err){ wait.innerHTML = "⚠️ " + (err.message || err); }
    }
  };
})();
