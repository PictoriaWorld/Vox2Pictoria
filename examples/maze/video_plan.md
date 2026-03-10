# Maze Video Plan

Indie dev vibes, not an ad.

## Target Platforms

| Platform | Format | Resolution | Length | Notes |
|----------|--------|------------|--------|-------|
| Instagram Reels | Vertical 9:16 video, MP4 | 1080x1920 | 20-25s | Text safe zone: avoid top/bottom 250px (covered by Instagram UI). |
| TikTok | Vertical 9:16 video, MP4 | 1080x1920 | 20-25s | Same video as Instagram. Algorithm favors 21-34s. |
| YouTube Shorts | Vertical 9:16 video, MP4 | 1080x1920 | 20-25s | Same video as Instagram. Max 60s. |
| X (Twitter) | Vertical 9:16 video, MP4 | 1080x1920 | 20-25s | Same video as Instagram. |
| Reddit r/isometric | Landscape 16:9 video, MP4 | 3840x2160 or 1920x1080 | 20-25s | Same content, re-edited for landscape framing. |

Vertical platforms get the same video file. Reddit gets a landscape edit of the same content.

## Shot List

| # | Text | Video | Duration | Notes |
|---|------|-------|-------|-------|
| 1 | What if you could build a multiplayer world using just 2D images? | 2 players moving through the maze in Pictoria | 3s | N/A |
| 2 | I'm building Pictoria, a social MMO that lets you do just that | Transition to wireframe mode, with just a few maze structures on the screen. Player is creating a structure, dragging image into Pictoria and dragging structure into place. | 3s | N/A |
| 3 | N/A | Timelapse of structures appearing 1-by-1 | 5s | Take a screenshot after each structure upload, stitch into video. See capture notes below. |
| 4 | N/A | Exit create structure mode | 1s | Time with music drop. |
| 5 | N/A | Walking through the maze | 2s | Show how the player can move under and over structures. |
| 6 | N/A | Another player shows up | 2s | Show simple interaction between players (chat bubbles). Show how the player can move under and over structures. |
| 7 | Pictoria.World. Closed pre-alpha is live. Keys in the Discord (link in bio) | Pictoria logo above "Pictoria.World" text. Zoom out to wide shot of the full maze | 3s | N/A |
| 8 | N/A | Zoom in to where shot 1 starts from | 0.5s | N/A |

## Timelapse Capture (Shot 4)

- Upload structures to the property one at a time
- After each upload, take a screenshot (no mouse cursor, no UI overlays)
- Stitch screenshots into video in editing at ~10-12 fps
- Experiment with speed — faster = more satisfying, but the structures need to be visible long enough to register

## Capture Settings

- **OBS**: Full display capture at 3840x2160, 60fps
- **DPR**: 100%
- **All cropping/reframing done in post** — crop, pan, and scale each shot to 1080x1920 from the 4K source
- **Timelapse screenshots**: Hide all UI and mouse cursor. Consistent zoom level and camera position across all frames.

## General Notes

- Text overlays only, no voiceover.
- Music: lo-fi or ambient. Nothing epic/trailer-y.
- Engagement bait is built in — people will comment asking how it works, arguing about "2D", etc. Don't over-explain in the video. Let the comments do the work.
- Multiplayer moment (shot 7): coordinate with another player beforehand, but make it look casual.

## Caption (Instagram / TikTok / Shorts / X)

I'm building Pictoria, a social MMO where you can upload 2D images to create explorable worlds.

I know quality 2D images aren't easy to create though - and I'm not much of an artist - so I created an open source tool that converts MagicaVoxel scenes into 2D images for Pictoria. This library maze was made entirely that way.

I'm preparing Pictoria for open alpha - feel free to join the Discord for early access (link in bio).

## Reddit Post (r/isometric)

**Title**: I procedurally generated a library maze and imported it into my MMO

**Video**: Landscape 16:9 edit of the same shot list. The 4K source footage gives room to frame wider than the vertical crop.

**Comment**: Longer version of the caption — explain the Python generation script, MagicaVoxel, Vox2Pictoria pipeline, link to GitHub repo. Reddit loves process details.
