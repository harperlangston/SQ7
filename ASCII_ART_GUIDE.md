# ASCII Art Integration Guide

## Overview
ASCII art has been integrated into Space Quest 7 for all rooms and characters. The art displays automatically when entering rooms and can be controlled with simple commands.

## Features

### Automatic Display
- ASCII art displays automatically when you enter a room
- Each room has unique, creative visual representation
- ASCII art is enabled by default

### Commands

#### `ascii_on`
Enables ASCII art display. Rooms will show visual art when you enter them.
```
> ascii_on
ASCII art enabled. You will now see visual art when entering rooms.
```

#### `ascii_off`
Disables ASCII art display. Rooms will show only text descriptions.
```
> ascii_off
ASCII art disabled. Rooms will display without visual art.
```

#### `ascii_show`
Displays the ASCII art for the current room (useful if you disabled it and want to see it again).
```
> ascii_show
[Shows the ASCII art for your current location]
```

## Available Rooms with ASCII Art

1. **Junk Pile** - Garbage mountain with debris
2. **Engine Room** - Massive spinning engines
3. **Engine Room Catwalk** - Narrow walkway over the abyss
4. **Airlock Corridor** - Pressurized corridor with sealed doors
5. **Escape Pod Bay** - Multiple escape pods
6. **Escape Pod (Landed)** - Your ticket to freedom
7. **Monolith Burger - Exterior** - Fast-food establishment
8. **Monolith Burger - Counter** - Service area with cashier
9. **Monolith Burger - Kitchen** - Industrial cooking nightmare
10. **Incinerator Chamber** - Raging inferno of doom
11. **CEO Hallway** - Corporate evil corridor
12. **CEO Office** - Nigel Rancid's domain
13. **Holding Cell** - Prison for the Two Guys

## Available Characters with ASCII Art

1. **Roger Wilco** - The protagonist janitor
2. **Cashier** - Tired fast-food worker
3. **Fester Blatz** - Disgusting blob customer
4. **Manager** - Tyrannical with ridiculous hat
5. **CEO Nigel Rancid** - Evil corporate overlord
6. **Mark Crowe** - Tall guy from Andromeda
7. **Scott Murphy** - Short guy from Andromeda

## Technical Details

### Files
- `ascii_art.py` - Contains all ASCII art definitions and helper functions
- `game.py` - Modified to integrate ASCII art display

### How It Works
1. When you enter a room, the game checks if ASCII art is enabled
2. If enabled, it retrieves the ASCII art for that room from `ascii_art.py`
3. The art is displayed before the text description
4. You can toggle this on/off at any time with the commands above

### Customization
To modify or add ASCII art:
1. Edit `ascii_art.py`
2. Add or modify art strings in the appropriate section
3. Update the `ROOM_ART` or `CHARACTER_ART` dictionaries
4. The changes will take effect immediately

## Tips
- Use `ascii_off` if you prefer a cleaner, text-only experience
- Use `ascii_show` to redisplay art for the current room
- The art is designed to fit standard terminal widths (60-70 characters)
- All art uses Unicode box-drawing characters for best appearance
