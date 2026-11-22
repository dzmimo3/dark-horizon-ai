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
  function loadGameEngine(){
    return new Promise(function(res){
      if(window.THREE && window.THREE.GLTFLoader) return res(window.THREE);
      var s1 = document.createElement("script");
      s1.src = "https://jsdelivr.net";
      s1.onload = function(){
        var s2 = document.createElement("script");
        s2.src = "https://jsdelivr.net";
        s2.onload = function(){ res(window.THREE); };
        s2.onerror = function(){ res(null); };
        document.head.appendChild(s2);
      };
      s1.onerror = function(){ res(null); };
      document.head.appendChild(s1);
    });
  }

  function init3DGameWorld(THREE, w, h){
    return new Promise(function(resolve){
      var scene = new THREE.Scene();
      scene.background = new THREE.Color(0x0b132b);
      scene.fog = new THREE.FogExp2(0x0b132b, 0.032);
      var cam = new THREE.PerspectiveCamera(45, w / h, 0.1, 100);
      cam.position.set(0, 2.5, 7.5);
      var ren = new THREE.WebGLRenderer({antialias: true, preserveDrawingBuffer: true});
      ren.setSize(w, h);

      scene.add(new THREE.AmbientLight(0xffffff, 0.9));
      var sun = new THREE.DirectionalLight(0xfef08a, 1.4); sun.position.set(5, 10, 6); scene.add(sun);
      var rim = new THREE.PointLight(0x38bdf8, 1.8, 25); rim.position.set(-4, 4, 3); scene.add(rim);

      var ground = new THREE.Mesh(new THREE.PlaneGeometry(60, 60), new THREE.MeshStandardMaterial({color: 0x1c2541, roughness: 0.8}));
      ground.rotation.x = -Math.PI / 2; scene.add(ground);
      scene.add(new THREE.GridHelper(60, 40, 0x3a506b, 0x1c2541));

      var glb = "https://jsdelivr.net";
      var loader = new THREE.GLTFLoader();
      var chars = [null, null], loaded = 0;

      [0, 1].forEach(function(idx){
        loader.load(glb, function(gltf){
          var model = gltf.scene;
          model.scale.set(0.62, 0.62, 0.62);
          model.position.set(idx === 0 ? -1.8 : 1.8, 0, 0);
          model.rotation.y = idx === 0 ? Math.PI / 2 : -Math.PI / 2;
          model.traverse(function(n){
            if(n.isMesh && n.material){
              n.material = n.material.clone();
              if(n.material.color) n.material.color.offsetHSL(idx === 0 ? 0.55 : 0.0, 0.2, 0);
            }
          });
          scene.add(model);
          var mixer = new THREE.AnimationMixer(model);
          var clips = {};
          gltf.animations.forEach(function(c){ clips[c.name] = mixer.clipAction(c); });
          if(clips["Idle"]) clips["Idle"].play();
          chars[idx] = {model: model, mixer: mixer, clips: clips, cur: "Idle"};
          if(++loaded === 2) resolve({scene: scene, cam: cam, ren: ren, chars: chars});
        }, undefined, function(){
          if(++loaded === 2) resolve(null);
        });
      });
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

          wait.innerHTML = "🎮 <b>2/4:</b> تحميل مجسمات الشخصيات ثلاثية الأبعاد وهيكلها العظمي...";
          var dm = getDims();
          var THREE = await loadGameEngine();
          var world = THREE ? await init3DGameWorld(THREE, dm.w, dm.h) : null;
          if(!world) throw new Error("تعذر تحميل محرك 3D، تحقق من اتصال الإنترنت");

          wait.innerHTML = "🎙️ <b>3/4:</b> تسجيل أصوات الشخصيات بالنبرات البشرية النظيفة...";
          var audioClips = await Promise.all(scenes.map(function(sc){
            return fetch(EDGE + sl + "tts?t=" + encodeURIComponent(cleanSpeech(sc.line)) + "&v=" + sc.tone)
              .then(function(r){ return r.ok ? r.arrayBuffer() : null; })
              .then(function(buf){ return (buf && buf.byteLength > 200) ? actx.decodeAudioData(buf) : null; })
              .catch(function(){ return null; });
          }));

          wait.innerHTML = "🎬 <b>4/4:</b> تحريك الشخصيات ثلاثية الأبعاد وتسجيل المشهد...";
          var hud = document.createElement("canvas"); hud.width = dm.w; hud.height = dm.h;
          var hctx = hud.getContext("2d");
          var vStream = hud.captureStream(30); dest.stream.getAudioTracks().forEach(function(tr){ vStream.addTrack(tr); });
          var mimeOut = MediaRecorder.isTypeSupported("video/mp4") ? "video/mp4" : "video/webm";
          var rec = new MediaRecorder(vStream, {mimeType: mimeOut}), chunks = [];
          rec.ondataavailable = function(e){ if(e.data.size > 0) chunks.push(e.data); };
          var doneRec = new Promise(function(res){ rec.onstop = function(){ try{actx.close();}catch(ex){} res(URL.createObjectURL(new Blob(chunks, {type: mimeOut}))); }; });
          rec.start();

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

              var targetAnim = curSc.motion === "run" ? "Running" : (curSc.motion === "walk" ? "Walking" : "Punch");
              world.chars.forEach(function(ch, ci){
                if(!ch) return;
                ch.mixer.update(0.033);
                var animName = (idx % 2 === ci) ? targetAnim : (curSc.motion === "fight" ? "Punch" : "Walking");
                if(!ch.clips[animName]) animName = "Idle";
                if(ch.cur !== animName && ch.clips[animName]){
                  if(ch.clips[ch.cur]) ch.clips[ch.cur].fadeOut(0.2);
                  ch.clips[animName].reset().fadeIn(0.2).play();
                  ch.cur = animName;
                }
                if(curSc.motion === "run" || curSc.motion === "walk"){
                  ch.model.position.x = (ci === 0 ? -1.8 : 1.8) + Math.sin(tSec * 2.2) * (ci === 0 ? 1.0 : -1.0);
                } else {
                  ch.model.position.x = (ci === 0 ? -0.95 : 0.95);
                }
              });

              world.cam.position.x = Math.sin(tSec * 0.65) * 2.2;
              world.cam.position.z = 6.8 - Math.sin(lp * Math.PI) * 1.3;
              world.cam.lookAt(0, 1.5, 0);
              world.ren.render(world.scene, world.cam);
              hctx.drawImage(world.ren.domElement, 0, 0);

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
        } else if((low.indexOf("صورة") !== -1 || low.indexOf("صور") !== -1 || low.indexOf("شخصية") !== -1 || low.indexOf("ارسم") !== -1 || low.indexOf("صمم") !== -1 || low.indexOf("image") !== -1) && cType !== "img"){
          var cleanT = t.replace(/صمم لي صور|صمم لي صورة|صمم شخصية|صمم صورة|ارسم لي|ارسم|صور|صورة/gi, "").trim() || "محارب أنمي واقعي بدرع فضي";
          wait.innerHTML = "🧬 <b>المرحلة 1/4 (النحت والهيكل):</b> بناء التناسق التشريحي وملامح الشخصية...<br>🎨 <b>المرحلة 2/4 (الخامات):</b> ضبط الجلد والمعادن والإضاءة السينمائية...";
          var pipePrompt = 'أنت مدير فني في استوديو ألعاب عالمي. صمم الشخصية التالية عبر 4 مراحل قصيرة بالعربية ثم اكتب في السطر الأخير وصفاً إنجليزياً دقيقاً للتصيير (25 كلمة):
' +
            '1- النحت والتشريح: (وصف الوجه والجسد والملابس)
' +
            '2- الخامات والإضاءة: (نوع الجلد والقماش والإضاءة)
' +
            '3- وضعية الهيكل العظمي: (الوقفة وحركة المفاصل)
' +
            '4- RENDER_PROMPT: (وصف إنجليزي احترافي يجمع المراحل الثلاث بدقة 8K)
' +
            'الطلب: ' + cleanT;
          var pipeRes = await askAI([{role: "user", content: pipePrompt}]);
          var lines = pipeRes.split("
"), renderEn = "";
          lines.forEach(function(l){ if(l.indexOf("RENDER_PROMPT") !== -1) renderEn = l.split(":").slice(1).join(":").trim(); });
          renderEn = renderEn.replace(/[^a-zA-Z0-9 ,.-]/g, "").trim().slice(0, 180) || "photorealistic 3D game character portrait, Unreal Engine 5 Metahuman quality, intricate armor, subsurface scattering skin, studio rim lighting, 8k";
          if(isAnime) renderEn += ", high budget 3D anime character render, Ufotable and Final Fantasy VII Remake style, sharp eyes, cel-shaded realism, 8k";
          else renderEn += ", Unreal Engine 5 Metahuman photorealistic render, cinematic depth of field, 8k";

          wait.innerHTML = "🦴 <b>المرحلة 3/4 (ضبط المفاصل):</b> تثبيت الوضعية الحركية...<br>🎬 <b>المرحلة 4/4 (التصيير النهائي 8K):</b> إخراج الشخصية الواقعية...";
          var ir = await fetch(EDGE + sl + "image", {method: "POST", headers: {"Content-Type": "application/json"}, body: JSON.stringify({prompt: renderEn, width: getDims().w, height: getDims().h})});
          var iData = await ir.json().catch(function(){ return {}; });
          if(!ir.ok || !iData.image_url) throw new Error("فشل التصيير النهائي للشخصية");
          var reportHtml = pipeRes.replace(/4-\s*RENDER_PROMPT:.*/i, "").trim();
          wait.remove();
          window.DH_UI.addMsg("AI", "🧬 <b>تم تصميم الشخصية وفق المراحل الاستوديو الأربع:</b><br><br>" + reportHtml, {img: iData.image_url});
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
