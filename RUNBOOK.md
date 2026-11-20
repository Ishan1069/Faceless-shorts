# Daily faceless-shorts run

Goal: publish one new original scary-story short per day to Instagram Reels + YouTube Shorts
(+ TikTok once it is connected in Metricool). Fully unattended: never stop to ask questions.

## 1. Get the repo
If `/home/claude/faceless-shorts` is not present, call `add_repo` (owner `Ishan1069`, repo
`faceless-shorts`, access `push`) and clone it there. `cd` into it. Run `bash setup.sh`.

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
