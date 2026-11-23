
window.tryRealVideo = async function(promptTxt) {
  try {
    var r = await fetch(EDGE + "/video", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ prompt: promptTxt })
    });
    if (r.ok) {
      var d = await r.json();
      if (d && d.video_url) return d.video_url;
    }
  } catch (e) {}
  return null;
};

window.enhanceViaTermux = async function(blob, mime) { try { var r = await fetch("http://127.0.0.1:5050", { method: "POST", headers: { "Content-Type": mime }, body: blob }); if (r.ok) return await r.blob(); } catch (e) {} return blob; };

window.DH_VOICE_PROFILES = [
  { pitch: 1.22, rate: 1.02 },
  { pitch: 0.78, rate: 0.94 },
  { pitch: 1.08, rate: 1.05 },
  { pitch: 0.85, rate: 0.98 }
];
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
      var wait = window.DH_UI.addMsg("AI", "⚡ جاري المعالجة السينمائية والذكاء الاصطناعي...");
      var low = t.toLowerCase();
      var isAnime = low.indexOf("انمي") !== -1 || low.indexOf("أنمي") !== -1 || low.indexOf("كرتون") !== -1 || low.indexOf("anime") !== -1;
      var isCinematic = low.indexOf("سينما") !== -1 || low.indexOf("هوليوود") !== -1 || low.indexOf("سينمائي") !== -1 || low.indexOf("cinematic") !== -1;

      try{
        if(low.indexOf("فيديو") !== -1 || low.indexOf("مقطع") !== -1 || low.indexOf("تحريك") !== -1 || low.indexOf("انمي") !== -1 || low.indexOf("أنمي") !== -1 || low.indexOf("حلقة") !== -1 || low.indexOf("video") !== -1){
          var cleanV = t.replace(/صمم لي فيديو|صمم فيديو|اصنع فيديو|انشئ فيديو|اصنع حلقة|فيديو|مقطع|\d+\s*(ثاني|ثوان|sec|s)/gi, "").trim() || "ملحمة سينمائية مذهلة بين الأبطال وقوى الظلام والطبيعة";

          wait.innerHTML = "🎬 <b>1/3:</b> محاولة توليد فيديو MP4 حقيقي من نماذج Hugging Face (LTX / Wan / CogVideo)...";
          let videoUrl = null;
          try {
            var vr = await fetch(EDGE + sl + "video", {
              method: "POST",
              headers: {"Content-Type": "application/json"},
              body: JSON.stringify({prompt: cleanV + ", cinematic masterpiece 8k"})
            });
            if(vr.ok){
              var vBlob = await vr.blob();
              if(vBlob.size > 2000){
                videoUrl = URL.createObjectURL(vBlob);
              }
            }
          } catch(e){}

          if(videoUrl){
            wait.remove();
            window.DH_UI.addMsg("AI", "🎬 <b>تم إنتاج فيديو MP4 الحقيقي بنجاح:</b>", {vid: videoUrl});
            return;
          }

          wait.innerHTML = "🌊 <b>2/3:</b> تشغيل محرك الاحتياط السينمائي WebGL مع مؤثرات البحر والسيوف والأصوات...";
          var actx = new (window.AudioContext || window.webkitAudioContext)();
          if(actx.state === "suspended") await actx.resume();
          var dest = actx.createMediaStreamDestination();
          var bgmGain = actx.createGain(); bgmGain.gain.value = 0.05; bgmGain.connect(dest); bgmGain.connect(actx.destination);
          var bgmOscs = [90.0, 135.0, 180.0].map(function(fq){ var o = actx.createOscillator(); o.type = "sine"; o.frequency.value = fq; o.connect(bgmGain); o.start(); return o; });

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
              {speaker: "آرثر", voice: "echo", line: "أمواج البحر تخفي أسرار عظمى!", prompt: "epic medieval king standing by stormy sea waves and clashing swords"},
              {speaker: "مورغانا", voice: "nova", line: "قوى الطبيعة ستنقاد لنا وحدنا!", prompt: "dark sorceress casting magical spells over stormy ocean and lightning"},
              {speaker: "لانسلوت", voice: "onyx", line: "سأحمي الشاطئ بسيفي ودرعي!", prompt: "brave knight with shining sword defending ocean cliff against storm"},
              {speaker: "آرثر", voice: "echo", line: "النصر لنا مع شروق الشمس!", prompt: "triumphant king raising sword as golden sunlight breaks over the sea"}
            ];
          }

          var dm = getDims();
          var fUrls = await Promise.all(scenes.map(function(sc, idx){
            var fullPr = sc.prompt + (isAnime ? ", Studio MAPPA masterpiece anime key visual, 8k" : ", cinematic ultra realistic 8k photography, ocean waves, sword sparks");
            return fetch(EDGE + sl + "image", {
              method: "POST",
              headers: {"Content-Type": "application/json"},
              body: JSON.stringify({prompt: fullPr, width: dm.w, height: dm.h})
            }).then(function(r){ return r.ok ? r.json() : null; })
              .then(function(d){
                if(d && d.image_url) return d.image_url;
                return "https:" + sl + sl + "image.pollinations.ai" + sl + "prompt" + sl + encodeURIComponent(fullPr) + "?width=" + dm.w + "&height=" + dm.h + "&nologo=true&seed=" + (5500 + idx * 19);
              }).catch(function(){
                return "https:" + sl + sl + "image.pollinations.ai" + sl + "prompt" + sl + encodeURIComponent(fullPr) + "?width=" + dm.w + "&height=" + dm.h + "&nologo=true&seed=" + (5500 + idx * 19);
              });
          }));

          var validPairs = [];
          for(var k = 0; k < fUrls.length; k++) if(fUrls[k]) validPairs.push({url: fUrls[k], scene: scenes[k]});
          if(!validPairs.length) throw new Error("تعذر توليد المشاهد");

          var imObjs = (await Promise.all(validPairs.map(function(vp){
            return new Promise(function(res){
              var im = new Image(); im.crossOrigin = "anonymous";
              im.onload = function(){ res({img: im, scene: vp.scene}); };
              im.onerror = function(){ res(null); };
              im.src = vp.url;
            });
          }))).filter(Boolean);

          var audioClips = await Promise.all(imObjs.map(function(item){
            var cleanSpeech = cleanTextForTTS(item.scene.line);
            return fetch(EDGE + sl + "tts?t=" + encodeURIComponent(cleanSpeech) + "&v=" + item.scene.voice)
              .then(function(r){ return r.ok ? r.arrayBuffer() : null; })
              .then(function(buf){ return (buf && buf.byteLength > 200) ? actx.decodeAudioData(buf) : null; })
              .catch(function(){ return null; });
          }));

          wait.innerHTML = "🎬 <b>3/3:</b> تسيير الفيديو الاحتياطي السينمائي مع الأداء الصوتي والمؤثرات...";
          var cv = document.createElement("canvas"); cv.width = dm.w; cv.height = dm.h;
          var gl = cv.getContext("webgl", {preserveDrawingBuffer: true});
          var vsSrc = "attribute vec2 a_pos; varying vec2 v_uv; void main(){ v_uv = vec2(a_pos.x*0.5+0.5, 0.5-a_pos.y*0.5); gl_Position = vec4(a_pos, 0.0, 1.0); }";
          var fsSrc = "precision mediump float; uniform sampler2D u_tex; uniform float u_time; uniform float u_prog; uniform int u_mode; uniform float u_talk; varying vec2 v_uv; void main(){ vec2 uv = v_uv; float z = (u_mode == 0) ? (1.04 + u_prog * 0.12) : (1.16 - u_prog * 0.12); uv = (uv - 0.5) / z + 0.5; uv.y += sin(u_time * 4.0) * 0.008 + sin(u_time * 22.0) * 0.006 * u_talk; uv.x += cos(u_time * 3.0) * 0.01; vec4 col = texture2D(u_tex, clamp(uv, 0.003, 0.997)); col.rgb *= mix(0.7, 1.1, smoothstep(0.95, 0.3, length(v_uv - 0.5))); gl_FragColor = col; }";
          
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
          var pts = Array.from({length: 45}, function(){ return {x: Math.random()*dm.w, y: Math.random()*dm.h, r: 1.5+Math.random()*3, vx: (Math.random()-0.5)*1.5, vy: -0.8-Math.random()*1.5, a: 0.4+Math.random()*0.5}; });
          var totalFrames = 30 * 12, perScene = Math.floor(totalFrames / imObjs.length), fc = 0, lastSpokenIdx = -1;

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
                hctx.fillStyle = "rgba(100,220,255," + pt.a + ")"; hctx.fill();
              });

              var curSc = imObjs[idx].scene;
              var gradY = dm.h - 210;
              var grad = hctx.createLinearGradient(0, gradY, 0, dm.h);
              grad.addColorStop(0, "rgba(0,0,0,0)"); grad.addColorStop(1, "rgba(0,0,0,0.96)");
              hctx.fillStyle = grad; hctx.fillRect(0, gradY, dm.w, 210);

              var badgeBg = curSc.voice === "nova" ? "#f472b6" : (curSc.voice === "echo" ? "#38bdf8" : "#fbbf24");
              hctx.fillStyle = badgeBg;
              hctx.fillRect(dm.w / 2 - 120, gradY + 12, 240, 34);
              hctx.font = "bold 19px sans-serif"; hctx.textAlign = "center"; hctx.fillStyle = "#090a0f";
              hctx.fillText("🌊 ⚔️ " + curSc.speaker, dm.w / 2, gradY + 35);

              hctx.font = "bold 25px sans-serif"; hctx.fillStyle = "#ffffff";
              hctx.shadowColor = "rgba(0,0,0,0.98)"; hctx.shadowBlur = 12;
              hctx.fillText(curSc.line, dm.w / 2, gradY + 85);
              hctx.shadowBlur = 0;

              if(++fc >= totalFrames){ clearInterval(tm); rec.stop(); res(); }
            }, 33);
          });

          var fbVid = await doneRec;
          var castSummary = imObjs.map(function(x){ return "• <b style='color:#38bdf8'>" + x.scene.speaker + " (" + x.scene.voice + "):</b> " + x.scene.line; }).join("<br>");
          wait.remove();
          window.DH_UI.addMsg("AI", "🎬 <b>تم إنتاج الفيديو السينمائي الاحتياطي (أصوات + بحر وسيوف + ترجمة):</b><br><br>" + castSummary, {vid: fbVid});

        } else if((low.indexOf("صورة") !== -1 || low.indexOf("صور") !== -1 || low.indexOf("ارسم") !== -1 || low.indexOf("صمم") !== -1 || low.indexOf("image") !== -1) && cType !== "img"){
          var cleanT = t.replace(/صمم لي صور|صمم لي صورة|صمم صورة|ارسم لي|ارسم|صور|صورة/gi, "").trim();
          var stylePrompt = isAnime ? "masterpiece Japanese anime key visual, Studio Ghibli or MAPPA style, vibrant cel shading" : (isCinematic ? "cinematic epic movie scene, volumetric lighting, photorealistic 8k" : "ultra realistic 8k photography, highly detailed");
          var promptFull = (cleanT.length > 2 ? cleanT : "epic futuristic city at sunset") + ", " + stylePrompt + ", 8k resolution";
          
          var dm = getDims();
          var ir = await fetch(EDGE + sl + "image", {
            method: "POST",
            headers: {"Content-Type": "application/json"},
            body: JSON.stringify({prompt: promptFull, width: dm.w, height: dm.h})
          });
          var iData = await ir.json().catch(function(){ return {}; });
          if(!iData || !iData.image_url) throw new Error("الخادم مشغول بتوليد الصورة، أعد المحاولة بعد ثوانٍ"); var imgUrl = iData.image_url;
          
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
