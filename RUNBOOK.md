# Daily faceless-shorts run

Goal: publish one new original scary-story short per day to Instagram Reels + YouTube Shorts
(+ TikTok once it is connected in Metricool). Fully unattended: never stop to ask questions.

## 1. Get the repo
If `/home/claude/faceless-shorts` is not present, call `add_repo` (owner `Ishan1069`, repo
`faceless-shorts`, access `push`) and clone it there. `cd` into it. Run `bash setup.sh`.

## 1b. Pick today's series (alternate days, ONE post per day)
Two series share one daily slot (Metricool free plan ≈20 posts/month, so never post both):
```
python3 -c "import datetime,zoneinfo as z;d=datetime.datetime.now(z.ZoneInfo('America/New_York')).date();print('horror' if d.toordinal()%2 else 'mysteries')"
```
- `horror` → follow sections 2-6 as written (stories/ folder).
- `mysteries` → follow section 2M instead of section 2, then sections 3-6 with `mysteries/` in place of `stories/`.

## 2M. Write today's unsolved-mystery script (series "mysteries")
If `mysteries/YYYY-MM-DD.json` already exists for today (pre-written), use it as-is. Otherwise read the titles in
`mysteries/*.json` so you never repeat a case, then write `mysteries/YYYY-MM-DD.json` in the same shape as the story
JSON plus `"series": "mysteries"` and `"motion": "dynamic"` (camera moves, drifting fog, flicker). Use
`"style": "dark cinematic digital painting, desaturated, documentary still, <era/setting details>"`.
Rules:
- A REAL, well-documented unexplained case (vanished ships/planes/expeditions, strange signals, lost
  colonies, unexplained places/objects). Every fact must be accurate: do a quick WebSearch to confirm dates,
  numbers and names. Say "theories" for speculation; never state a theory as fact.
- Prefer older/historical cases. Avoid recent crimes, cases with living suspects or grieving families,
  graphic deaths, and anything involving harm to children. Don't name private individuals beyond what the
  standard public record uses.
- Third-person narrator, 7-9 scenes, 120-160 words. Scene 1 is a one-sentence hook. Final scene is a
  surprising true detail or the haunting open question.
- hashtags: unsolvedmysteries, mystery, history, creepy, truestory, unexplained + one case-specific tag.
- youtube_title ends with `#shorts #mystery`; caption ends with "Follow for a new unsolved mystery."
- YouTube tags in step 5 for this series: ["unsolved mysteries","mystery","history","unexplained","shorts"].

## 2. Write today's story
Read the titles in `stories/*.json` so you never repeat a premise. Write
`stories/YYYY-MM-DD.json` (today's date, America/New_York) with this shape:

```json
{
  "slug": "YYYY-MM-DD-short-kebab-title",
  "title": "Short Title",
  "youtube_title": "Hooky title under 90 chars #shorts #scarystories",
  "caption": "One-line hook that teases the twist + 'Follow for a new scary story every day.'",
  "hashtags": ["scarystories","horrortok","creepy","horrorstories","storytime","scary","horror"],
  "style": "dark cinematic digital painting, eerie moonlight, deep shadows, muted palette, horror movie still",
  "scenes": [{"text": "1-2 narration sentences", "image_prompt": "concrete visual description"}]
}
```

Story rules:
- 100% original. First person, present-day, relatable setting (home, work, road trip, phone, kid, neighbor...).
- 7-9 scenes, 120-160 words total (≈40-55 s). Scene 1 must be a hook that creates a question in one sentence.
- Build tension, end on a twist in the final scene. No gore, no real people or brands, nothing involving harm to children.
- Rotate sub-genres: paranormal, stalker/creepy stranger, urban legend, "rules" horror, sci-fi wrongness, cursed object, folklore.
- image_prompt: describe what is seen (place, objects, lighting). No text in images. Avoid showing faces up close.

## 3. Render
`python3 make_video.py stories/YYYY-MM-DD.json videos` (≈3-6 min; image host may throttle, the
script retries automatically). Confirm `videos/<slug>.mp4` exists and is under 90 MB.
Spot-check: extract 3 frames with ffmpeg and look at them; captions visible, images not blank.
If an image is the plain gradient fallback, delete `videos/_work_<slug>/img<N>.jpg` and rerun once.

## 4. Publish the file
Commit the story JSON to `main` (do NOT commit mp4/jpg to main; they are gitignored) and push.
Then publish the video on the `media` branch, replacing whatever is there:
```
bash publish_media.sh videos/<slug>.mp4 videos/<slug>.jpg
```
It prints the public raw URLs. Verify with `curl -sI <url>` → HTTP 200, content-type video/mp4.
(raw.githubusercontent.com can take ~1 minute to serve a new file; retry for up to 5 min.)

## 5. Schedule
Metricool brand `blogId` = `8214324`, timezone America/New_York.
Call `getBrandSettings`; if `networksData` now includes TikTok, add `{"network":"tiktok"}` + tiktokData
`{"privacyOption":"PUBLIC_TO_EVERYONE","title":"<title>","isAigc":true}`.
Call `createScheduledPost` with date today 19:00 ET (if that is under 30 min away or past, use now + 45 min):
```json
{"autoPublish": true, "draft": false, "descendants": [], "firstCommentText": "", "hasNotReadNotes": false,
 "media": ["<mp4 raw url>"], "mediaAltText": [],
 "providers": [{"network":"instagram"},{"network":"youtube"}],
 "publicationDate": {"dateTime":"YYYY-MM-DDT19:00:00","timezone":"America/New_York"},
 "shortener": false, "smartLinkData": {"ids": []},
 "text": "<caption>\n\n#tag1 #tag2 ...",
 "instagramData": {"type":"REEL","showReelOnFeed":true,"isAiGenerated":true},
 "youtubeData": {"title":"<youtube_title>","type":"short","privacy":"public","tags":["scary stories","horror","creepy","horror stories","shorts"],"category":"ENTERTAINMENT","madeForKids":false,"isAiGeneratedContent":true}}
```
If Metricool says the media download timed out, wait 2 minutes and retry (max 3 tries).

## 6. Report
Append a line to `LOG.md` (date, title, scheduled time, Metricool plannerUrl or error), commit + push to main.
Send the user a one-line summary with SendUserMessage and attach the mp4 with SendUserFile.
If any step failed after retries, say exactly which step and why.
