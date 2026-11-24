#!/usr/bin/env python3
"""Faceless short-video engine.

Usage: python3 make_video.py story.json OUT_DIR

story.json:
{
  "slug": "the-last-caller",
  "style": "dark cinematic digital painting, moody lighting, film grain",
  "motion": "dynamic",   # optional; "static" (default, slow zoom) or "dynamic" (camera moves, fog, flicker)
  "scenes": [{"text": "Narration sentence(s)...", "image_prompt": "what the picture shows"}, ...]
}
Produces OUT_DIR/<slug>.mp4 (1080x1920, 30fps) and OUT_DIR/<slug>.jpg (cover).
"""
import json, os, sys, subprocess, wave, re, urllib.parse, urllib.request, time, random, shutil

HERE = os.path.dirname(os.path.abspath(__file__))
VOICE_DIR = os.path.expanduser("~/.faceless_voices")
VOICE = "en_US-ryan-high"
VOICE_URL = "https://huggingface.co/rhasspy/piper-voices/resolve/main/en/en_US/ryan/high/"
FONT_DIR = os.path.join(HERE, "fonts")
W, H, FPS = 1080, 1920, 30


def sh(cmd):
    r = subprocess.run(cmd, capture_output=True, text=True)
    if r.returncode:
        sys.stderr.write(r.stderr[-3000:])
        raise SystemExit(f"command failed: {cmd[:3]}")
    return r.stdout


def ensure_voice():
    os.makedirs(VOICE_DIR, exist_ok=True)
    for ext in (".onnx", ".onnx.json"):
        p = os.path.join(VOICE_DIR, VOICE + ext)
        if not os.path.exists(p) or os.path.getsize(p) < 1000:
            urllib.request.urlretrieve(VOICE_URL + VOICE + ext, p)
    return os.path.join(VOICE_DIR, VOICE + ".onnx")


def tts(scenes, work):
    from piper import PiperVoice
    from piper.config import SynthesisConfig
    voice = PiperVoice.load(ensure_voice())
    cfg = SynthesisConfig(length_scale=1.08, noise_scale=0.6, noise_w_scale=0.8)
    pieces, times, t = [], [], 0.0
    gap = 0.35
    rate = None
    for i, sc in enumerate(scenes):
        p = os.path.join(work, f"v{i}.wav")
        with wave.open(p, "wb") as wf:
            voice.synthesize_wav(sc["text"], wf, syn_config=cfg)
        with wave.open(p) as wf:
            rate = wf.getframerate()
            d = wf.getnframes() / rate
        pieces.append(p)
        times.append((t, t + d + gap))
        t += d + gap
    # concat with gaps
    out = os.path.join(work, "narration.wav")
    with wave.open(out, "wb") as o:
        o.setnchannels(1); o.setsampwidth(2); o.setframerate(rate)
        silence = b"\x00\x00" * int(rate * gap)
        for p in pieces:
            with wave.open(p) as wf:
                o.writeframes(wf.readframes(wf.getnframes()))
            o.writeframes(silence)
    return out, times, t


def fetch_image(prompt, style, path, seed):
    full = f"{prompt}, {style}, vertical composition, highly detailed, no text, no watermark"
    url = ("https://image.pollinations.ai/prompt/" + urllib.parse.quote(full) +
           f"?width=1080&height=1920&nologo=true&seed={seed}&model=flux")
    for attempt in range(4):
        try:
            req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
            with urllib.request.urlopen(req, timeout=180) as r:
                data = r.read()
            if len(data) > 20000:
                open(path, "wb").write(data)
                return True
        except Exception as e:
            sys.stderr.write(f"image retry {attempt}: {e}\n")
        time.sleep(10 + attempt * 15)
    # fallback: dark gradient so the pipeline never stops
    sh(["ffmpeg", "-y", "-v", "error", "-f", "lavfi", "-i",
        f"gradients=s={W}x{H}:c0=0x0a0a12:c1=0x2a0d0d:duration=1", "-frames:v", "1", path])
    return False


def scene_clip(img, dur, idx, path, motion="static", fog=None):
    frames = int(round(dur * FPS))
    if motion != "dynamic":
        zin = idx % 2 == 0
        z = "min(1.0+0.0009*on,1.25)" if zin else "max(1.25-0.0009*on,1.0)"
        vf = (f"crop=iw:ih*0.94:0:0,scale={W*2}:{H*2}:force_original_aspect_ratio=increase,crop={W*2}:{H*2},"
              f"zoompan=z='{z}':x='iw/2-(iw/zoom/2)':y='ih/2-(ih/zoom/2)':d={frames}:s={W}x{H}:fps={FPS},"
              f"eq=contrast=1.08:saturation=0.85:brightness=0.0,vignette=PI/4,"
              f"noise=alls=3:allf=t,format=yuv420p")
        sh(["ffmpeg", "-y", "-v", "error", "-loop", "1", "-i", img, "-vf", vf,
            "-frames:v", str(frames), "-c:v", "libx264", "-preset", "veryfast", "-crf", "20", path])
        return
    # "dynamic": eased camera moves (push, pan, pull, tilt), drifting fog, light flicker, grain.
    e = f"((1-cos(PI*min(on/{frames},1)))/2)"
    moves = [
        (f"1.0+0.24*{e}", "iw/2-(iw/zoom/2)", "ih/2-(ih/zoom/2)"),            # push in
        ("1.2", f"(iw-iw/zoom)*{e}", "ih/2-(ih/zoom/2)"),                    # pan left->right
        (f"1.26-0.24*{e}", "iw/2-(iw/zoom/2)", "ih/2-(ih/zoom/2)"),          # pull out
        ("1.2", "iw/2-(iw/zoom/2)", f"(ih-ih/zoom)*(1-{e})"),                # tilt up
        (f"1.12+0.1*{e}", f"(iw-iw/zoom)*(1-{e})", "ih/2-(ih/zoom/2)"),      # pan right->left + push
    ]
    z, x, y = moves[idx % len(moves)]
    off = (idx * 137) % 500  # max drift per scene ~10s*45px stays inside the 2W texture
    fc = (f"[0:v]crop=iw:ih*0.94:0:0,scale={W*2}:{H*2}:force_original_aspect_ratio=increase,crop={W*2}:{H*2},"
          f"zoompan=z='{z}':x='{x}':y='{y}':d={frames}:s={W}x{H}:fps={FPS},"
          f"eq=contrast=1.1:saturation=0.8:brightness='-0.015+0.03*sin(5.3*t)*sin(1.9*t+{idx})':eval=frame,"
          f"format=gbrp[base];"
          f"[1:v]crop={W}:{H}:x='min(t*45+{off},{W})':y=0,format=gbrp[fog];"
          f"[base][fog]blend=all_mode=screen:all_opacity=0.22,vignette=PI/4,"
          f"noise=alls=6:allf=t,fade=t=in:st=0:d=0.25,format=yuv420p[v]")
    sh(["ffmpeg", "-y", "-v", "error", "-loop", "1", "-i", img, "-loop", "1", "-i", fog,
        "-filter_complex", fc, "-map", "[v]",
        "-frames:v", str(frames), "-r", str(FPS), "-c:v", "libx264", "-preset", "veryfast", "-crf", "20", path])


def make_fog(path):
    """Soft cloudy texture twice the frame width; each scene crops a slowly drifting window."""
    sh(["ffmpeg", "-y", "-v", "error", "-f", "lavfi", "-i", f"color=c=black:s={W//4}x{H//8}",
        "-vf", f"noise=alls=100:allf=u,gblur=sigma=6,eq=contrast=2.2:brightness=-0.25,"
               f"scale={W*2}:{H}:flags=bicubic,gblur=sigma=40,format=gray",
        "-frames:v", "1", path])


def _align(script_words, ws, t0, t1):
    """Map script words onto whisper words [(word,start,end)] inside one scene window [t0,t1]."""
    import difflib
    norm = lambda x: re.sub(r"[^a-z0-9']", "", x.lower())
    out = [None] * len(script_words)
    if ws:
        sm = difflib.SequenceMatcher(a=[norm(w) for w in script_words], b=[norm(w[0]) for w in ws],
                                     autojunk=False)
        for blk in sm.get_matching_blocks():
            for k in range(blk.size):
                out[blk.a + k] = (ws[blk.b + k][1], ws[blk.b + k][2])
    known = [i for i, v in enumerate(out) if v]
    # unmatched words: spread by character length between the nearest matched neighbours
    i = 0
    while i < len(out):
        if out[i] is not None:
            i += 1; continue
        j = i
        while j < len(out) and out[j] is None:
            j += 1
        g0 = out[i - 1][1] if i > 0 else (t0 if not known else min(t0 + 0.05, out[known[0]][0]))
        g1 = out[j][0] if j < len(out) else (ws[-1][2] if ws else t1)
        if g1 <= g0:
            g1 = g0 + 0.15 * (j - i)
        lens = [len(w) + 1 for w in script_words[i:j]]
        tot, c = sum(lens), g0
        for k, L in enumerate(lens):
            d = (g1 - g0) * L / tot
            out[i + k] = (c, c + d); c += d
        i = j
    return [(script_words[k], max(t0, min(out[k][0], t1)), max(t0, min(out[k][1], t1)))
            for k in range(len(out))]


def words_timing(work, scenes, times):
    """Word timestamps aligned per scene: whisper on each scene's own clip, offset by its known start,
    so drift can never accumulate across scenes."""
    model = None
    try:
        import numpy as np
        from faster_whisper import WhisperModel
        model = WhisperModel("base.en", compute_type="int8")
    except Exception as e:
        sys.stderr.write(f"whisper unavailable, using estimate: {e}\n")
    res = []
    for i, sc in enumerate(scenes):
        script_words = sc["text"].split()
        t0, t1 = times[i]
        ws = []
        if model is not None:
            try:
                with wave.open(os.path.join(work, f"v{i}.wav")) as wf:
                    sr = wf.getframerate()
                    a = np.frombuffer(wf.readframes(wf.getnframes()), np.int16).astype(np.float32) / 32768
                if sr != 16000:
                    idx = np.linspace(0, len(a) - 1, int(len(a) * 16000 / sr)).astype(int)
                    a = a[idx]
                segs, _ = model.transcribe(a, word_timestamps=True, initial_prompt=sc["text"])
                ws = [(w.word.strip(), t0 + w.start, t0 + w.end) for s_ in segs for w in s_.words]
            except Exception as e:
                sys.stderr.write(f"whisper failed on scene {i}: {e}\n")
        res += _align(script_words, ws, t0, t1)
    return res


def ass_time(t):
    t = max(t, 0)
    return f"{int(t//3600)}:{int(t%3600//60):02d}:{t%60:05.2f}"


def write_ass(words, path):
    chunks, cur = [], []
    for w in words:
        cur.append(w)
        if len(cur) >= 3 or re.search(r"[.,!?;:…]$", w[0]):
            chunks.append(cur); cur = []
    if cur: chunks.append(cur)
    head = f"""[Script Info]
ScriptType: v4.00+
PlayResX: {W}
PlayResY: {H}
WrapStyle: 0

[V4+ Styles]
Format: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, OutlineColour, BackColour, Bold, Italic, Underline, StrikeOut, ScaleX, ScaleY, Spacing, Angle, BorderStyle, Outline, Shadow, Alignment, MarginL, MarginR, MarginV, Encoding
Style: Cap,Anton,118,&H00FFFFFF,&H00FFFFFF,&H00000000,&H96000000,0,0,0,0,100,100,2,0,1,8,4,5,70,70,0,1

[Events]
Format: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text
"""
    lines = []
    for ci, ch in enumerate(chunks):
        end_chunk = chunks[ci + 1][0][1] if ci + 1 < len(chunks) else ch[-1][2] + 0.4
        for wi, w in enumerate(ch):
            st = w[1]
            en = ch[wi + 1][1] if wi + 1 < len(ch) else end_chunk
            parts = []
            for k, x in enumerate(ch):
                txt = x[0].upper().replace("{", "").replace("}", "")
                parts.append("{\\c&H0033D7FF&\\fscx108\\fscy108}" + txt + "{\\c&H00FFFFFF&\\fscx100\\fscy100}"
                             if k == wi else txt)
            pos = "{\\an5\\pos(540,1180)}"
            lines.append(f"Dialogue: 0,{ass_time(st)},{ass_time(en)},Cap,,0,0,0,,{pos}{' '.join(parts)}")
    open(path, "w").write(head + "\n".join(lines) + "\n")


def main():
    story = json.load(open(sys.argv[1]))
    outdir = os.path.abspath(sys.argv[2])
    os.makedirs(outdir, exist_ok=True)
    slug = re.sub(r"[^a-z0-9-]+", "-", story.get("slug", "video").lower()).strip("-")
    work = os.path.join(outdir, "_work_" + slug)
    os.makedirs(work, exist_ok=True)
    scenes = story["scenes"]
    style = story.get("style", "dark cinematic digital painting, eerie atmosphere, dramatic shadows")

    narr, times, total = tts(scenes, work)
    print(f"narration {total:.1f}s, {len(scenes)} scenes", flush=True)

    motion = story.get("motion", "static")
    fog = None
    if motion == "dynamic":
        fog = os.path.join(work, "fog.png")
        make_fog(fog)

    base_seed = random.randint(1, 10**6)
    clips = []
    for i, sc in enumerate(scenes):
        img = os.path.join(work, f"img{i}.jpg")
        ok = os.path.exists(img) and os.path.getsize(img) > 20000
        if not ok:
            ok = fetch_image(sc["image_prompt"], style, img, base_seed + i)
            time.sleep(3)
        print(f"image {i}: {'ai' if ok else 'fallback'}", flush=True)
        c = os.path.join(work, f"clip{i}.mp4")
        scene_clip(img, times[i][1] - times[i][0], i, c, motion, fog)
        clips.append(c)
        if i == 0:
            shutil.copy(img, os.path.join(outdir, slug + ".jpg"))

    lst = os.path.join(work, "list.txt")
    open(lst, "w").write("".join(f"file '{c}'\n" for c in clips))
    silent = os.path.join(work, "silent.mp4")
    sh(["ffmpeg", "-y", "-v", "error", "-f", "concat", "-safe", "0", "-i", lst, "-c", "copy", silent])

    words = words_timing(work, scenes, times)
    ass = os.path.join(work, "caps.ass")
    write_ass(words, ass)

    out = os.path.join(outdir, slug + ".mp4")
    # ambient drone bed: low detuned sines + filtered brown noise
    drone = (f"aevalsrc='0.5*sin(2*PI*55*t)+0.35*sin(2*PI*55.7*t)+0.2*sin(2*PI*82.4*t)*(0.6+0.4*sin(2*PI*0.07*t))':"
             f"s=44100:d={total+0.5}")
    fc = (f"[0:v]ass={ass}:fontsdir={FONT_DIR},fade=t=in:st=0:d=0.4,fade=t=out:st={total-0.6:.2f}:d=0.6[v];"
          f"[1:a]aresample=44100,volume=1.6,acompressor=threshold=-18dB:ratio=3[n];"
          f"[2:a]volume=0.05[d];[3:a]lowpass=f=400,volume=0.08[b];"
          f"[n][d][b]amix=inputs=3:duration=first:normalize=0,alimiter=limit=0.95,"
          f"afade=t=out:st={total-0.6:.2f}:d=0.6[a]")
    sh(["ffmpeg", "-y", "-v", "error", "-i", silent, "-i", narr,
        "-f", "lavfi", "-i", drone,
        "-f", "lavfi", "-i", f"anoisesrc=c=brown:a=0.5:d={total+0.5}:r=44100",
        "-filter_complex", fc, "-map", "[v]", "-map", "[a]",
        "-c:v", "libx264", "-preset", "veryfast", "-crf", "24", "-maxrate", "6M", "-bufsize", "12M", "-pix_fmt", "yuv420p",
        "-c:a", "aac", "-b:a", "192k", "-movflags", "+faststart", "-t", f"{total:.2f}", out])
    shutil.rmtree(work, ignore_errors=True)
    print(json.dumps({"video": out, "cover": os.path.join(outdir, slug + ".jpg"), "duration": round(total, 1)}))


if __name__ == "__main__":
    main()
