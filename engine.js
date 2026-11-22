(function(){
  var hist = [];
  try{ hist = JSON.parse(localStorage.getItem("dh_hist") || "[]"); }catch(e){ hist = []; }
  var sl = String.fromCharCode(47);
  var EDGE = "https:" + sl + sl + "hidden-bread-95eb.dz30007000.workers.dev";
  var q = document.getElementById("q");

  function saveH(){ try{ localStorage.setItem("dh_hist", JSON.stringify(hist.slice(-20))); }catch(e){} }
  function cleanSpeech(s){ return String(s || "").replace(/[*#|_~`\[\](){}<>\/\\•\-:؛،."'!؟]/g, " ").replace(/\s+/g, " ").trim(); }
  function getDims(){
    var el = document.getElementById("aspectSel"), v = el ? el.value : "1:1";
    if(v === "16:9") return {w: 960, h: 540};
    if(v === "9:16") return {w: 540, h: 960};
    return {w: 768, h: 768};
  }

  // مكتبة المؤثرات الصوتية الشاملة (بحر، رعد، رياح، سيوف، وحوش، خطوات)
  function playStudioSFX(actx, dest, kind){
    try{
      var now = actx.currentTime;
      if(kind === "sea" || kind === "wind"){
        var len = actx.sampleRate * 2.2, buf = actx.createBuffer(1, len, actx.sampleRate), d = buf.getChannelData(0);
        for(var i = 0; i < len; i++) d[i] = (Math.random() * 2 - 1) * Math.sin(Math.PI * i / len);
        var src = actx.createBufferSource(), flt = actx.createBiquadFilter(), g = actx.createGain();
        src.buffer = buf; flt.type = "lowpass"; flt.frequency.value = kind === "sea" ? 360 : 650; g.gain.value = 0.15;
        src.connect(flt); flt.connect(g); g.connect(dest); g.connect(actx.destination); src.start(now);
      } else if(kind === "roar" || kind === "thunder"){
        var o = actx.createOscillator(), g = actx.createGain();
        o.type = "sawtooth"; o.frequency.setValueAtTime(135, now); o.frequency.exponentialRampToValueAtTime(42, now + 0.7);
        g.gain.setValueAtTime(0.24, now); g.gain.exponentialRampToValueAtTime(0.001, now + 0.75);
        o.connect(g); g.connect(dest); g.connect(actx.destination); o.start(now); o.stop(now + 0.75);
      } else {
        var o2 = actx.createOscillator(), g2 = actx.createGain();
        o2.type = "triangle"; o2.frequency.setValueAtTime(1050, now); o2.frequency.exponentialRampToValueAtTime(130, now + 0.25);
        g2.gain.setValueAtTime(0.18, now); g2.gain.exponentialRampToValueAtTime(0.001, now + 0.28);
        o2.connect(g2); g2.connect(dest); g2.connect(actx.destination); o2.start(now); o2.stop(now + 0.28);
      }
    }catch(e){}
  }
  function drawDynamicFrame(ctx, w, h, t, lp, idx, sc, talking, bgImg, pts){
    ctx.save();
    // كاميرا سينمائية: تقريب، اهتزاز قتالي، وميلان ديناميكي
    var zoom = 1.05 + Math.sin(lp * Math.PI) * 0.14;
    var shakeX = (lp < 0.14) ? Math.sin(t * 55) * 6 : 0;
    var shakeY = (lp < 0.14) ? Math.cos(t * 48) * 5 : 0;
    ctx.translate(w * 0.5 + shakeX, h * 0.5 + shakeY);
    ctx.scale(zoom, zoom);
    ctx.translate(-w * 0.5, -h * 0.5);

    // 1. رسم خلفية المشهد المولدة بالذكاء الاصطناعي أو الخلفية السينمائية الفورية (لا شاشة سوداء أبداً)
    if(bgImg){
      ctx.drawImage(bgImg, 0, 0, w, h);
      ctx.fillStyle = "rgba(6, 10, 20, 0.25)";
      ctx.fillRect(0, 0, w, h);
    } else {
      var sky = ctx.createLinearGradient(0, 0, 0, h);
      if(idx % 2 === 0){ sky.addColorStop(0, "#071124"); sky.addColorStop(1, "#1e3a5f"); }
      else { sky.addColorStop(0, "#1c0a24"); sky.addColorStop(1, "#4c1d3d"); }
      ctx.fillStyle = sky; ctx.fillRect(0, 0, w, h);
      ctx.fillStyle = "rgba(254, 240, 138, 0.9)";
      ctx.beginPath(); ctx.arc(w * 0.5, h * 0.25, w * 0.09, 0, Math.PI * 2); ctx.fill();
      ctx.fillStyle = "#090f1d";
      ctx.beginPath(); ctx.moveTo(0, h);
      for(var x = 0; x <= w; x += 30) ctx.lineTo(x, h * 0.65 - Math.sin(x * 0.015 + t) * 35);
      ctx.lineTo(w, h); ctx.fill();
    }

    // 2. رسم وتحريك الشخصيات المتفاعلة (مشي / جري / قتال) فوق المشهد
    function renderActor(cx, cy, dir, colMain, colHair, isSpeaker){
      ctx.save();
      var spd = sc.motion === "run" ? 11.0 : (sc.motion === "walk" ? 5.5 : 8.5);
      var moveX = (sc.motion === "run" || sc.motion === "walk") ? Math.sin(t * 2.2) * 45 * dir : Math.sin(t * 6.0) * 18 * dir;
      var bounce = Math.abs(Math.sin(t * spd)) * (sc.motion === "run" ? 16 : 6);
      ctx.translate(cx + moveX, cy - bounce);
      ctx.scale(dir, 1);

      if(isSpeaker){
        var aura = ctx.createRadialGradient(0, -45, 5, 0, -45, 95);
        aura.addColorStop(0, colMain + "66"); aura.addColorStop(1, "rgba(0,0,0,0)");
        ctx.fillStyle = aura; ctx.beginPath(); ctx.arc(0, -45, 95, 0, Math.PI * 2); ctx.fill();
      }

      // عباءة متطايرة + أرجل متحركة + جذع + رأس + سيف متوهج
      ctx.fillStyle = colMain;
      ctx.beginPath(); ctx.moveTo(-12, -72); ctx.quadraticCurveTo(-68, -45 + Math.sin(t * 9) * 16, -88, 16); ctx.lineTo(-14, -8); ctx.fill();

      var legA = Math.sin(t * spd) * 24;
      ctx.strokeStyle = "#0f172a"; ctx.lineWidth = 13; ctx.lineCap = "round";
      ctx.beginPath(); ctx.moveTo(-8, -14); ctx.lineTo(-18 - legA, 42); ctx.stroke();
      ctx.beginPath(); ctx.moveTo(10, -14); ctx.lineTo(22 + legA, 42); ctx.stroke();

      ctx.fillStyle = "#f8fafc"; ctx.beginPath(); ctx.roundRect(-19, -78, 38, 66, 11); ctx.fill();
      ctx.fillStyle = colMain; ctx.fillRect(-19, -48, 38, 12);

      ctx.save();
      ctx.translate(0, -102 + (isSpeaker && talking ? Math.sin(t * 24) * 2.5 : 0));
      ctx.fillStyle = "#ffedd5"; ctx.beginPath(); ctx.arc(0, 0, 22, 0, Math.PI * 2); ctx.fill();
      ctx.fillStyle = colHair; ctx.beginPath(); ctx.moveTo(-24, -4); ctx.lineTo(-16, -34); ctx.lineTo(0, -22); ctx.lineTo(14, -36); ctx.lineTo(25, -4); ctx.fill();
      ctx.fillStyle = colMain; ctx.fillRect(6, -4, 8, (Math.sin(t * 2.3) > 0.96) ? 1.5 : 6);
      ctx.fillStyle = "#be123c"; ctx.fillRect(7, 9, 8, (isSpeaker && talking) ? (3 + Math.abs(Math.sin(t * 28)) * 6) : 2);
      ctx.restore();

      ctx.save();
      ctx.translate(12, -64);
      ctx.rotate(sc.motion === "fight" ? (Math.sin(t * 8.0) * 1.1 - 0.35) : (Math.sin(t * spd) * 0.4));
      ctx.strokeStyle = "#ffedd5"; ctx.lineWidth = 10; ctx.beginPath(); ctx.moveTo(0, 0); ctx.lineTo(36, 0); ctx.stroke();
      ctx.strokeStyle = colMain; ctx.lineWidth = 5; ctx.shadowColor = colMain; ctx.shadowBlur = 14;
      ctx.beginPath(); ctx.moveTo(36, 0); ctx.lineTo(130, -12); ctx.stroke();
      ctx.restore();
      ctx.restore();
    }

    renderActor(w * 0.28, h * 0.66, 1, "#38bdf8", "#0f172a", idx % 2 === 0);
    renderActor(w * 0.72, h * 0.66, -1, "#f43f5e", "#f8fafc", idx % 2 === 1);
    ctx.restore();

    // 3. جزيئات الطاقة وخطوط السرعة
    pts.forEach(function(pt){
      pt.x += pt.vx; pt.y += pt.vy;
      if(pt.y < 0) pt.y = h; if(pt.x < 0) pt.x = w; if(pt.x > w) pt.x = 0;
      ctx.fillStyle = "rgba(253, 224, 71, " + pt.a + ")";
      ctx.beginPath(); ctx.arc(pt.x, pt.y, pt.r, 0, Math.PI * 2); ctx.fill();
    });
  }
  function renderSmartReply(text){
    var d = window.DH_UI.addMsg("AI", text);
    var codeMatch = text.match(/```(?:html|xml)?\s*([\s\(\S\)]*?)```/i);
    if(codeMatch && codeMatch){
      var ac = d.querySelector(".actions") || document.createElement("div");
      ac.className = "actions";
      var runBtn = document.createElement("button");
      runBtn.type = "button"; runBtn.className = "act"; runBtn.textContent = "▶️ تشغيل البرنامج مباشرة";
      runBtn.onclick = function(){
        var blob = new Blob([codeMatch], {type: "text/html;charset=utf-8"});
        window.open(URL.createObjectURL(blob), "_blank");
      };
      ac.appendChild(runBtn);
      if(!d.contains(ac)) d.appendChild(ac);
    }
  }
  hist.forEach(function(m){ if(m.role === "user") window.DH_UI.addMsg("USER", m.content); else renderSmartReply(m.content); });

  async function askAI(msgs, imgData){
    var lastQ = msgs.length ? msgs[msgs.length - 1].content : "";
    var webCtx = "";
    if(lastQ.length > 4 && (lastQ.indexOf("اخبار") !== -1 || lastQ.indexOf("أخبار") !== -1 || lastQ.indexOf("بحث") !== -1 || lastQ.indexOf("ما هو") !== -1 || lastQ.indexOf("من هو") !== -1)){
      try{
        var sr = await fetch(EDGE + sl + "search?q=" + encodeURIComponent(lastQ));
        if(sr.ok){ var sd = await sr.json(); if(sd && sd.results) webCtx = "\n[معلومات حية من الإنترنت]:\n" + sd.results; }
      }catch(e){}
    }
    var sendMsgs = msgs.slice(-8);
    if(webCtx && sendMsgs.length) sendMsgs[sendMsgs.length - 1] = {role: "user", content: lastQ + webCtx};
    var r = await fetch(EDGE + sl + "chat", {
      method: "POST", headers: {"Content-Type": "application/json"},
      body: JSON.stringify({messages: sendMsgs, image: imgData || null})
    });
    if(r.ok){ var d = await r.json(); if(d && d.reply) return d.reply; }
    throw new Error("الخادم مشغول، أعد المحاولة");
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
        if(low.indexOf("فيديو") !== -1 || low.indexOf("مقطع") !== -1 || low.indexOf("تحريك") !== -1 || low.indexOf("انمي") !== -1 || low.indexOf("أنمي") !== -1 || low.indexOf("حلقة") !== -1 || low.indexOf("فيلم") !== -1 || low.indexOf("video") !== -1){
          var actx = new (window.AudioContext || window.webkitAudioContext)();
          if(actx.state === "suspended") await actx.resume();
          var dest = actx.createMediaStreamDestination();

          var matchSec = t.match(/(\d+)\s*(ثاني|ثوان|sec|s)/i);
          var targetSec = matchSec ? Math.max(parseInt(matchSec.shift(), 10), 8) : 14;
          var cleanV = t.replace(/صمم لي فيديو|صمم فيديو|اصنع فيديو|انشئ فيديو|اصنع حلقة|فيديو|مقطع|\d+\s*(ثاني|ثوان|sec|s)/gi, "").trim() || "مواجهة وجري وقتال بالسيوف بين سيف وكايتو";

          wait.innerHTML = "📝 <b>1/4:</b> تأليف السيناريو وتوزيع النبرات الصوتية والحركة...";
          var sp = 'اكتب 4 سطور حوارية مشوقة بالعربية الفصحى بدون أي رموز عن: "' + cleanV + '". التزم حرفياً بهذا التنسيق:\nاسم_الشخصية | النبرة(soft أو rough أو deep) | الحركة(walk أو run أو fight) | الحوار_بالعربية(6 كلمات بدون رموز) | وصف_الخلفية_بالإنجليزية(8 كلمات)';
          var rawScript = await askAI([{role: "user", content: sp}]);
          var scenes = rawScript.split("\n").map(function(line){
            var p = line.split("|").map(function(x){ return cleanSpeech(x); });
            if(p.length >= 5){
              var s0 = p.shift(), s1 = p.shift().toLowerCase(), s2 = p.shift().toLowerCase(), s3 = p.shift(), s4 = p.shift();
              if(s1 !== "soft" && s1 !== "rough" && s1 !== "deep") s1 = "rough";
              if(s2 !== "walk" && s2 !== "run" && s2 !== "fight") s2 = "fight";
              if(s0 && s3) return {speaker: s0, tone: s1, motion: s2, line: s3, bgPrompt: s4 || "epic anime battlefield sunset"};
            }
            return null;
          }).filter(Boolean).slice(0, 4);
          if(!scenes.length){
            scenes = [
              {speaker: "سيف", tone: "rough", motion: "run", line: "لن أسمح لك بالهروب اليوم", bgPrompt: "Japanese anime city rooftop night moonlight"},
              {speaker: "كايتو", tone: "deep", motion: "fight", line: "ستسقط أمام قوة نصلي المظلم", bgPrompt: "dark anime temple ruins glowing energy"},
              {speaker: "لينا", tone: "soft", motion: "walk", line: "انتبه يا سيف إنه يهاجم بسرعة", bgPrompt: "anime forest cliff dramatic clouds sunset"},
              {speaker: "سيف", tone: "rough", motion: "fight", line: "هذه ضربة العدالة الحاسمة", bgPrompt: "epic anime energy explosion sky background"}
            ];
          }

          wait.innerHTML = "🎨 <b>2/4:</b> توليد خلفيات الاستوديو وتسجيل أصوات الشخصيات...";
          var dm = getDims();
          var bgImgs = await Promise.all(scenes.map(function(sc){
            if(cType === "img") return new Promise(function(r){ var im = new Image(); im.onload = function(){ r(im); }; im.onerror = function(){ r(null); }; im.src = cData; });
            return fetch(EDGE + sl + "image", {
              method: "POST", headers: {"Content-Type": "application/json"},
              body: JSON.stringify({prompt: sc.bgPrompt + ", anime scenery background, no text, 8k", width: dm.w, height: dm.h})
            }).then(function(r){ return r.ok ? r.json() : null; }).then(function(d){
              if(!d || !d.image_url) return null;
              return new Promise(function(res){ var im = new Image(); im.onload = function(){ res(im); }; im.onerror = function(){ res(null); }; im.src = d.image_url; });
            }).catch(function(){ return null; });
          }));

          var audioClips = await Promise.all(scenes.map(function(sc){
            return fetch(EDGE + sl + "tts?t=" + encodeURIComponent(cleanSpeech(sc.line)) + "&v=" + sc.tone)
              .then(function(r){ return r.ok ? r.arrayBuffer() : null; })
              .then(function(buf){ return (buf && buf.byteLength > 200) ? actx.decodeAudioData(buf) : null; })
              .catch(function(){ return null; });
          }));
          wait.innerHTML = "🎬 <b>3/4:</b> إخراج المشهد وتحريك الشخصيات ودمج الأصوات...";
          var hud = document.createElement("canvas"); hud.width = dm.w; hud.height = dm.h;
          var hctx = hud.getContext("2d");
          var vStream = hud.captureStream(30); dest.stream.getAudioTracks().forEach(function(tr){ vStream.addTrack(tr); });
          var mimeOut = MediaRecorder.isTypeSupported("video/mp4") ? "video/mp4" : "video/webm";
          var rec = new MediaRecorder(vStream, {mimeType: mimeOut}), chunks = [];
          rec.ondataavailable = function(e){ if(e.data.size > 0) chunks.push(e.data); };
          var doneRec = new Promise(function(res){ rec.onstop = function(){ try{actx.close();}catch(ex){} res(URL.createObjectURL(new Blob(chunks, {type: mimeOut}))); }; });
          rec.start();

          var pts = Array.from({length: 45}, function(){ return {x: Math.random()*dm.w, y: Math.random()*dm.h, r: 1.5+Math.random()*2.5, vx: (Math.random()-0.5)*1.5, vy: -0.8-Math.random()*1.5, a: 0.45+Math.random()*0.5}; });
          var totalFrames = Math.max(targetSec, scenes.length * 4) * 30, perScene = Math.floor(totalFrames / scenes.length), fc = 0, lastSpokenIdx = -1;
          var sfxKind = (low.indexOf("بحر") !== -1) ? "sea" : ((low.indexOf("رعد") !== -1 || low.indexOf("وحش") !== -1) ? "roar" : "sword");

          await new Promise(function(res){
            var tm = setInterval(function(){
              var idx = Math.min(Math.floor(fc / perScene), scenes.length - 1), lp = (fc % perScene) / perScene;
              var curSc = scenes[idx], tSec = fc * 0.033;
              if(idx !== lastSpokenIdx){
                lastSpokenIdx = idx; window._isTalking = false;
                playStudioSFX(actx, dest, sfxKind);
                if(audioClips[idx]){
                  try{
                    var src = actx.createBufferSource(); src.buffer = audioClips[idx];
                    src.playbackRate.value = curSc.tone === "soft" ? 1.15 : (curSc.tone === "deep" ? 0.84 : 0.96);
                    src.connect(dest); src.connect(actx.destination);
                    window._isTalking = true; src.onended = function(){ window._isTalking = false; };
                    src.start(0);
                  }catch(ex){}
                }
              }
              drawDynamicFrame(hctx, dm.w, dm.h, tSec, lp, idx, curSc, window._isTalking, bgImgs[idx], pts);
              var grad = hctx.createLinearGradient(0, dm.h*0.72, 0, dm.h); grad.addColorStop(0, "rgba(0,0,0,0)"); grad.addColorStop(1, "rgba(0,0,0,0.94)");
              hctx.fillStyle = grad; hctx.fillRect(0, dm.h*0.72, dm.w, dm.h*0.28);
              hctx.fillStyle = curSc.tone === "soft" ? "#f472b6" : (curSc.tone === "deep" ? "#fbbf24" : "#38bdf8");
              hctx.fillRect(dm.w/2 - 110, dm.h*0.78, 220, 34); hctx.font = "bold 19px sans-serif"; hctx.textAlign = "center"; hctx.fillStyle = "#090a0f"; hctx.fillText(curSc.speaker, dm.w/2, dm.h*0.78 + 24);
              hctx.font = "bold 28px sans-serif"; hctx.fillStyle = "#ffffff"; hctx.fillText(curSc.line, dm.w/2, dm.h*0.91);
              if(++fc >= totalFrames){ clearInterval(tm); rec.stop(); res(); }
            }, 33);
          });

          var fbVid = await doneRec, castSummary = scenes.map(function(x){ return "• <b>" + x.speaker + ":</b> " + x.line; }).join("<br>");
          wait.remove(); window.DH_UI.addMsg("AI", "🎬 <b>تم الإخراج الشامل (خلفيات AI + شخصيات متحركة + أصوات متعددة):</b><br><br>" + castSummary, {vid: fbVid});
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
          saveH(); wait.remove(); renderSmartReply(rep);
        }
      } catch(err){ wait.innerHTML = "⚠️ " + (err.message || err); }
    }
  };
})();
