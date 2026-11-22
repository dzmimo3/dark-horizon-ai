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
      if(window.THREE && window.THREE.GLTFLoader) return res(window.THREE);
      var sc = document.createElement("script");
      sc.src = "https://cloudflare.com";
      sc.onload = function(){
        var ld = document.createElement("script");
        ld.src = "https://jsdelivr.net";
        ld.onload = function(){ res(window.THREE); };
        ld.onerror = function(){ res(window.THREE); };
        document.head.appendChild(ld);
      };
      sc.onerror = function(){ res(null); };
      document.head.appendChild(sc);
    });
  }

  function create3DStage(THREE, w, h){
    var scene = new THREE.Scene();
    scene.background = new THREE.Color(0x060b16);
    scene.fog = new THREE.FogExp2(0x060b16, 0.038);
    var cam = new THREE.PerspectiveCamera(45, w / h, 0.1, 100);
    cam.position.set(0, 2.8, 8.2);
    var ren = new THREE.WebGLRenderer({antialias: true, preserveDrawingBuffer: true});
    ren.setSize(w, h);

    scene.add(new THREE.AmbientLight(0xffffff, 0.75));
    var dirL = new THREE.DirectionalLight(0x93c5fd, 1.5); dirL.position.set(5, 10, 7); scene.add(dirL);
    var rimL = new THREE.PointLight(0xf43f5e, 1.8, 25); rimL.position.set(-4, 5, -3); scene.add(rimL);

    var ground = new THREE.Mesh(new THREE.PlaneGeometry(50, 50), new THREE.MeshStandardMaterial({color: 0x0b1220, roughness: 0.6}));
    ground.rotation.x = -Math.PI / 2; scene.add(ground);
    scene.add(new THREE.GridHelper(50, 50, 0x38bdf8, 0x1e293b));

    // جزيئات طاقة ثلاثية الأبعاد (3D Game Particle System)
    var pGeo = new THREE.BufferGeometry(), pArr = new Float32Array(300 * 3);
    for(var i = 0; i < 900; i++) pArr[i] = (Math.random() - 0.5) * 18;
    pGeo.setAttribute("position", new THREE.BufferAttribute(pArr, 3));
    var pSys = new THREE.Points(pGeo, new THREE.PointsMaterial({color: 0x38bdf8, size: 0.12}));
    scene.add(pSys);

    // تحميل مجسمات الألعاب ثلاثية الأبعاد بهيكل عظمي وحركات حقيقية (GLB Skeletal Rig)
    var glbUrl = "https://threejs.org";
    var mixers = [], models = [null, null], actionsList = [{}, {}];

    if(THREE.GLTFLoader){
      var loader = new THREE.GLTFLoader();
      [0, 1].forEach(function(idx){
        loader.load(glbUrl, function(gltf){
          var m = gltf.scene;
          m.scale.set(0.65, 0.65, 0.65);
          m.position.set(idx === 0 ? -1.8 : 1.8, 0, 0);
          m.rotation.y = idx === 0 ? Math.PI / 2 : -Math.PI / 2;
          m.traverse(function(c){
            if(c.isMesh && c.material){
              c.material = new THREE.MeshToonMaterial({color: idx === 0 ? 0x38bdf8 : 0xf43f5e});
            }
          });
          scene.add(m);
          models[idx] = m;
          var mx = new THREE.AnimationMixer(m);
          mixers.push(mx);
          gltf.animations.forEach(function(clip){ actionsList[idx][clip.name] = mx.clipAction(clip); });
          if(actionsList[idx]["Running"]) actionsList[idx]["Running"].play();
        });
      });
    }
    return {scene: scene, cam: cam, ren: ren, mixers: mixers, models: models, actionsList: actionsList, pSys: pSys};
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
                stage.mixers.forEach(function(mx){ mx.update(0.033); });
                stage.pSys.rotation.y += 0.008;
                [0, 1].forEach(function(ci){
                  var m = stage.models[ci], acts = stage.actionsList[ci];
                  if(m && acts){
                    var targetAnim = curSc.motion === "run" ? "Running" : (curSc.motion === "walk" ? "Walking" : "Punch");
                    if(!acts[targetAnim]) targetAnim = "Idle";
                    if(m._curAnim !== targetAnim && acts[targetAnim]){
                      if(m._curAnim && acts[m._curAnim]) acts[m._curAnim].fadeOut(0.2);
                      acts[targetAnim].reset().fadeIn(0.2).play();
                      m._curAnim = targetAnim;
                    }
                    if(curSc.motion === "run" || curSc.motion === "walk"){
                      m.position.x = (ci === 0 ? -1.8 : 1.8) + Math.sin(tSec * 2.0) * (ci === 0 ? 1.1 : -1.1);
                    } else {
                      m.position.x = (ci === 0 ? -1.1 : 1.1);
                    }
                  }
                });
                stage.cam.position.x = Math.sin(tSec * 0.65) * 2.4;
                stage.cam.position.z = 7.4 - Math.sin(lp * Math.PI) * 1.5;
                stage.cam.lookAt(0, 1.5, 0);
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
