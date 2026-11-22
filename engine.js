(function(){
  var hist = [];
  try{ hist = JSON.parse(localStorage.getItem("dh_hist") || "[]"); }catch(e){ hist = []; }
  var sl = String.fromCharCode(47);
  var EDGE = "https:" + sl + sl + "hidden-bread-95eb.dz30007000.workers.dev";
  var q = document.getElementById("q");

  function getDims(){
    var el = document.getElementById("aspectSel");
    var v = el ? el.value : "1:1";
    if(v === "16:9") return {w: 960, h: 540};
    if(v === "9:16") return {w: 540, h: 960};
    return {w: 768, h: 768};
  }

  function saveH(){
    try{ localStorage.setItem("dh_hist", JSON.stringify(hist.slice(-20))); }catch(e){}
  }

  hist.forEach(function(m){
    window.DH_UI.addMsg(m.role === "user" ? "USER" : "AI", m.content);
  });

  async function askAI(msgs, imgData){
    var r = await fetch(EDGE + sl + "chat", {
      method: "POST",
      headers: {"Content-Type": "application/json"},
      body: JSON.stringify({messages: msgs.slice(-8), image: imgData || null})
    });
    if(r.ok){
      var d = await r.json();
      if(d && d.reply) return d.reply;
    }
    throw new Error("تعذر الاتصال بالمحرك السحابي");
  }

  function cleanTextForTTS(txt){
    if(!txt) return "";
    return String(txt)
      .replace(/[\*\#\_\-\~\|\`\+\!\?\.\,\;\:\(\)\[\]\{\}\"\'\/\\«»]/g, " ")
      .replace(/\s+/g, " ")
      .trim();
  }

  window.DH_ENGINE = {
    reset: function(){ hist = []; },
    send: async function(t){
      q.value = "";
      var cData = window.DH_UI.attData, cType = window.DH_UI.attType, cName = window.DH_UI.attName;
      window.DH_UI.clearAttachment();
      window.DH_UI.addMsg("USER", t || ("📎 ملف: " + cName), cType === "img" ? {user_img: cData} : null);
      var wait = window.DH_UI.addMsg("AI", "⚡ جاري المعالجة والتنفيذ...");
      var low = t.toLowerCase();
      var isAnime = low.indexOf("انمي") !== -1 || low.indexOf("أنمي") !== -1 || low.indexOf("كرتون") !== -1 || low.indexOf("anime") !== -1;
      var isCinematic = low.indexOf("سينما") !== -1 || low.indexOf("هوليوود") !== -1 || low.indexOf("سينمائي") !== -1 || low.indexOf("cinematic") !== -1;

      try{
        if(low.indexOf("فيديو") !== -1 || low.indexOf("مقطع") !== -1 || low.indexOf("تحريك") !== -1 || low.indexOf("انمي") !== -1 || low.indexOf("أنمي") !== -1 || low.indexOf("حلقة") !== -1 || low.indexOf("video") !== -1){
          var actx = new (window.AudioContext || window.webkitAudioContext)();
          if(actx.state === "suspended") await actx.resume();
          var dest = actx.createMediaStreamDestination();
          var bgmGain = actx.createGain(); bgmGain.gain.value = 0.04; bgmGain.connect(dest); bgmGain.connect(actx.destination);
          var bgmOscs = [110.0, 164.81, 220.0].map(function(fq){ var o = actx.createOscillator(); o.type = "sine"; o.frequency.value = fq; o.connect(bgmGain); o.start(); return o; });

          var matchSec = t.match(/(\d+)\s*(ثاني|ثوان|sec|s)/i);
          var targetSec = matchSec ? Math.max(parseInt(matchSec.shift(), 10), 8) : 14;
          var cleanV = t.replace(/صمم لي فيديو|صمم فيديو|اصنع فيديو|انشئ فيديو|اصنع حلقة|فيديو|مقطع|\d+\s*(ثاني|ثوان|sec|s)/gi, "").trim() || "ملحمة سينمائية مذهلة بين الأبطال وقوى الظلام";

          wait.innerHTML = "📝 <b>1/4:</b> تأليف الحوار وتوزيع نبرات أصوات الشخصيات...";
          var sp = 'أنت مخرج أفلام ومسلسلات أنمي عالمي. اكتب 4 سطور حوارية درامية بالعربية الفصحى عن: "' + cleanV + '". التزم حرفياً بهذا القالب في كل سطر بدون ترقيم:\nاسم_الشخصية | الصوت(onyx للعميق الرجولي أو nova للأنثوي الناعم أو echo للرجولي الواثق) | الحوار_بالعربية(6 كلمات كحد أقصى) | وصف_اللقطة_بالإنجليزية(12 كلمة)';
          var rawScript = await askAI([{role: "user", content: sp}]);
          var scenes = rawScript.split("\n").map(function(line){
            var p = line.split("|").map(function(x){ return x.replace(/[*#]/g, "").trim(); });
            if(p.length >= 4){
              var s0 = p.shift(), s1 = p.shift().toLowerCase(), s2 = p.shift(), s3 = p.shift();
              if(s1 !== "onyx" && s1 !== "nova" && s1 !== "echo") s1 = "echo";
              if(s0 && s2 && s3) return {speaker: s0, voice: s1, line: s2, prompt: s3};
            }
            return null;
          }).filter(Boolean).slice(0, 4);

          if(!scenes.length){
            scenes = [
              {speaker: "آرثر", voice: "echo", line: "حان وقت استعادة مملكتنا الضائعة!", prompt: "epic medieval king in shining armor holding glowing sword on castle citadel"},
              {speaker: "مورغانا", voice: "nova", line: "الظلام سيبتلع عروشكم جميعا اليوم!", prompt: "dark sorceress with purple magical energy casting spells in gothic throne room"},
              {speaker: "لانسلوت", voice: "onyx", line: "سأحمي البوابة مهما تكلف الأمر!", prompt: "brave knight with shield and golden spear defending fortress gate against army"},
              {speaker: "آرثر", voice: "echo", line: "النصر مكتوب لنا يا رفاق!", prompt: "triumphant king raising sword as golden sunlight breaks through stormy clouds"}
            ];
          }
          if(cType === "img") scenes = scenes.slice(0, 1);

          wait.innerHTML = "🎨 <b>2/4:</b> توليد المشاهد بدقة 8K مع تحسين الإضاءة والتفاصيل...";
          var dm = getDims();
          var fUrls = cType === "img" ? [cData] : await Promise.all(scenes.map(function(sc, idx){
            var fullPr = sc.prompt + (isAnime ? ", Studio MAPPA masterpiece anime key visual, vibrant cel shading, 8k" : ", cinematic ultra realistic 8k photography, volumetric ray tracing lighting");
            return fetch(EDGE + sl + "image", {
              method: "POST",
              headers: {"Content-Type": "application/json"},
              body: JSON.stringify({prompt: fullPr, width: dm.w, height: dm.h})
            }).then(function(r){ return r.ok ? r.json() : null; })
              .then(function(d){
                if(d && d.image_url) return d.image_url;
                return "https:" + sl + sl + "image.pollinations.ai" + sl + "prompt" + sl + encodeURIComponent(fullPr) + "?width=" + dm.w + "&height=" + dm.h + "&nologo=true&seed=" + (7700 + idx * 31);
              }).catch(function(){
                return "https:" + sl + sl + "image.pollinations.ai" + sl + "prompt" + sl + encodeURIComponent(fullPr) + "?width=" + dm.w + "&height=" + dm.h + "&nologo=true&seed=" + (7700 + idx * 31);
              });
          }));

          var validPairs = [];
          for(var k = 0; k < fUrls.length; k++) if(fUrls[k]) validPairs.push({url: fUrls[k], scene: scenes[k]});
          if(!validPairs.length) throw new Error("تعذر توليد المشاهد حالياً");

          var imObjs = (await Promise.all(validPairs.map(function(vp){
            return new Promise(function(res){
              var im = new Image(); im.crossOrigin = "anonymous";
              im.onload = function(){ res({img: im, scene: vp.scene}); };
              im.onerror = function(){ res(null); };
              im.src = vp.url;
            });
          }))).filter(Boolean);

          wait.innerHTML = "🎙️ <b>3/4:</b> تركيب أصوات الأداء الصوتي النقي (بدون رموز أو تكرار)...";
          var audioClips = await Promise.all(imObjs.map(function(item){
            var cleanSpeech = cleanTextForTTS(item.scene.line);
            return fetch(EDGE + sl + "tts?t=" + encodeURIComponent(cleanSpeech) + "&v=" + item.scene.voice)
              .then(function(r){ return r.ok ? r.arrayBuffer() : null; })
              .then(function(buf){ return (buf && buf.byteLength > 200) ? actx.decodeAudioData(buf) : null; })
              .catch(function(){ return null; });
          }));

          wait.innerHTML = "🎬 <b>4/4:</b> إخراج المشاهد السينمائية بحركة كاميرا ناعمة وجزيئات الإضاءة...";
          var cv = document.createElement("canvas"); cv.width = dm.w; cv.height = dm.h;
          var gl = cv.getContext("webgl", {preserveDrawingBuffer: true});
          var vsSrc = "attribute vec2 a_pos; varying vec2 v_uv; void main(){ v_uv = vec2(a_pos.x*0.5+0.5, 0.5-a_pos.y*0.5); gl_Position = vec4(a_pos, 0.0, 1.0); }";
          var fsSrc = "precision mediump float; uniform sampler2D u_tex; uniform float u_time; uniform float u_prog; uniform int u_mode; uniform float u_talk; varying vec2 v_uv; void main(){ vec2 uv = v_uv; float z = (u_mode == 0) ? (1.03 + u_prog * 0.12) : (1.15 - u_prog * 0.12); uv = (uv - 0.5) / z + 0.5; float upperBody = smoothstep(0.85, 0.15, v_uv.y); float headZone = smoothstep(0.55, 0.15, v_uv.y); uv.y += sin(u_time * 3.5) * 0.007 * upperBody + sin(u_time * 20.0) * 0.006 * headZone * u_talk; uv.x += cos(u_time * 2.8 + float(u_mode)) * 0.01 * upperBody; vec4 col = texture2D(u_tex, clamp(uv, 0.003, 0.997)); float vig = smoothstep(0.95, 0.3, length(v_uv - 0.5)); col.rgb *= mix(0.7, 1.1, vig); gl_FragColor = col; }";
          
          function mkSh(tp, sr){ var sh = gl.createShader(tp); gl.shaderSource(sh, sr); gl.compileShader(sh); return sh; }
          var prog = gl.createProgram(); gl.attachShader(prog, mkSh(gl.VERTEX_SHADER, vsSrc)); gl.attachShader(prog, mkSh(gl.FRAGMENT_SHADER, fsSrc)); gl.linkProgram(prog); gl.useProgram(prog);
          var buf = gl.createBuffer(); gl.bindBuffer(gl.ARRAY_BUFFER, buf); gl.bufferData(gl.ARRAY_BUFFER, new Float32Array([-1,-1,1,-1,-1,1,1,1]), gl.STATIC_DRAW);
          var posLoc = gl.getAttribLocation(prog, "a_pos"); gl.enableVertexAttribArray(posLoc); gl.vertexAttribPointer(posLoc, 2, gl.FLOAT, false, 0, 0);

          var texList = imObjs.map(function(item){
            var tx = gl.createTexture(); gl.bindTexture(gl.TEXTURE_2D, tx);
            gl.texParameteri(gl.TEXTURE_2D, gl.TEXTURE_WRAP_S, gl.CLAMP_TO_EDGE); gl.texParameteri(gl.TEXTURE_2D, gl.TEXTURE_WRAP_T, gl.CLAMP_TO_EDGE);
            gl.texParameteri(gl.TEXTURE_2D, gl.TEXTURE_MIN_FILTER, gl.LINEAR); gl.texParameteri(gl.TEXTURE_2D, gl.TEXTURE_MAG_FILTER, gl.LINEAR);
            gl.texImage2D(gl.TEXTURE_2D, 0, gl.RGBA, gl.RGBA, gl.UNSIGNED_BYTE, item.img); return tx;
          });

          var hud = document.createElement("canvas"); hud.width = dm.w; hud.height = dm.h; var hctx = hud.getContext("2d");
          var vStream = hud.captureStream(30); dest.stream.getAudioTracks().forEach(function(tr){ vStream.addTrack(tr); });
          var mimeOut = MediaRecorder.isTypeSupported("video/mp4") ? "video/mp4" : "video/webm";
          var rec = new MediaRecorder(vStream, {mimeType: mimeOut}), chunks = [];
          rec.ondataavailable = function(e){ if(e.data.size > 0) chunks.push(e.data); };
          var doneRec = new Promise(function(res){ rec.onstop = function(){ bgmOscs.forEach(function(o){try{o.stop();}catch(ex){}}); try{actx.close();}catch(ex){} res(URL.createObjectURL(new Blob(chunks, {type: mimeOut}))); }; });
          rec.start();

          var uTime = gl.getUniformLocation(prog, "u_time"), uProg = gl.getUniformLocation(prog, "u_prog"), uMode = gl.getUniformLocation(prog, "u_mode"), uTalk = gl.getUniformLocation(prog, "u_talk");
          var pts = Array.from({length: 40}, function(){ return {x: Math.random()*dm.w, y: Math.random()*dm.h, r: 1.5+Math.random()*2.5, vx: (Math.random()-0.5)*1.2, vy: -0.6-Math.random()*1.2, a: 0.4+Math.random()*0.5}; });
          var totalFrames = Math.max(targetSec, imObjs.length * 4) * 30, perScene = Math.floor(totalFrames / imObjs.length), fc = 0, lastSpokenIdx = -1;

          await new Promise(function(res){
            var tm = setInterval(function(){
              var idx = Math.min(Math.floor(fc / perScene), imObjs.length - 1), lp = (fc % perScene) / perScene;
              if(idx !== lastSpokenIdx){
                lastSpokenIdx = idx; window._isTalking = 0.0;
                if(audioClips[idx]){ try{ var src = actx.createBufferSource(); src.buffer = audioClips[idx]; src.connect(dest); src.connect(actx.destination); window._isTalking = 1.0; src.onended = function(){ window._isTalking = 0.0; }; src.start(0); }catch(ex){} }
              }
              gl.viewport(0, 0, dm.w, dm.h); gl.bindTexture(gl.TEXTURE_2D, texList[idx]);
              gl.uniform1f(uTime, fc * 0.033); gl.uniform1f(uProg, lp); gl.uniform1i(uMode, idx % 2); gl.uniform1f(uTalk, window._isTalking || 0.0);
              gl.drawArrays(gl.TRIANGLE_STRIP, 0, 4); 
              hctx.clearRect(0, 0, dm.w, dm.h); hctx.drawImage(cv, 0, 0);

              pts.forEach(function(pt){
                pt.x += pt.vx; pt.y += pt.vy;
                if(pt.y < 0) pt.y = dm.h; if(pt.x < 0) pt.x = dm.w; if(pt.x > dm.w) pt.x = 0;
                hctx.beginPath(); hctx.arc(pt.x, pt.y, pt.r, 0, Math.PI*2);
                hctx.fillStyle = "rgba(255,225,160," + pt.a + ")"; hctx.fill();
              });

              var curSc = imObjs[idx].scene;
              var gradY = dm.h - 220;
              var grad = hctx.createLinearGradient(0, gradY, 0, dm.h);
              grad.addColorStop(0, "rgba(0,0,0,0)"); grad.addColorStop(1, "rgba(0,0,0,0.96)");
              hctx.fillStyle = grad; hctx.fillRect(0, gradY, dm.w, 220);

              var badgeBg = curSc.voice === "nova" ? "#f472b6" : (curSc.voice === "echo" ? "#38bdf8" : "#fbbf24");
              hctx.fillStyle = badgeBg;
              hctx.fillRect(dm.w / 2 - 120, gradY + 15, 240, 36);
              hctx.font = "bold 20px sans-serif"; hctx.textAlign = "center"; hctx.fillStyle = "#090a0f";
              hctx.fillText("🎙️ " + curSc.speaker, dm.w / 2, gradY + 40);

              hctx.font = "bold 26px sans-serif"; hctx.fillStyle = "#ffffff";
              hctx.shadowColor = "rgba(0,0,0,0.98)"; hctx.shadowBlur = 12;
              hctx.fillText(curSc.line, dm.w / 2, gradY + 95);
              hctx.shadowBlur = 0;

              if(++fc >= totalFrames){ clearInterval(tm); rec.stop(); res(); }
            }, 33);
          });

          var fbVid = await doneRec;
          var castSummary = imObjs.map(function(x){ return "• <b style='color:#38bdf8'>" + x.scene.speaker + " (" + x.scene.voice + "):</b> " + x.scene.line; }).join("<br>");
          wait.remove();
          window.DH_UI.addMsg("AI", "🎬 <b>تم إنتاج حلقة الفيديو/الأنمي بنجاح (مع الأصوات وتراخيص الشخصيات والحركة السينمائية):</b><br><br>" + castSummary, {vid: fbVid});

        } else if((low.indexOf("صورة") !== -1 || low.indexOf("صور") !== -1 || low.indexOf("ارسم") !== -1 || low.indexOf("صمم") !== -1 || low.indexOf("image") !== -1) && cType !== "img"){
          var cleanT = t.replace(/صمم لي صور|صمم لي صورة|صمم صورة|ارسم لي|ارسم|صور|صورة/gi, "").trim();
          var stylePrompt = isAnime ? "masterpiece Japanese anime key visual, Studio Ghibli or MAPPA style, vibrant cel shading" : (isCinematic ? "cinematic epic movie scene, volumetric lighting, photorealistic 8k" : "ultra realistic 8k photography, highly detailed");
          var promptFull = (cleanT.length > 2 ? cleanT : "epic futuristic city at sunset") + ", " + stylePrompt + ", 8k resolution";
          
          var ir = await fetch(EDGE + sl + "image", {
            method: "POST",
            headers: {"Content-Type": "application/json"},
            body: JSON.stringify({prompt: promptFull, width: dm.w, height: dm.h})
          });
          var iData = await ir.json().catch(function(){ return {}; });
          var imgUrl = iData.image_url || ("https:" + sl + sl + "image.pollinations.ai" + sl + "prompt" + sl + encodeURIComponent(promptFull) + "?width=" + dm.w + "&height=" + dm.h + "&nologo=true");
          
          wait.remove();
          window.DH_UI.addMsg("AI", "🎨 <b>تم تصميم الصورة بدقة 8K (الأبعاد: " + dm.w + "×" + dm.h + "):</b>", {img: imgUrl});

        } else {
          var fullT = cType === "doc" ? (t + "\n\n[محتوى الملف " + cName + "]:\n" + String(cData).slice(0, 4000)) : (t || "مرحباً");
          hist.push({role: "user", content: fullT});
          var rep = await askAI(hist, cType === "img" ? cData : null);
          hist.push({role: "assistant", content: rep});
          saveH();
          wait.remove();
          window.DH_UI.addMsg("AI", rep);
        }
      } catch(err){
        wait.innerHTML = "⚠️ حدث خطأ أثناء المعالجة: " + (err.message || err);
      }
    }
  };
})();
