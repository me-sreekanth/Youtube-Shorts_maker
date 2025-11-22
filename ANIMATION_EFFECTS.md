# Animation Effects Guide

This guide explains the engaging animations/effects available for your YouTube Shorts videos.

## 🎬 Auto-Applied Animations

**All scenes automatically get engaging animations!** The system cycles through 18 different effects to ensure maximum variety and engagement. You can also manually specify effects if desired.

## Available Effects (18 Total)

### 🔍 Zoom Effects (6)
- **`zoom_in`** - Smooth zoom in (perfect for hooks)
- **`zoom_out`** - Smooth zoom out from center
- **`ken_burns_in`** - Classic Ken Burns zoom in
- **`ken_burns_out`** - Classic Ken Burns zoom out
- **`zoom_center`** - Dynamic pulsing zoom (oscillating)
- **`zoom_rapid`** - Fast, dramatic zoom in

### 📹 Pan Effects (4)
- **`pan_left`** - Pan camera left (reveal effect)
- **`pan_right`** - Pan camera right
- **`pan_up`** - Pan camera upward
- **`pan_down`** - Pan camera downward

### ✨ Parallax Effects (2)
- **`parallax_up`** - Smooth upward parallax movement
- **`parallax_down`** - Smooth downward parallax movement

### 🌊 Drift/Float Effects (3)
- **`drift_left`** - Gentle leftward drift (subtle movement)
- **`drift_right`** - Gentle rightward drift
- **`float_up`** - Floating upward motion

### 💓 Pulse Effects (2)
- **`pulse`** - Breathing/pulsing effect
- **`breathe`** - Subtle breathing animation

### 📐 Diagonal Effects (2)
- **`diagonal_tl_br`** - Diagonal movement (top-left to bottom-right)
- **`diagonal_tr_bl`** - Diagonal movement (top-right to bottom-left)

## Usage

### Automatic (Recommended)
Just create your scenes normally - animations are automatically applied:

```json
{
  "scene_number": 1,
  "narration": "What if your entire life was just a simulation?",
  "subtitle": "What if your life was a simulation?",
  "image_prompt": "digital matrix code raining down...",
  "duration": 4
}
```

### Manual Override
Specify a custom effect for any scene:

```json
{
  "scene_number": 1,
  "narration": "...",
  "duration": 4,
  "effect": "zoom_rapid"
}
```

## 🎯 Best Practices for Shorts

- **Hook scenes**: Use `zoom_rapid`, `zoom_in`, or `ken_burns_in` for immediate impact
- **Action scenes**: Use `pan_left`, `pan_right`, or `diagonal_tl_br` for dynamic movement
- **Emotional scenes**: Use `pulse`, `breathe`, or `float_up` for subtle engagement
- **Reveal scenes**: Use `parallax_up` or `parallax_down` for smooth reveals
- **Final scenes**: Use `zoom_out` or `ken_burns_out` for dramatic conclusions

## 💡 Pro Tips

- The system automatically cycles through all 18 effects for maximum variety
- Mix zoom, pan, and drift effects for the most engaging shorts
- Vertical format (9:16) is optimized for all effects
- All animations are smooth and professional-grade

