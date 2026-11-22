(function(){
  var hist = [];
  try{ hist = JSON.parse(localStorage.getItem("dh_hist") || "[]"); }catch(e){ hist = []; }
  var sl = String.fromCharCode(47);
  var EDGE = "https:" + sl + sl + "hidden-bread-95eb.dz30007000.workers.dev";
  var q = document.getElementById("q");

  function saveH(){ try{ localStorage.setItem("dh_hist", JSON.stringify(hist.slice(-20))); }catch(e){} }

  function cleanSpeech(str){
    return String(str || "").replace(/[*#|_~`\[\](){}<>\/\\•\-:؛،."'!؟]/g, " ").replace(/\s+/g, " ").trim();
  }

  function getDims(){
    var el = document.getElementById("aspectSel");
    var v = el ? el.value : "1:1";
    if(v === "16:9") return {w: 960, h: 540};
    if(v === "9:16") return {w: 540, h: 960};
    return {w: 768, h: 768};
  }

  function playFoleySFX(actx, dest, type){
    try{
      var now = actx.currentTime;
      if(type === "sea"){
        var bSize = actx.sampleRate * 2, buf = actx.createBuffer(1, bSize, actx.sampleRate), data = buf.getChannelData(0);
        for(var i=0; i<bSize; i++) data[i] = (Math.random()*2 - 1) * Math.sin(Math.PI * i / bSize);
        var ns = actx.createBufferSource(), flt = actx.createBiquadFilter(), g = actx.createGain();
        ns.buffer = buf; flt.type = "lowpass"; flt.frequency.value = 380; g.gain.value = 0.14;
        ns.connect(flt); flt.connect(g); g.connect(dest); g.connect(actx.destination); ns.start(now);
      } else if(type === "roar"){
        var o = actx.createOscillator(), g = actx.createGain();
        o.type = "sawtooth"; o.frequency.setValueAtTime(140, now); o.frequency.exponentialRampToValueAtTime(52, now + 0.6);
        g.gain.setValueAtTime(0.22, now); g.gain.exponentialRampToValueAtTime(0.001, now + 0.65);
        o.connect(g); g.connect(dest); g.connect(actx.destination); o.start(now); o.stop(now + 0.65);
      } else {
        var o2 = actx.createOscillator(), g2 = actx.createGain();
        o2.type = "triangle"; o2.frequency.setValueAtTime(980, now); o2.frequency.exponentialRampToValueAtTime(120, now + 0.25);
        g2.gain.setValueAtTime(0.18, now); g2.gain.exponentialRampToValueAtTime(0.001, now + 0.28);
        o2.connect(g2); g2.connect(dest); g2.connect(actx.destination); o2.start(now); o2.stop(now + 0.28);
      }
    }catch(e){}
  }
  function loadThreeJS(){
    return new Promise(function(res){
      if(window.THREE) return res(window.THREE);
      var sc = document.createElement("script");
      sc.src = "https://cloudflare.com";
      sc.onload = function(){ res(window.THREE); };
      sc.onerror = function(){ res(null); };
      document.head.appendChild(sc);
    });
  }

  function create3DStage(THREE, w, h){
    var scene = new THREE.Scene();
    scene.background = new THREE.Color(0x070d19);
    scene.fog = new THREE.FogExp2(0x070d19, 0.045);
    var cam = new THREE.PerspectiveCamera(45, w / h, 0.1, 100);
    cam.position.set(0, 3.2, 8.5);
    var ren = new THREE.WebGLRenderer({antialias: true, preserveDrawingBuffer: true});
    ren.setSize(w, h);

    var amb = new THREE.AmbientLight(0xffffff, 0.65); scene.add(amb);
    var dirL = new THREE.DirectionalLight(0x93c5fd, 1.3); dirL.position.set(5, 10, 7); scene.add(dirL);
    var rimL = new THREE.PointLight(0xf43f5e, 1.5, 20); rimL.position.set(-4, 4, -3); scene.add(rimL);

    var ground = new THREE.Mesh(new THREE.PlaneGeometry(40, 40), new THREE.MeshStandardMaterial({color: 0x0f172a, roughness: 0.7}));
    ground.rotation.x = -Math.PI / 2; scene.add(ground);
    var grid = new THREE.GridHelper(40, 40, 0x38bdf8, 0x1e293b); scene.add(grid);

    function makeChar3D(bodyHex, swordHex, xPos, rotY){
      var root = new THREE.Group(); root.position.set(xPos, 0, 0); root.rotation.y = rotY;
      var matSkin = new THREE.MeshStandardMaterial({color: 0xffedd5});
      var matBody = new THREE.MeshStandardMaterial({color: bodyHex});
      var matDark = new THREE.MeshStandardMaterial({color: 0x1e293b});

      var torso = new THREE.Mesh(new THREE.BoxGeometry(0.9, 1.3, 0.5), matBody); torso.position.y = 1.65; root.add(torso);
      var head = new THREE.Mesh(new THREE.BoxGeometry(0.65, 0.65, 0.65), matSkin); head.position.y = 2.68; root.add(head);

      var legL = new THREE.Mesh(new THREE.BoxGeometry(0.32, 1.0, 0.35), matDark); legL.position.set(-0.24, 0.5, 0); root.add(legL);
      var legR = new THREE.Mesh(new THREE.BoxGeometry(0.32, 1.0, 0.35), matDark); legR.position.set(0.24, 0.5, 0); root.add(legR);

      var armL = new THREE.Mesh(new THREE.BoxGeometry(0.28, 1.0, 0.28), matBody); armL.position.set(-0.65, 1.75, 0); root.add(armL);
      var armR = new THREE.Group(); armR.position.set(0.65, 2.1, 0);
      var armMesh = new THREE.Mesh(new THREE.BoxGeometry(0.28, 0.95, 0.28), matBody); armMesh.position.y = -0.4; armR.add(armMesh);
      var sword = new THREE.Mesh(new THREE.BoxGeometry(0.1, 2.2, 0.22), new THREE.MeshStandardMaterial({color: swordHex, emissive: swordHex, emissiveIntensity: 0.7}));
      sword.position.set(0, -0.85, 0.95); sword.rotation.x = Math.PI / 2; armR.add(sword);
      root.add(armR); scene.add(root);
      return {root: root, head: head, legL: legL, legR: legR, armL: armL, armR: armR, baseX: xPos};
    }

    var hero = makeChar3D(0x0284c7, 0x38bdf8, -2.2, Math.PI / 2);
    var rival = makeChar3D(0xdc2626, 0xf43f5e, 2.2, -Math.PI / 2);
    return {scene: scene, cam: cam, ren: ren, hero: hero, rival: rival};
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
          var THREE = await loadThreeJS();
          var actx = new (window.AudioContext || window.webkitAudioContext)();
          if(actx.state === "suspended") await actx.resume();
          var dest = actx.createMediaStreamDestination();

          var matchSec = t.match(/(\d+)\s*(ثاني|ثوان|sec|s)/i);
          var targetSec = matchSec ? Math.max(parseInt(matchSec.shift(), 10), 8) : 14;
          var cleanV = t.replace(/صمم لي فيديو|صمم فيديو|اصنع فيديو|انشئ فيديو|اصنع حلقة|فيديو|مقطع|\d+\s*(ثاني|ثوان|sec|s)/gi, "").trim() || "مواجهة وجري وقتال بالسيوف بين سيف وكايتو";

          wait.innerHTML = "📝 <b>1/3:</b> تأليف الحوار وتوزيع النبرات الصوتية والحركة...";
          var sp = 'اكتب 4 سطور حوارية مشوقة بالعربية الفصحى بدون أي رموز عن: "' + cleanV + '". التزم حرفياً بهذا التنسيق:\nاسم_الشخصية | النبرة(soft أو rough أو deep) | الحركة(walk أو run أو fight) | الحوار_بالعربية(6 كلمات بدون رموز)';
          var rawScript = await askAI([{role: "user", content: sp}]);
          var scenes = rawScript.split("\n").map(function(line){
            var p = line.split("|").map(function(x){ return cleanSpeech(x); });
            if(p.length >= 4){
              var s0 = p.shift(), s1 = p.shift().toLowerCase(), s2 = p.shift().toLowerCase(), s3 = p.shift();
              if(s1 !== "soft" && s1 !== "rough" && s1 !== "deep") s1 = "rough";
              if(s2 !== "walk" && s2 !== "run" && s2 !== "fight") s2 = "fight";
              if(s0 && s3) return {speaker: s0, tone: s1, motion: s2, line: s3};
            }
            return null;
          }).filter(Boolean).slice(0, 4);

          if(!scenes.length){
            scenes = [
              {speaker: "سيف", tone: "rough", motion: "run", line: "لن أسمح لك بالهروب اليوم"},
              {speaker: "كايتو", tone: "deep", motion: "fight", line: "ستسقط أمام قوة نصلي المظلم"},
              {speaker: "لينا", tone: "soft", motion: "walk", line: "انتبه يا سيف إنه يهاجم بسرعة"},
              {speaker: "سيف", tone: "rough", motion: "fight", line: "هذه ضربة العدالة الحاسمة"}
            ];
          }

          wait.innerHTML = "🎙️ <b>2/3:</b> تسجيل أصوات الشخصيات بالنبرات البشرية النظيفة...";
          var audioClips = await Promise.all(scenes.map(function(sc){
            return fetch(EDGE + sl + "tts?t=" + encodeURIComponent(cleanSpeech(sc.line)) + "&v=" + sc.tone)
              .then(function(r){ return r.ok ? r.arrayBuffer() : null; })
              .then(function(buf){ return (buf && buf.byteLength > 200) ? actx.decodeAudioData(buf) : null; })
              .catch(function(){ return null; });
          }));
          wait.innerHTML = "🎬 <b>3/3:</b> إخراج المشهد ثلاثي الأبعاد (مشي + جري + قتال + مؤثرات)...";
          var dm = getDims();
          var stage = THREE ? create3DStage(THREE, dm.w, dm.h) : null;
          var hud = document.createElement("canvas"); hud.width = dm.w; hud.height = dm.h;
          var hctx = hud.getContext("2d");
          var vStream = hud.captureStream(30); dest.stream.getAudioTracks().forEach(function(tr){ vStream.addTrack(tr); });
          var mimeOut = MediaRecorder.isTypeSupported("video/mp4") ? "video/mp4" : "video/webm";
          var rec = new MediaRecorder(vStream, {mimeType: mimeOut}), chunks = [];
          rec.ondataavailable = function(e){ if(e.data.size > 0) chunks.push(e.data); };
          var doneRec = new Promise(function(res){ rec.onstop = function(){ try{actx.close();}catch(ex){} res(URL.createObjectURL(new Blob(chunks, {type: mimeOut}))); }; });
          rec.start();

          var totalFrames = Math.max(targetSec, scenes.length * 4) * 30, perScene = Math.floor(totalFrames / scenes.length), fc = 0, lastSpokenIdx = -1;
          var foleyType = (low.indexOf("بحر") !== -1 || low.indexOf("محيط") !== -1) ? "sea" : ((low.indexOf("حيوان") !== -1 || low.indexOf("وحش") !== -1) ? "roar" : "sword");

          await new Promise(function(res){
            var tm = setInterval(function(){
              var idx = Math.min(Math.floor(fc / perScene), scenes.length - 1), lp = (fc % perScene) / perScene;
              var curSc = scenes[idx], tSec = fc * 0.033;
              if(idx !== lastSpokenIdx){
                lastSpokenIdx = idx; window._isTalking = false;
                playFoleySFX(actx, dest, foleyType);
                if(audioClips[idx]){
                  try{
                    var src = actx.createBufferSource(); src.buffer = audioClips[idx];
                    src.playbackRate.value = curSc.tone === "soft" ? 1.14 : (curSc.tone === "deep" ? 0.84 : 0.96);
                    src.connect(dest); src.connect(actx.destination);
                    window._isTalking = true; src.onended = function(){ window._isTalking = false; };
                    src.start(0);
                  }catch(ex){}
                }
              }

              if(stage){
                var spd = curSc.motion === "run" ? 11.0 : (curSc.motion === "walk" ? 5.0 : 8.5);
                var amp = curSc.motion === "run" ? 0.75 : (curSc.motion === "walk" ? 0.35 : 0.5);
                [stage.hero, stage.rival].forEach(function(ch, ci){
                  var ph = tSec * spd + ci * 2.0;
                  ch.legL.rotation.x = Math.sin(ph) * amp;
                  ch.legR.rotation.x = -Math.sin(ph) * amp;
                  ch.armL.rotation.x = -Math.sin(ph) * amp * 0.8;
                  ch.armR.rotation.x = (curSc.motion === "fight") ? (Math.sin(tSec * 9.0 + ci) * 1.1 - 0.5) : (Math.sin(ph) * 0.4);
                  ch.root.position.y = Math.abs(Math.sin(ph)) * (curSc.motion === "run" ? 0.25 : 0.08);
                  if(curSc.motion === "run" || curSc.motion === "walk"){
                    ch.root.position.x = ch.baseX + Math.sin(tSec * 2.2) * (ci === 0 ? 0.8 : -0.8);
                  } else {
                    ch.root.position.x = (ci === 0 ? -1.1 : 1.1) + Math.sin(tSec * 6.0) * 0.25;
                  }
                  if((idx % 2 === ci) && window._isTalking) ch.head.rotation.x = Math.sin(tSec * 22.0) * 0.12;
                });
                stage.cam.position.x = Math.sin(tSec * 0.7) * 2.2;
                stage.cam.position.z = 7.2 - Math.sin(lp * Math.PI) * 1.4;
                stage.cam.lookAt(0, 1.6, 0);
                stage.ren.render(stage.scene, stage.cam);
                hctx.drawImage(stage.ren.domElement, 0, 0);
              }
              var grad = hctx.createLinearGradient(0, dm.h*0.72, 0, dm.h); grad.addColorStop(0, "rgba(0,0,0,0)"); grad.addColorStop(1, "rgba(0,0,0,0.94)");
              hctx.fillStyle = grad; hctx.fillRect(0, dm.h*0.72, dm.w, dm.h*0.28);
              hctx.fillStyle = curSc.tone === "soft" ? "#f472b6" : (curSc.tone === "deep" ? "#fbbf24" : "#38bdf8");
              hctx.fillRect(dm.w/2 - 110, dm.h*0.78, 220, 34); hctx.font = "bold 19px sans-serif"; hctx.textAlign = "center"; hctx.fillStyle = "#090a0f"; hctx.fillText(curSc.speaker, dm.w/2, dm.h*0.78 + 24);
              hctx.font = "bold 28px sans-serif"; hctx.fillStyle = "#ffffff"; hctx.fillText(curSc.line, dm.w/2, dm.h*0.91);

              if(++fc >= totalFrames){ clearInterval(tm); rec.stop(); res(); }
            }, 33);
          });

          var fbVid = await doneRec, castSummary = scenes.map(function(x){ return "• <b>" + x.speaker + ":</b> " + x.line; }).join("<br>");
          wait.remove(); window.DH_UI.addMsg("AI", "🎬 <b>تم الإنتاج ثلاثي الأبعاد (حركة مشي/جري/قتال + نبرات صوتية نظيفة):</b><br><br>" + castSummary, {vid: fbVid});
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
