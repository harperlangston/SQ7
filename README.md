# Space Quest 7: The Smell of Fear

A text parser adventure game written in Python, in the spirit of Sierra
On-Line's classic *Space Quest* series. You play as Roger Wilco, Janitor
First Class and accidental hero of the galaxy, who wakes up face-down in a
pile of garbage and must save the day — again, and against his better
judgment.

---

## Table of Contents

1. [Requirements](#requirements)
2. [Installation](#installation)
3. [Running the Game](#running-the-game)
4. [Sound](#sound)
5. [The Story](#the-story)
6. [Your Mission](#your-mission)
7. [The World](#the-world)
8. [Characters](#characters)
9. [Items](#items)
10. [Commands Reference](#commands-reference)
11. [Scoring](#scoring)
12. [Saving and Restoring](#saving-and-restoring)
13. [Tips and Hints](#tips-and-hints)
14. [Features](#features)
15. [File Overview](#file-overview)

---

## Requirements

- **Python 3.8 or higher**
- **pygame 2.x** — required for chiptune sound (optional; game runs silently without it)
- **pyfiglet** — used only at development time to generate the title screen font art; not needed to run the game

The game has no other external dependencies. All audio is synthesized
programmatically — no `.wav`, `.mp3`, or `.mid` files are needed.

---

## Installation

### 1. Clone or copy the game files

Make sure the following three files are in the same directory:

```
game.py          -- main game engine
sq7_sound.py     -- chiptune sound engine
ascii_art.py     -- ASCII art for rooms, characters, and the title screen
```

### 2. Install pygame (for sound)

```bash
pip install pygame
```

If you skip this step the game will still run — it just won't have music or
sound effects. You will see no error messages; sound degrades silently.

### 3. Verify Python version

```bash
python3 --version
# Should print Python 3.8.x or higher
```

---

## Running the Game

```bash
python3 game.py
```

That's it. No arguments, no configuration files, no setup step.

The game runs entirely in your terminal. A wide terminal (at least 80
columns) is recommended for the ASCII art and map to display correctly.

---

## Sound

Sound is handled by `sq7_sound.py`, which synthesizes all audio from raw
waveform mathematics using `pygame.mixer`. There are no external audio
files — every note, chord, and sound effect is generated in real time when
the game starts.

### What you hear

**Background music** — each of the 13 rooms has a unique looping chiptune
track that plays while you explore. Music crossfades when you move between
rooms.

| Room | Style |
|------|-------|
| Junk Pile | Slow C minor, dismal and comedic |
| Engine Room | Rhythmic E minor staccato, industrial |
| Engine Room Catwalk | Tense E minor, thin and high |
| Airlock Corridor | Eerie A minor, sparse and ambient |
| Escape Pod Bay | Rising C major arpeggios, anticipation |
| Escape Pod (Landed) | Hopeful G major, new world |
| Monolith Burger Exterior | Upbeat F major jingle, cheesy fast-food |
| Monolith Burger Counter | Bustling F major with sawtooth bass |
| Monolith Burger Kitchen | Dark D minor, hot and dangerous |
| Incinerator Chamber | Fast chromatic descent at 160 BPM, urgent |
| CEO Hallway | Slow Bb minor, corporate menace |
| CEO Office | Bold Bb minor, confrontational |
| Holding Cell | Quiet C minor, melancholy with hope |

**Sound effects** — triggered by game events:

| Event | Sound |
|-------|-------|
| Death | Descending chromatic run + noise burst |
| Victory | Ascending major fanfare + chord |
| Picking up an item | Quick two-note ascending ping |
| Earning score points | Three ascending notes |
| Entering the incinerator | Door slam |
| Incinerator countdown (5 turns left) | Two warning beeps |
| Incinerator critical (2 turns left) | Rapid beeping |
| CEO ejection | Descending whoosh |
| Pod launch | Rising sine sweep + rocket noise |
| Intercom message | Two-note chime before announcement |
| Pressing the button | Square wave blip |
| Electric shock (3rd button press) | Tremolo noise burst |
| Unlocking the holding cell | Two metallic clicks |

### Sound troubleshooting

**No sound at all** — install pygame:
```bash
pip install pygame
```

**pygame installed but still no sound** — your system may lack an audio
device or ALSA/PulseAudio may not be configured. The game will detect this
and fall back to silent mode automatically. You can verify:
```bash
python3 -c "import pygame; pygame.mixer.init(); print(pygame.mixer.get_init())"
```
If this prints `None` or raises an error, your audio system needs
configuration outside the game.

**MIDI not working** — the game does *not* use MIDI files. All audio is
synthesized PCM. You do not need timidity, fluidsynth, or any MIDI
synthesizer.

---

## The Story

You are **Roger Wilco**, Janitor First Class, Hero of the Galaxy (three
times over, not that anyone remembers), and chronic underachiever. You wake
up face-down in a mountain of interstellar garbage aboard a derelict
freighter. The smell is indescribable.

Somewhere in your lunch box is a crumpled receipt. It mentions a flux
capacitor — removed for cleaning and stored in the incinerator room of
Monolith Burger Location 7. You need that flux capacitor. You're not sure
why yet, but the universe has a way of making these things clear.

Meanwhile, the Two Guys from Andromeda — **Mark Crowe** and **Scott
Murphy**, the legendary game designers who created the Space Quest series —
are being held prisoner by **CEO Nigel Rancid** in his executive suite.
They need rescuing. They also need that flux capacitor, as it turns out.

The universe is, as usual, entirely indifferent to your prior
contributions.

---

## Your Mission

There are three objectives, in rough order:

### 1. Escape the Garbage Freighter

The freighter is falling apart. You need to:
- Fix a burst steam pipe blocking the ladder to the catwalk
- Clean up an oil slick at the base of that same ladder
- Pry open a jammed locker on the catwalk to find an access card
- Power up the escape pod with a fuel cell
- Launch the pod to Monolith Burger

### 2. Retrieve the Flux Capacitor

Monolith Burger Location 7 has an incinerator. The flux capacitor is in it.
You need to:
- Get hired as a Monolith Burger employee (fill out the application form)
- Enter the incinerator chamber before it activates — or survive if it does
- Use the grease trap override key to escape the incinerator with the capacitor

**Warning:** Once you enter the incinerator, you have 8 turns to get out.
The game auto-saves before you enter.

### 3. Rescue the Two Guys and Escape

CEO Nigel Rancid has Mark Crowe and Scott Murphy locked in a holding cell.
You need to:
- Distract the CEO (he has a weakness for Monolith Burger food)
- Get the holding cell key from his desk
- Free the Two Guys
- Return to the escape pod with the flux capacitor and the Two Guys
- Install the flux capacitor and launch

---

## The World

The game has 13 rooms across two regions.

### Garbage Freighter

```
  AIRLOCK ---- JUNK PILE ---- ENGINE RM
    |                              |
  POD BAY  ----  (blank)  ----  CATWALK
    |
  POD LANDED
```

| Room | Description |
|------|-------------|
| **Junk Pile** | Starting location. Garbage everywhere. Your mop is here. |
| **Engine Room** | Machinery that should have been serviced decades ago. Steam pipe, oil slick, wrench, fuel cell. |
| **Engine Room Catwalk** | High above the engine room. Jammed locker, mysterious button. |
| **Airlock Corridor** | Connects junk pile to pod bay. Eerie and empty. |
| **Escape Pod Bay** | The way out. Card reader requires an access card. |
| **Escape Pod (Landed)** | After launch, your pod sits outside Monolith Burger. |

### Monolith Burger

```
  MB EXTERIOR
       |
  MB COUNTER ---- MB KITCHEN ---- INCINERATR
                       |
               CEO HALLWY ---- CEO OFFICE ---- HOLD. CELL
```

| Room | Description |
|------|-------------|
| **Monolith Burger Exterior** | The parking lot. Your crashed pod is here. |
| **Monolith Burger Counter** | Order counter. Cashier, Fester Blatz, menu, application form. |
| **Monolith Burger Kitchen** | Hot, greasy, dangerous. Manager, spatula, grease trap key. |
| **Incinerator Chamber** | Timed death trap. The flux capacitor is in here. 8 turns to escape. |
| **CEO Hallway** | Ominous corridor leading to the executive suite. |
| **CEO Office** | CEO Nigel Rancid's domain. Very nice desk. Do not go north without a plan. |
| **Holding Cell** | Mark Crowe and Scott Murphy are imprisoned here. |

---

## Characters

| Character | Location | Notes |
|-----------|----------|-------|
| **Roger Wilco** | Everywhere | You. Janitor. Hero. Garbage-scented. |
| **Cashier** | MB Counter | Underpaid, suspicious. Will sell you a Monolith Meal for 10 Buckazoids. |
| **Fester Blatz** | MB Counter | Regular customer. Knows things about the Two Guys. Talk to him. |
| **Manager** | MB Kitchen | Runs the kitchen. Will hire you if you give him the application form. |
| **CEO Nigel Rancid** | CEO Office | The villain. Has a very nice desk. Will physically eject you if you try to go north without distracting him first. |
| **Mark Crowe** | Holding Cell / Pod | One of the Two Guys from Andromeda. Optimistic. Knows how to install flux capacitors. |
| **Scott Murphy** | Holding Cell / Pod | The other Guy from Andromeda. Less optimistic. More practical. |

---

## Items

| Item | Found In | Used For |
|------|----------|----------|
| **Mop** | Junk Pile | Cleaning the oil slick in the engine room |
| **Lunch Box** | Junk Pile | Contains a receipt (examine it) and a burger; used to distract the CEO |
| **Scrap Metal** | Junk Pile | Prying open the jammed locker on the catwalk |
| **Credits (Buckazoids)** | Junk Pile | Buying a Monolith Meal from the cashier |
| **Wrench** | Engine Room | Fixing the burst steam pipe |
| **Fuel Cell** | Engine Room | Powering up the escape pod's nav computer |
| **Oil Slick** | Engine Room | Obstacle — clean it with the mop |
| **Locker** | Catwalk | Contains the access card (pry open with scrap metal) |
| **Button** | Catwalk | Labeled "DO NOT PRESS." Three progressive responses. |
| **Escape Pod** | Pod Bay | Your transport — needs access card + fuel cell |
| **Menu** | MB Counter | Readable for flavor |
| **Application Form** | MB Counter | Give to the manager to get hired |
| **Spatula** | MB Kitchen | Jamming the CEO hallway door latch |
| **Grease Trap Key** | MB Kitchen | Overriding the incinerator lock |
| **Access Card** | Catwalk Locker | Launching the escape pod |
| **Flux Capacitor** | Incinerator | The MacGuffin. Retrieve it and bring it to the pod. |
| **Holding Cell Key** | CEO's Desk | Unlocking the holding cell |
| **Monolith Meal** | MB Counter (buy) | Alternative to the lunch box for distracting the CEO |

---

## Commands Reference

Commands are not case-sensitive. Most accept natural variations
(`take mop`, `pick up mop`, `get mop` all work).

### Movement

| Command | Description |
|---------|-------------|
| `go north` / `n` | Move north |
| `go south` / `s` | Move south |
| `go east` / `e` | Move east |
| `go west` / `w` | Move west |
| `go up` / `u` | Move up |
| `go down` / `d` | Move down |
| `enter pod` | Enter the escape pod (in Pod Bay or Pod Landed) |

You can also type just the direction: `north`, `n`, `south`, `s`, etc.

### Looking Around

| Command | Description |
|---------|-------------|
| `look` / `l` | Describe the current room |
| `look at [thing]` | Look at an item or NPC in the room |
| `examine [thing]` / `x [thing]` | Examine something in detail (more info than `look at`) |

### Inventory

| Command | Description |
|---------|-------------|
| `inventory` / `inv` / `i` | List everything you're carrying |
| `take [item]` / `get [item]` / `pick up [item]` | Pick up an item |
| `drop [item]` | Drop an item in the current room |

### Interaction

| Command | Description |
|---------|-------------|
| `use [item]` | Use an item (context-sensitive) |
| `use [item] on [target]` | Use an item on a specific target |
| `give [item] to [person]` / `hand [item] to [person]` | Give an item to an NPC |
| `talk to [person]` / `speak to [person]` | Talk to an NPC (cycles through dialogue) |
| `buy [item]` | Buy something from a vendor |
| `press [thing]` | Press a button or switch |

### Display

| Command | Description |
|---------|-------------|
| `verbose` | Always show full room descriptions (default) |
| `brief` | Show only room name and exits on revisited rooms |
| `ascii_on` / `ascii` | Enable ASCII art illustrations when entering rooms |
| `ascii_off` | Disable ASCII art illustrations |
| `ascii_show` | Show ASCII art for the current room without re-entering |
| `map` | Display an ASCII map of all explored rooms |

### Game Management

| Command | Description |
|---------|-------------|
| `score` | Show your current score out of 120 |
| `hint` | Get a context-sensitive hint for what to do next |
| `save [slot]` | Save the game to a numbered slot (default: 1) |
| `restore [slot]` | Restore a saved game from a numbered slot |
| `again` / `g` | Repeat the last command |
| `help` / `?` | Show the in-game command reference |
| `quit` / `q` / `exit` | Quit the game |

### Shorthand

Many commands have short forms:

```
l       = look
x       = examine
i       = inventory
n/s/e/w = go north/south/east/west
u/d     = go up/down
g       = again (repeat last command)
```

---

## Scoring

The maximum score is **120 points**. Points are awarded for meaningful
progress — solving puzzles, reaching new areas, and completing objectives.

| Action | Points |
|--------|--------|
| Fix the steam pipe (use wrench) | 5 |
| Clean the oil slick (use mop) | 5 |
| Pry open the locker (use scrap metal) | 5 |
| Pick up the Access Card | 5 |
| Insert the fuel cell into the pod | 5 |
| Pick up the Grease Trap Key | 5 |
| Jam the CEO hallway door (use spatula) | 5 |
| Buy a Monolith Meal from the cashier | 5 |
| Press the DO NOT PRESS button (first time) | 2 |
| Press the button a third time (electric shock) | −1 |
| Escape the incinerator with the flux capacitor | 10 |
| Pick up the Flux Capacitor | 15 |
| Launch the escape pod from the freighter | 15 |
| Get hired at Monolith Burger | 10 |
| Distract the CEO | 10 |
| Pick up the Holding Cell Key | 10 |
| Free the Two Guys from Andromeda | 15 |
| Install the flux capacitor and escape | 20 |

---

## Saving and Restoring

### Manual saves

```
save        -- saves to slot 1 (file: sq7_save_1.dat)
save 2      -- saves to slot 2 (file: sq7_save_2.dat)
restore     -- restores from slot 1
restore 2   -- restores from slot 2
```

Save files are written to the current working directory as
`sq7_save_<slot>.dat`. You can have as many slots as you like.

### Autosave

The game automatically saves to `sq7_autosave.dat` immediately before you
enter the incinerator chamber. If you die in the incinerator, you will be
offered the option to restore this autosave at the Game Over screen.

### Game Over

When you die, you are presented with options:

- **Restore Autosave (a)** — only shown if `sq7_autosave.dat` exists
- **Restart (r)** — start a fresh game from the beginning
- **Quit (q)** — exit the program

---

## Tips and Hints

The game has a built-in hint system. Type `hint` at any time for a
context-sensitive nudge based on your current room and inventory.

### General tips

- **Examine everything.** `examine` gives more detail than `look at`. Many
  items have hidden information only revealed by examining them closely.
  The lunch box, for example, contains a receipt with a critical clue.

- **Talk to everyone, more than once.** NPCs cycle through multiple lines
  of dialogue. Fester Blatz in particular has information you need.

- **Read the room descriptions carefully.** Exits, items, and interactive
  objects are always mentioned in the description.

- **The `map` command** shows which rooms you've visited and how they
  connect. Use it if you get disoriented.

- **You can't carry everything.** The game is designed so you only need
  what's relevant. If you're stuck, think about what you're holding and
  what the current obstacle is.

- **The incinerator is timed.** You have exactly 8 turns once you enter.
  Make sure you have the grease trap key *before* going in. The game
  auto-saves before entry so you can always restore if you get trapped.

- **The CEO will throw you out.** The first time you try to go north in
  the CEO Office without distracting him, he physically ejects you back
  to the escape pod. The second time, he uses a trapdoor. Distract him
  first.

- **Brief mode** (`brief`) is useful once you know the rooms. It shows
  only the room name and exits on revisits instead of the full description.

### Stuck? Step-by-step walkthrough outline

1. In the **Junk Pile**: take the mop, lunch box, scrap metal, and credits.
   Examine the lunch box.
2. Go east to the **Engine Room**: take the wrench and fuel cell.
   Use the wrench on the steam pipe. Use the mop on the oil slick.
3. Go up to the **Catwalk**: use the scrap metal on the locker. Take the
   access card. (Feel free to press the button.)
4. Go east to the **Pod Bay**: use the fuel cell on the pod.
   Use the access card on the pod (or type `enter pod`) to launch.
5. At **Monolith Burger Exterior**: go north to the counter.
6. At the **Counter**: take the application form. Talk to Fester Blatz.
7. Go east to the **Kitchen**: give the application form to the manager.
   Take the spatula and the grease trap key.
8. Go north to the **Incinerator**: use the grease trap key on the control
   panel. Take the flux capacitor. Go south.
9. Go east to the **CEO Hallway**: use the spatula on the door latch.
10. Go east to the **CEO Office**: use the lunch box (or Monolith Meal) to
    distract the CEO. Take the holding cell key from the desk.
11. Go north to the **Holding Cell**: use the holding cell key on the door.
12. Return south through the CEO Office and hallway, west through the
    kitchen and counter, south to the exterior, and south to the pod.
13. At the **Pod (Landed)**: use the flux capacitor. The Two Guys install
    it. Launch and win.

---

## Features

The game includes a number of quality-of-life and flavor features:

| Feature | Description |
|---------|-------------|
| **again / g** | Repeats the last command — useful for `talk` to cycle NPC dialogue |
| **Brief/verbose mode** | Toggle between full descriptions and short summaries on revisited rooms |
| **Detailed examine** | `examine` reveals more information than `look at` for most items |
| **Auto-save** | Silently saves before the incinerator so you can always recover from death |
| **Wrong-item responses** | Using the wrong item in the wrong place gives a snarky, context-specific response instead of a generic error |
| **Bribeable cashier** | You can buy a Monolith Meal as an alternative to the lunch box for distracting the CEO |
| **DO NOT PRESS button** | The catwalk button has four progressive responses depending on how many times you press it |
| **NPC personalities** | Each NPC has multiple lines of dialogue that cycle as you talk to them |
| **Intercom messages** | Periodic announcements play over the ship/restaurant intercom as you explore |
| **CEO confrontation** | The CEO has two different ejection sequences depending on whether he's thrown you out before |
| **Chiptune sound** | 13 room music tracks and 13 sound effects, all synthesized in real time |
| **ASCII art** | Room illustrations and character portraits displayed on entry (toggle with `ascii_on`/`ascii_off`) |
| **Navigation map** | `map` command shows a live ASCII map of explored rooms with your current location |
| **Context hints** | `hint` gives a nudge tailored to your current room and inventory |
| **Multiple save slots** | Save and restore from numbered slots; autosave before dangerous situations |
| **Title screen** | Full ASCII art opening screen with station diagram, Roger's portrait, cast list, and mission briefing |

---

## File Overview

| File | Purpose |
|------|---------|
| `game.py` | Main game engine: parser, rooms, items, NPCs, all game logic |
| `sq7_sound.py` | Chiptune sound engine: waveform synthesis, room music, sound effects |
| `ascii_art.py` | ASCII art: room illustrations, character portraits, title screen |
| `sq7_save_<n>.dat` | Manual save files (created when you use the `save` command) |
| `sq7_autosave.dat` | Autosave file (created automatically before the incinerator) |

All save files are Python `pickle` format and are written to the directory
you run the game from.

---

## Credits

*Space Quest 7: The Smell of Fear* is a fan-made tribute to Sierra On-Line's
*Space Quest* series, created by Ken Williams and originally designed by
Mark Crowe and Scott Murphy (the Two Guys from Andromeda). This game is not
affiliated with or endorsed by Activision, Sierra, or any rights holders.

Roger Wilco, Space Quest, and all related characters and concepts are
trademarks of their respective owners.

The Two Guys from Andromeda are real people who really did make Space Quest.
They are not actually imprisoned by a fast-food CEO. As far as we know.
