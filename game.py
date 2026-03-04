#!/usr/bin/env python3
"""
Space Quest 7: The Smell of Fear
A text parser adventure game in the spirit of Sierra's Space Quest series.

GOAL: Retrieve the flux capacitor from Monolith Burger's incinerator,
      rescue the Two Guys from Andromeda from the CEO's clutches,
      and escape the planet before anyone notices you were here.
"""

import sys
import textwrap
import time
import pickle
import os
import random

try:
    from ascii_art import get_room_art, get_character_art, print_title_screen
    _ASCII_ART_AVAILABLE = True
except ImportError:
    _ASCII_ART_AVAILABLE = False

try:
    from sq7_sound import SoundEngine
    _SOUND_AVAILABLE = True
except ImportError:
    _SOUND_AVAILABLE = False

_sound_engine = None  # module-level ref for die()/win()

# ---------------------------------------------------------------------------
# Utility
# ---------------------------------------------------------------------------

WRAP = 72

def say(text, pause=False):
    print()
    for line in text.strip().split("\n"):
        if line.strip() == "":
            print()
        else:
            print(textwrap.fill(line.strip(), WRAP))
    if pause:
        time.sleep(0.5)

AUTOSAVE_FILE = "sq7_autosave.dat"

def die(message):
    if _sound_engine:
        _sound_engine.play_sfx('death')
    say(message)
    say(
        "You are dead. As in, no longer among the living. Deceased. "
        "Departed. Pushing up space daisies. Roger Wilco, Janitor First "
        "Class, has once again demonstrated that the universe is better "
        "off without him. Congratulations."
    )
    print()
    has_autosave = os.path.exists(AUTOSAVE_FILE)
    if has_autosave:
        choice = input("GAME OVER  --  Restore Autosave, Restart, or Quit? (a/r/q): ").strip().lower()
    else:
        choice = input("GAME OVER  --  Restart or Quit? (r/q): ").strip().lower()
    if choice == "a" and has_autosave:
        game = Game()
        try:
            with open(AUTOSAVE_FILE, "rb") as f:
                state = pickle.load(f)
            game._restore_state(state)
            say("Autosave restored. Try not to die this time.")
            game.player.room.describe(game=game)
            game.run()
        except Exception as e:
            say(f"Autosave restore failed: {e}. Starting fresh.")
            main()
    elif choice == "r":
        main()
    else:
        sys.exit(0)

def win(message):
    if _sound_engine:
        _sound_engine.stop_music()
        _sound_engine.play_sfx('victory')
    say(message)
    say(
        "Against all odds, Roger Wilco has survived. Mark Crowe and "
        "Scott Murphy — the Two Guys from Andromeda — are free. The "
        "galaxy breathes a collective sigh of relief, mostly because "
        "Roger is no longer near any of its air supplies. Well done, "
        "you magnificent slacker."
    )
    sys.exit(0)


# ---------------------------------------------------------------------------
# Item
# ---------------------------------------------------------------------------

class Item:
    def __init__(self, name, aliases, description, takeable=True, examine_description=None):
        self.name = name
        self.aliases = aliases
        self.description = description
        self.takeable = takeable
        self.examine_description = examine_description

    def matches(self, word):
        return word in self.aliases or word == self.name.lower()


# ---------------------------------------------------------------------------
# NPC
# ---------------------------------------------------------------------------

class NPC:
    def __init__(self, name, aliases, lines):
        self.name = name
        self.aliases = aliases
        self.lines = lines
        self._index = 0

    def matches(self, word):
        return word in self.aliases or word == self.name.lower()

    def talk(self):
        line = self.lines[self._index % len(self.lines)]
        self._index += 1
        say(f'{self.name} says: "{line}"')


# ---------------------------------------------------------------------------
# Room
# ---------------------------------------------------------------------------

class Room:
    def __init__(self, name, description, exits=None, items=None, npcs=None):
        self.name = name
        self.description = description      # string or callable
        self.exits = exits or {}
        self.items = items or []
        self.npcs = npcs or []
        self.on_enter = None                # callable, called when player enters
        self.on_tick = None                 # callable, called each turn while here
        self.visited = False                # Feature 2: brief/verbose

    def describe(self, brief=False, game=None):
        say(self.name.upper())
        # Show ASCII art if enabled
        if game and game._show_ascii_art and _ASCII_ART_AVAILABLE:
            art = get_room_art(self.name)
            if art:
                print(art)
        if not brief:
            desc = self.description() if callable(self.description) else self.description
            say(desc)
            if self.items:
                say("You can see: " + ", ".join(i.name for i in self.items) + ".")
            if self.npcs:
                say("Also here: " + ", ".join(n.name for n in self.npcs) + ".")
        if self.exits:
            say("Exits: " + ", ".join(self.exits.keys()) + ".")

    def get_item(self, word):
        for item in self.items:
            if item.matches(word):
                return item
        return None

    def get_npc(self, word):
        for npc in self.npcs:
            if npc.matches(word):
                return npc
        return None


# ---------------------------------------------------------------------------
# Player
# ---------------------------------------------------------------------------

class Player:
    def __init__(self, start_room):
        self.room = start_room
        self.inventory = []
        self.score = 0
        self.flags = {}

    def has(self, item_name):
        return any(i.name.lower() == item_name.lower() for i in self.inventory)

    def get_inv_item(self, word):
        for item in self.inventory:
            if item.matches(word):
                return item
        return None

    def take(self, item):
        self.inventory.append(item)

    def drop_item(self, item):
        self.inventory = [i for i in self.inventory if i is not item]


# ---------------------------------------------------------------------------
# Parser
# ---------------------------------------------------------------------------

DIRECTIONS = {
    "north": "north", "n": "north",
    "south": "south", "s": "south",
    "east":  "east",  "e": "east",
    "west":  "west",  "w": "west",
    "up":    "up",    "u": "up",
    "down":  "down",  "d": "down",
    "out":   "out",
}

STOP_WORDS = {"the", "a", "an", "at", "with", "to", "into", "from", "of"}

def tokenize(raw):
    words = raw.lower().split()
    return [w for w in words if w not in STOP_WORDS]


# ---------------------------------------------------------------------------
# Feature 9: Intercom messages
# ---------------------------------------------------------------------------

FREIGHTER_INTERCOM = [
    "[INTERCOM] 'Attention crew: the recycling unit is now recycling itself. "
    "Please do not interfere with the process.'",
    "[INTERCOM] 'Reminder: unauthorized use of escape pods will result in "
    "termination. Of employment. And also of you.'",
    "[INTERCOM] 'The cafeteria is now closed. It has been closed for six years. "
    "Please stop asking.'",
    "[INTERCOM] 'Will the owner of a blue 1987 Astro-Wagon please report to "
    "the airlock? Your vehicle is being towed. Into space.'",
    "[INTERCOM] 'Safety tip: do not lick the engine coolant. We should not "
    "have to say this twice.'",
    "[INTERCOM] 'Today's motivational message: You are replaceable. "
    "Have a productive shift.'",
    "[INTERCOM] 'Lost and found update: one mop, one dignity, and three "
    "unidentified life forms. Claim at your own risk.'",
    "[INTERCOM] 'The artificial gravity will be offline for maintenance in "
    "approximately never. Budget cuts.'",
    "[INTERCOM] 'Crew morale survey results are in: morale remains "
    "theoretical.'",
    "[INTERCOM] 'Reminder: the airlock is not a suggestion box. Please stop "
    "putting complaints in it.'",
    "[INTERCOM] 'Engineering reports that the strange noise from deck seven "
    "is nothing to worry about. Engineering has also evacuated deck seven.'",
    "[INTERCOM] 'Happy birthday to... *shuffling papers* ...nobody. "
    "Nobody has a birthday today. Carry on.'",
]

MB_INTERCOM = [
    "[INTERCOM] 'Attention Monolith Burger customers: our ice cream machine "
    "is working. Just kidding.'",
    "[INTERCOM] 'Employee reminder: the secret sauce is secret for legal "
    "reasons. Do not investigate.'",
    "[INTERCOM] 'Will the owner of a crashed escape pod in the parking lot "
    "please move it? You are blocking the drive-through.'",
    "[INTERCOM] 'Today's special: the Monolith Burger. Tomorrow's special: "
    "also the Monolith Burger. We have one item.'",
    "[INTERCOM] 'The CEO would like to remind all employees that happiness "
    "is mandatory. Smile or be reassigned.'",
    "[INTERCOM] 'Health inspector visit postponed indefinitely. The health "
    "inspector has not been seen since his last visit.'",
]

# ---------------------------------------------------------------------------
# Game
# ---------------------------------------------------------------------------

class Game:
    def __init__(self):
        self.rooms = {}
        self.player = None
        self.turn = 0
        # Feature 1: again/g
        self._last_command = ""
        # Feature 2: brief/verbose
        self._verbose = True
        # ASCII art display
        self._show_ascii_art = True
        # Feature 7: DO NOT PRESS button
        self._button_presses = 0
        # Feature 9: intercom messages
        self._intercom_index = 0
        self._next_intercom = 5
        # Feature 10: CEO ejection
        self._ejected_by_ceo = False
        self._build_world()
        # Sound engine (optional — game works without it)
        global _sound_engine
        self.sound = None
        if _SOUND_AVAILABLE:
            try:
                self.sound = SoundEngine()
                _sound_engine = self.sound
            except Exception:
                pass

    def _play_room_music(self):
        """Play background music for the current room."""
        if not self.sound:
            return
        for key, room in self.rooms.items():
            if room is self.player.room:
                self.sound.play_room_music(key)
                return

    # ------------------------------------------------------------------
    # World building
    # ------------------------------------------------------------------

    def _build_world(self):

        # ================================================================
        # GARBAGE FREIGHTER
        # ================================================================

        junk_pile = Room(
            name="Junk Pile",
            description=(
                "You wake up face-down in a mountain of interstellar garbage. "
                "The smell is indescribable, which is fortunate because the "
                "narrator refuses to try. Broken machinery, crushed food "
                "containers, and what appears to be someone's collection of "
                "Leisure Suit Larry cartridges surround you. "
                "A rusty hatch leads north. A narrow corridor goes east."
            ),
            exits={"north": "airlock_corridor", "east": "engine_room"},
            items=[
                Item("Mop", ["mop", "broom"],
                     "A trusty mop. Roger's one true companion. The bristles are "
                     "stiff with something you'd rather not identify."),
                Item("Lunch Box", ["lunch", "lunchbox", "box"],
                     "A dented lunch box. Inside: a half-eaten Monolith Burger, "
                     "still somehow warm, and a crumpled receipt. The receipt "
                     "reads: 'FLUX CAPACITOR - REMOVED FOR CLEANING - STORED IN "
                     "INCINERATOR ROOM, MONOLITH BURGER LOCATION 7.' "
                     "Someone has underlined 'INCINERATOR ROOM' three times.",
                     examine_description=(
                         "You open the lunch box and peer inside. The half-eaten "
                         "Monolith Burger is still warm — impossibly, defiantly warm, "
                         "as if it has made a personal decision to never cool down. "
                         "The smell hits you like a freight train made of grease. "
                         "Beneath the burger, a crumpled receipt reads:\n"
                         "\n"
                         "  MONOLITH BURGER LOCATION 7\n"
                         "  --------------------------\n"
                         "  1x Monolith Burger Meal ... 4.99\n"
                         "  FLUX CAPACITOR - REMOVED FOR CLEANING\n"
                         "  STORED IN: INCINERATOR ROOM\n"
                         "  ** DO NOT INCINERATE **\n"
                         "\n"
                         "Someone has underlined 'INCINERATOR ROOM' three times "
                         "and added 'SERIOUSLY' in the margin. The narrator notes "
                         "that this is the most important piece of garbage Roger "
                         "has ever found, which is saying something."
                     )),
                Item("Scrap Metal", ["scrap", "metal", "piece", "hull"],
                     "A jagged piece of hull plating. Sturdy enough to wedge "
                     "something open, or pry something loose."),
                Item("Credits", ["credits", "money", "cash", "coins", "buckazoids", "pouch"],
                     "A small pouch containing 10 Buckazoids. Not exactly a "
                     "fortune, but enough to buy something at a fast food joint."),
            ]
        )

        engine_room = Room(
            name="Engine Room",
            description=lambda: self._engine_room_desc(),
            exits={"west": "junk_pile"},
            items=[
                Item("Wrench", ["wrench", "tool", "spanner"],
                     "A heavy hydrospanner. The kind of tool that fixes things "
                     "and also breaks things, depending on your skill level. "
                     "Roger's skill level is... optimistic."),
                Item("Fuel Cell", ["fuel", "cell", "battery"],
                     "A small fuel cell, still charged. It smells like ambition "
                     "— faint and fading, but present."),
                Item("Oil Slick", ["oil", "slick", "puddle", "grease"],
                     "A spreading puddle of engine oil blocking the base of the "
                     "ladder to the catwalk. Slippery enough to be fatal.",
                     takeable=False),
            ]
        )

        catwalk = Room(
            name="Engine Room Catwalk",
            description=lambda: self._catwalk_desc(),
            exits={"down": "engine_room", "east": "escape_pod_bay"},
            items=[
                Item("Locker", ["locker", "cabinet", "box"],
                     "A metal storage locker, door jammed shut. Something "
                     "rattles inside when you shake it.",
                     takeable=False,
                     examine_description=(
                         "You press your ear against the locker door. Something "
                         "definitely rattles inside — something flat and plastic. "
                         "The door is jammed, but there's a gap between the door "
                         "and the frame, about half an inch wide. If you had "
                         "something sturdy and flat, you could lever it open."
                     )),
                Item("Button", ["button", "red", "light", "blinking"],
                     "A single blinking red button labeled 'DO NOT PRESS.' "
                     "It blinks invitingly.",
                     takeable=False,
                     examine_description=(
                         "A large, candy-red button mounted on a small pedestal. "
                         "It blinks with a slow, hypnotic rhythm. A label above it "
                         "reads 'DO NOT PRESS' in bold letters. Below that, in "
                         "smaller print: 'SERIOUSLY. DON'T.' The button practically "
                         "begs to be pressed. It's the most pressable thing you've "
                         "ever seen."
                     )),
            ]
        )

        airlock_corridor = Room(
            name="Airlock Corridor",
            description=(
                "A long corridor with flickering fluorescent lights and the "
                "distinct aroma of recycled air and broken dreams. Doors line "
                "the walls, most welded shut. One door to the east has a card "
                "reader. The junk pile is back south."
            ),
            exits={"south": "junk_pile", "east": "escape_pod_bay"},
            items=[]
        )

        escape_pod_bay = Room(
            name="Escape Pod Bay",
            description=lambda: self._escape_pod_bay_desc(),
            exits={"west": "engine_room_catwalk", "south": "airlock_corridor"},
            items=[
                Item("Escape Pod", ["pod", "escape", "ship", "vessel", "coffin"],
                     "An XJ-7 'Coffin Class' escape pod. The name is not "
                     "inspiring. A panel on the side is open — the flux "
                     "capacitor housing is empty. Without it, this thing "
                     "isn't going anywhere. A card reader on the wall "
                     "controls the launch sequence.",
                     takeable=False,
                     examine_description=(
                         "You run your hands over the XJ-7 'Coffin Class' escape pod. "
                         "The hull is dented, scorched, and covered in stickers that say "
                         "things like 'MY OTHER SHIP IS A STAR GENERATOR' and 'HONK IF "
                         "YOU'VE BEEN ABDUCTED.' The side panel hangs open, revealing "
                         "an empty flux capacitor housing — a circular slot lined with "
                         "copper contacts, all dark. Without a flux capacitor seated "
                         "in there, the temporal drive is dead. The receipt in your "
                         "lunch box mentioned one stored in an incinerator room..."
                     )),
            ]
        )
        escape_pod_bay.on_enter = self._on_enter_pod_bay

        # ================================================================
        # MONOLITH BURGER
        # ================================================================

        escape_pod_landed = Room(
            name="Escape Pod (Landed)",
            description=lambda: self._escape_pod_landed_desc(),
            exits={"north": "monolith_burger_exterior"},
            items=[]
        )
        escape_pod_landed.on_enter = self._on_enter_pod_landed

        mb_exterior = Room(
            name="Monolith Burger - Exterior",
            description=(
                "You've arrived at Monolith Burger, the galaxy's finest fast "
                "food establishment, assuming your standards are low enough. "
                "The golden arches have been replaced with a giant golden "
                "monolith. A flickering neon sign reads 'NOW HIRING.' "
                "The entrance is north. Your escape pod is parked "
                "illegally to the south."
            ),
            exits={"north": "monolith_burger_counter", "south": "escape_pod_(landed)"},
            items=[]
        )

        mb_counter = Room(
            name="Monolith Burger - Counter",
            description=(
                "The interior smells of grease, despair, and something that "
                "was once a vegetable. A bored cashier stares at you from "
                "behind the counter. A door marked 'EMPLOYEES ONLY' leads "
                "east to the kitchen. Exit is south."
            ),
            exits={"south": "monolith_burger_exterior", "east": "monolith_burger_kitchen"},
            items=[
                Item("Menu", ["menu", "sign", "board"],
                     "The menu. Item #1: Monolith Burger. Item #2: Monolith "
                     "Burger with cheese. Item #3: Monolith Burger meal. "
                     "The galaxy's most ambitious menu.",
                     takeable=False),
                Item("Application Form", ["application", "form", "paper"],
                     "A greasy job application form. It asks for your name, "
                     "species, and whether you have ever been the cause of a "
                     "planetary catastrophe. There's a checkbox for 'yes.'"),
            ],
            npcs=[
                NPC("Cashier", ["cashier", "worker", "employee"],
                    [
                        "Welcome to Monolith Burger. May I take your order, "
                        "or are you just here to stare blankly like the last guy?",
                        "If you want a job, grab the application and take it "
                        "to the manager in the kitchen.",
                        "We're not responsible for existential crises caused "
                        "by our menu.",
                        "Sir, this is a Monolith Burger.",
                    ]),
                NPC("Fester Blatz", ["customer", "disgusting", "alien", "blob", "guy", "fester", "blatz"],
                    [
                        "*slurp* Hey pal, you look like someone who needs "
                        "directions. *burp* Name's Fester. Fester Blatz. "
                        "I'm what you'd call a regular.",
                        "I heard they got the Two Guys from Andromeda locked "
                        "up in the back. CEO's office, east of the kitchen. "
                        "Poor fellas. *slurp* Say, you got any fries?",
                        "The CEO's a real piece of work. Keeps his office key "
                        "on him at all times. But I hear he can't resist the "
                        "smell of a fresh Monolith Burger. *burp* Not that "
                        "I'd know anything about that.",
                        "*slurp* You know what I think? I think the government "
                        "puts mind-control chips in the Monolith Sauce. "
                        "That's why I eat here every day. *burp* Wait...",
                        "I once ate fourteen Monolith Burgers in one sitting. "
                        "They named a biohazard protocol after me. *slurp*",
                        "*slurp* You still here? Go rescue those guys already. "
                        "I got burgers to eat and conspiracies to uncover.",
                    ]),
            ]
        )

        mb_kitchen = Room(
            name="Monolith Burger - Kitchen",
            description=lambda: self._kitchen_desc(),
            exits={"west": "monolith_burger_counter"},
            items=[
                Item("Spatula", ["spatula", "flipper"],
                     "A well-used spatula, coated in a substance that defies "
                     "chemical analysis. The handle is just thin enough to "
                     "slip into a door latch."),
                Item("Grease Trap Key", ["key", "grease", "trap", "override"],
                     "A small key labeled 'INCINERATOR OVERRIDE — DO NOT LOSE.' "
                     "It was just sitting here on the counter. "
                     "That seems like a safety violation.",
                     examine_description=(
                         "A small brass key with 'INCINERATOR OVERRIDE' stamped "
                         "into the bow. The teeth are worn but functional. On the "
                         "back, someone has scratched 'FITS NORTH WALL PANEL' in "
                         "tiny letters. The fact that this was just sitting on a "
                         "kitchen counter next to a spatula says everything you "
                         "need to know about Monolith Burger's safety standards."
                     )),
            ],
            npcs=[
                NPC("Manager", ["manager", "boss", "alien", "hat"],
                    [
                        "You want a job? Fill out the application from the "
                        "counter and hand it to me. We have an opening in "
                        "waste disposal. Naturally.",
                        "Don't touch anything in the kitchen. Especially "
                        "the incinerator controls.",
                        "Our incinerator runs on a 60-second cycle. "
                        "Very efficient. Very final.",
                        "You look familiar. Have you caused any galactic "
                        "incidents lately?",
                    ])
            ]
        )

        incinerator = Room(
            name="Incinerator Chamber",
            description=lambda: self._incinerator_desc(),
            exits={},
            items=[]
        )
        incinerator.on_enter = self._on_enter_incinerator
        incinerator.on_tick = self._incinerator_tick

        ceo_hallway = Room(
            name="CEO Hallway",
            description=lambda: self._ceo_hallway_desc(),
            exits={"west": "monolith_burger_kitchen", "east": "ceo_office"},
            items=[]
        )

        ceo_office = Room(
            name="CEO Office",
            description=lambda: self._ceo_office_desc(),
            exits={"west": "ceo_hallway", "north": "holding_cell"},
            items=[],
            npcs=[
                NPC("CEO Nigel Rancid", ["ceo", "nigel", "rancid", "boss", "suit"],
                    [
                        "'What are YOU doing in my office?! Security!'",
                        "'The Two Guys? They work for ME now. "
                        "Their talents are wasted on games.'",
                        "'Get out before I have you incinerated. "
                        "We have a very efficient incinerator, you know.'",
                        "'I can smell that lunch box from here. "
                        "Is that... a Monolith Burger? I haven't eaten since—' "
                        "He catches himself. 'GET OUT.'",
                    ]),
            ]
        )
        ceo_office.on_enter = self._on_enter_ceo_office

        holding_cell = Room(
            name="Holding Cell",
            description=lambda: self._holding_cell_desc(),
            exits={"south": "ceo_office"},
            items=[],
            npcs=[
                NPC("Mark Crowe", ["mark", "crowe", "tall", "guys"],
                    [
                        "'You're here to rescue us, right? RIGHT? I knew "
                        "someone would come! I've been planning our escape "
                        "for weeks!'",
                        "'Once we're out of here, we're going to make the "
                        "greatest game the galaxy has ever seen. I've got "
                        "ideas. SO many ideas.'",
                        "'Scott keeps saying we're doomed, but I told him — "
                        "heroes always show up at the last minute. And here "
                        "you are! Slightly late, but here!'",
                    ]),
                NPC("Scott Murphy", ["scott", "murphy", "short"],
                    [
                        "'Don't get your hopes up. The last three rescue "
                        "attempts ended in the incinerator. I've been "
                        "keeping count.'",
                        "'Even if we get out, how are we getting off this "
                        "rock? Do you even HAVE a ship? Please tell me "
                        "you have a ship.'",
                        "'Mark thinks everything will work out fine. Mark "
                        "also thought working for this CEO was a good idea. "
                        "Mark's judgment is... optimistic.'",
                    ]),
            ]
        )

        # ================================================================
        # Register all rooms
        # ================================================================

        for room in [junk_pile, engine_room, catwalk, airlock_corridor,
                     escape_pod_bay, escape_pod_landed, mb_exterior,
                     mb_counter, mb_kitchen, incinerator, ceo_hallway,
                     ceo_office, holding_cell]:
            key = room.name.lower().replace(" - ", "_").replace(" ", "_").replace("-", "_")
            self.rooms[key] = room

        # ================================================================
        # Game state flags
        # ================================================================

        self._pod_launched = False          # freighter pod launched
        self._oil_cleared = False           # mop used on oil slick
        self._pipe_fixed = False            # wrench used on steam pipe
        self._locker_opened = False         # scrap metal used on locker
        self._fuel_cell_inserted = False    # fuel cell in pod
        self._hired = False                 # got the job
        self._incinerator_active = False
        self._incinerator_turns = 0
        self._incinerator_max = 8
        self._flux_capacitor_retrieved = False
        self._customer_talked = False       # learned about Two Guys
        self._ceo_distracted = False        # CEO lured away with lunch box
        self._two_guys_freed = False        # holding cell unlocked
        self._two_guys_following = False    # Two Guys are with Roger
        self._bribed_cashier = False        # Feature 6: bought meal from cashier

        # Convenience refs
        self._engine_room = engine_room
        self._catwalk = catwalk
        self._incinerator = incinerator
        self._ceo_office = ceo_office
        self._holding_cell = holding_cell
        self._mb_kitchen = mb_kitchen
        self._escape_pod_landed = escape_pod_landed

        self.player = Player(junk_pile)

    # ------------------------------------------------------------------
    # Dynamic descriptions
    # ------------------------------------------------------------------

    def _engine_room_desc(self):
        base = (
            "The freighter's engine room hums with the sound of machinery "
            "that really should have been serviced about forty years ago. "
            "Pipes leak unidentified fluids. "
        )
        if not self._pipe_fixed:
            base += (
                "A burst steam pipe on the north wall is spraying scalding "
                "vapor across the ladder to the catwalk — you can't climb "
                "up safely like this. "
            )
        else:
            base += "The steam pipe is now sealed. The ladder up is clear. "
        if not self._oil_cleared:
            base += (
                "A spreading oil slick covers the floor near the ladder. "
            )
        base += "The junk pile is back west."
        return base

    def _catwalk_desc(self):
        base = (
            "A rickety metal catwalk overlooks the engine room below. "
            "From up here you can see the full scope of the freighter's "
            "mechanical neglect. "
        )
        if not self._locker_opened:
            base += (
                "A metal storage locker on the west wall has its door "
                "jammed shut. Something rattles inside. "
            )
        else:
            base += "The storage locker hangs open, empty now. "
        base += "The ladder leads back down. The escape pod bay is east."
        return base

    def _escape_pod_bay_desc(self):
        if self._pod_launched:
            return (
                "The escape pod bay is empty now, save for scorch marks "
                "where your pod used to be."
            )
        base = (
            "The escape pod bay holds one battered XJ-7 'Coffin Class' "
            "escape pod. The flux capacitor housing on its side panel "
            "is conspicuously empty — this thing isn't going anywhere "
            "without one. A card reader on the wall controls the launch "
            "sequence. "
        )
        if self._fuel_cell_inserted:
            base += "The pod's nav display glows green. "
        base += "The catwalk is west. The airlock corridor is south."
        return base

    def _escape_pod_landed_desc(self):
        base = (
            "Your escape pod sits here, slightly singed and smelling of "
            "fear. The hatch is open. Monolith Burger is to the north. "
        )
        if self._two_guys_following:
            base += (
                "Mark Crowe and Scott Murphy are crouched next to the pod, "
                "already elbow-deep in the flux capacitor housing. "
                "'Almost got it!' Mark shouts. Scott mutters something "
                "about safety protocols. "
            )
        return base

    def _kitchen_desc(self):
        base = (
            "The kitchen is a marvel of industrial food production. "
            "Conveyor belts carry unidentified patties past open flames. "
        )
        if self._hired:
            base += (
                "A door to the north leads to the incinerator. "
                "A door to the east leads to the CEO hallway. "
            )
        else:
            base += (
                "A door in the back is labeled "
                "'INCINERATOR — AUTHORIZED PERSONNEL ONLY.' "
            )
        base += "The counter is back west."
        return base

    def _incinerator_desc(self):
        remaining = self._incinerator_max - self._incinerator_turns
        if remaining > 5:
            heat = "The room is warm. Uncomfortably warm."
        elif remaining > 3:
            heat = "The walls are glowing faintly orange. This is not good."
        elif remaining > 1:
            heat = "The heat is intense. Your eyebrows are reconsidering their life choices."
        else:
            heat = "IT IS VERY HOT. YOU ARE ABOUT TO BECOME A ROGER CRISP."
        base = (
            "You are in the Monolith Burger incinerator chamber. The walls "
            "are slowly closing in. This is exactly like that scene in "
            "Star Wars, except instead of a princess there is a spatula, "
            "and instead of a dashing smuggler there is you. "
            f"{heat} "
            "A heavy blast door is to the south (locked). A control "
            "panel on the north wall has a keyhole. "
        )
        if self._flux_capacitor_retrieved:
            base += "The flux capacitor slot on the wall is now empty. "
        else:
            base += (
                "Mounted on the east wall, behind a wire cage, is a "
                "glowing device labeled 'FLUX CAPACITOR — DO NOT REMOVE.' "
                "Someone has added '(unless emergency)' in marker. "
            )
        return base

    def _ceo_hallway_desc(self):
        base = (
            "A carpeted hallway lined with framed motivational posters. "
            "One reads: 'YOU CAN DO IT — unless you work here, in which "
            "case you cannot.' The CEO's office is east. "
            "The kitchen is back west. "
        )
        if not self._ceo_distracted:
            base += (
                "The CEO office door has a latch that looks like it could "
                "be jammed open with something thin and flat. "
            )
        return base

    def _ceo_office_desc(self):
        if self._ceo_distracted:
            return (
                "The CEO's office is empty — Nigel Rancid has stepped out, "
                "apparently lured by the irresistible aroma of a Monolith "
                "Burger. On his desk sits a key labeled 'HOLDING CELL.' "
                "The holding cell door is north. The hallway is west."
            )
        return (
            "A lavishly appointed office that screams 'I compensate for "
            "something.' CEO Nigel Rancid sits behind a desk the size of "
            "a small moon, glaring at you. A door to the north is labeled "
            "'HOLDING CELL.' The hallway is west."
        )

    def _holding_cell_desc(self):
        if self._two_guys_freed:
            return (
                "The holding cell is empty now, save for two sets of "
                "hastily discarded shackles and a half-finished game "
                "design document titled 'Space Quest 4: Roger Wilco and "
                "the Time Rippers.' The CEO office is south."
            )
        return (
            "A small, damp cell. Two disheveled men in matching jumpsuits "
            "sit on a bench. The tall one bounces with nervous energy. "
            "The short one looks like he's calculating escape routes. "
            "'Are you here to rescue us?' the tall one asks. 'We're Mark "
            "and Scott — the Two Guys from Andromeda. We can fix anything "
            "— ships, computers, bad sequels. Just get us OUT of here.' "
            "The CEO office is south."
        )

    # ------------------------------------------------------------------
    # Room event handlers
    # ------------------------------------------------------------------

    def _on_enter_pod_bay(self, brief=False):
        self.player.room.describe(brief=brief, game=self)

    def _on_enter_pod_landed(self, brief=False):
        if self._two_guys_following:
            # Add Two Guys NPCs if not already there
            room = self.player.room
            if not room.get_npc("mark"):
                room.npcs.append(
                    NPC("Mark Crowe",
                        ["mark", "crowe", "tall", "guys"],
                        [
                            "'Hand us that flux capacitor and we'll have "
                            "you flying in minutes! I've done this before!'",
                            "'This is EXCITING! A real escape! Just like "
                            "in the games we used to make!'",
                            "'Just give us the flux capacitor. Please.'",
                        ])
                )
            if not room.get_npc("scott"):
                room.npcs.append(
                    NPC("Scott Murphy",
                        ["scott", "murphy", "short"],
                        [
                            "'The flux capacitor housing is standard XJ-7. "
                            "I can rewire it, but I need the actual capacitor.'",
                            "'If this pod explodes, I want it on record that "
                            "this was Mark's idea.'",
                            "'Just give us the flux capacitor. Please.'",
                        ])
                )
        self.player.room.describe(brief=brief, game=self)

    def _on_enter_incinerator(self, brief=False):
        self._autosave()  # Feature 4: auto-save before incinerator
        self._incinerator_active = True
        self._incinerator_turns = 0
        if self.sound:
            self.sound.play_sfx('door_slam')
        say(
            "The door slams shut behind you with a very final-sounding CLANG. "
            "A cheerful recorded voice announces: 'Incineration cycle "
            "initiated. Please remain calm. Monolith Burger is not "
            "responsible for any vaporization that may occur.' "
            "The walls begin to glow."
        )
        say(f"You have {self._incinerator_max} turns to find a way out "
            "before you become the day's special.")
        self.player.room.describe(game=self)

    def _incinerator_tick(self):
        if not self._incinerator_active:
            return
        self._incinerator_turns += 1
        remaining = self._incinerator_max - self._incinerator_turns
        if self.sound:
            if remaining <= 2:
                self.sound.play_sfx('incinerator_critical')
            elif remaining <= 5:
                self.sound.play_sfx('incinerator_warning')
        if remaining <= 0:
            die(
                "The incinerator reaches full temperature. The last thing "
                "Roger Wilco sees is a cheerful Monolith Burger logo on "
                "the wall. The last thing he smells is himself. "
                "He is, briefly, the most well-done item on the menu."
            )
        elif remaining == 3:
            say(f"[The walls are very close now. {remaining} turns remaining.]")
        elif remaining == 1:
            say("[ONE TURN LEFT. DO SOMETHING.]")

    def _on_enter_ceo_office(self, brief=False):
        if not self._ceo_distracted:
            # CEO blocks the north door
            self._ceo_office.exits = {"west": "ceo_hallway"}
        else:
            self._ceo_office.exits = {"west": "ceo_hallway", "north": "holding_cell"}
        self.player.room.describe(brief=brief, game=self)

    # ------------------------------------------------------------------
    # Helper
    # ------------------------------------------------------------------

    def _find_room(self, key):
        if key in self.rooms:
            return self.rooms[key]
        for r in self.rooms.values():
            if r.name.lower() == key.lower():
                return r
        return None

    def _score(self, points, reason=None):
        self.player.score += points
        if points > 0 and self.sound:
            self.sound.play_sfx('score_up')

    # Feature 5: wrong-item response table
    WRONG_USE_RESPONSES = {
        ("Mop", "CEO Office"): "You consider mopping the CEO. He looks like he could use it.",
        ("Spatula", "Incinerator Chamber"): "The spatula melts slightly. That was not the right tool.",
        ("Wrench", "CEO Office"): "Tempting, but assault charges are hard to explain on a resume.",
        ("Wrench", "Escape Pod Bay"): "You bang on the pod with the wrench. It makes a satisfying clang and accomplishes nothing.",
        ("Flux Capacitor", "Monolith Burger - Counter"): "You hold up the flux capacitor. It hums. You have no idea what to do with it.",
        ("Flux Capacitor", "Monolith Burger - Kitchen"): "You hold up the flux capacitor. It hums. You have no idea what to do with it.",
        ("Flux Capacitor", "CEO Office"): "You hold up the flux capacitor. It hums. You have no idea what to do with it.",
        ("Flux Capacitor", "CEO Hallway"): "You hold up the flux capacitor. It hums. You have no idea what to do with it.",
        ("Grease Trap Key", "CEO Office"): "The key doesn't fit anything here. It's very specifically an incinerator key.",
        ("Grease Trap Key", "Escape Pod Bay"): "The key doesn't fit anything here. It's very specifically an incinerator key.",
        ("Grease Trap Key", "Engine Room"): "The key doesn't fit anything here. It's very specifically an incinerator key.",
        ("Scrap Metal", "Engine Room"): "You poke at things with the scrap metal. Nothing gives.",
        ("Scrap Metal", "CEO Office"): "You poke at things with the scrap metal. Nothing gives.",
        ("Scrap Metal", "Escape Pod Bay"): "You poke at things with the scrap metal. Nothing gives.",
        ("Fuel Cell", "Engine Room"): "The fuel cell has nowhere to go here.",
        ("Fuel Cell", "Monolith Burger - Kitchen"): "The fuel cell has nowhere to go here.",
        ("Fuel Cell", "CEO Office"): "The fuel cell has nowhere to go here.",
        ("Access Card", "Engine Room"): "The card reader blinks at you from across the room. You're not close enough.",
        ("Access Card", "Monolith Burger - Counter"): "The card reader blinks at you from across the room. You're not close enough.",
    }

    # Item-only fallbacks (any room not matching a specific combo)
    WRONG_USE_ITEM_ONLY = {
        "Mop": "You wave the mop around. Nothing gets cleaner.",
        "Lunch Box": "You open the lunch box. The smell wafts out. Nobody relevant is here to care.",
        "Flux Capacitor": "You hold up the flux capacitor. It hums. You have no idea what to do with it.",
        "Grease Trap Key": "The key doesn't fit anything here. It's very specifically an incinerator key.",
        "Scrap Metal": "You poke at things with the scrap metal. Nothing gives.",
        "Fuel Cell": "The fuel cell has nowhere to go here.",
        "Access Card": "The card reader blinks at you from across the room. You're not close enough.",
    }

    def _check_wrong_use(self, item, room):
        """Return a snarky response for wrong item/room combos, or None."""
        key = (item.name, room.name)
        resp = self.WRONG_USE_RESPONSES.get(key)
        if resp:
            return resp
        return self.WRONG_USE_ITEM_ONLY.get(item.name)

    def _maybe_intercom(self):
        """Feature 9: play intercom messages at intervals."""
        if self.turn < self._next_intercom:
            return
        room = self.player.room
        # Don't play during incinerator (too tense) or at win screen
        if room.name == "Incinerator Chamber":
            return
        # Pick the right message list
        if not self._pod_launched:
            messages = FREIGHTER_INTERCOM
        else:
            messages = MB_INTERCOM
        if not messages:
            return
        msg = messages[self._intercom_index % len(messages)]
        if self.sound:
            self.sound.play_sfx('intercom')
        say(msg)
        self._intercom_index += 1
        self._next_intercom = self.turn + random.randint(4, 7)

    # ------------------------------------------------------------------
    # Command handlers
    # ------------------------------------------------------------------

    def cmd_look(self, tokens):
        if len(tokens) <= 1 or tokens[1] in ("around", "room"):
            self.player.room.describe(game=self)
            return
        target = tokens[-1]
        multi = " ".join(tokens[1:])
        # Room items
        item = self.player.room.get_item(target) or self.player.room.get_item(multi)
        if item:
            say(item.description)
            return
        # Inventory
        item = self.player.get_inv_item(target) or self.player.get_inv_item(multi)
        if item:
            say(item.description)
            return
        # NPCs
        npc = self.player.room.get_npc(target) or self.player.room.get_npc(multi)
        if npc:
            say(f"It's {npc.name}. They look like they've seen better days, "
                "but then again, so have you.")
            return
        # Special scenery
        if target in ("receipt", "note") and self.player.room.name == "Junk Pile":
            say("You don't have the receipt yet — it's inside the lunch box.")
            return
        say("You don't see that here.")

    def cmd_examine(self, tokens):
        """Feature 3: examine gives more detail than look."""
        if len(tokens) <= 1 or tokens[1] in ("around", "room"):
            self.player.room.describe(game=self)
            return
        target = tokens[-1]
        multi = " ".join(tokens[1:])
        # Room items
        item = self.player.room.get_item(target) or self.player.room.get_item(multi)
        if item:
            say(item.examine_description or item.description)
            return
        # Inventory
        item = self.player.get_inv_item(target) or self.player.get_inv_item(multi)
        if item:
            say(item.examine_description or item.description)
            return
        # NPCs
        npc = self.player.room.get_npc(target) or self.player.room.get_npc(multi)
        if npc:
            say(f"It's {npc.name}. They look like they've seen better days, "
                "but then again, so have you.")
            return
        # Special scenery
        if target in ("receipt", "note") and self.player.room.name == "Junk Pile":
            say("You don't have the receipt yet — it's inside the lunch box.")
            return
        say("You don't see that here.")

    def cmd_take(self, tokens):
        if len(tokens) < 2:
            say("Take what? Be specific.")
            return
        target = tokens[-1]
        item = self.player.room.get_item(target) or self.player.room.get_item(" ".join(tokens[1:]))
        if not item:
            say("You don't see that here.")
            return
        if not item.takeable:
            say(f"You can't take the {item.name}. It's not going anywhere.")
            return
        self.player.room.items.remove(item)
        self.player.take(item)
        say(f"You take the {item.name}.")
        if self.sound:
            self.sound.play_sfx('item_pickup')
        # Score milestones
        score_items = {
            "Access Card": 5, "Flux Capacitor": 15,
            "Holding Cell Key": 10, "Grease Trap Key": 5,
        }
        if item.name in score_items:
            self._score(score_items[item.name])

    def cmd_drop(self, tokens):
        if len(tokens) < 2:
            say("Drop what?")
            return
        item = self.player.get_inv_item(tokens[-1])
        if not item:
            say("You're not carrying that.")
            return
        self.player.drop_item(item)
        self.player.room.items.append(item)
        say(f"You drop the {item.name}.")

    def cmd_inventory(self, tokens):
        if not self.player.inventory:
            say("You are carrying nothing. You are, in the truest sense, "
                "a man with nothing to lose.")
        else:
            say("You are carrying:")
            for item in self.player.inventory:
                say(f"  - {item.name}: {item.description}")

    def cmd_go(self, tokens):
        if len(tokens) < 2:
            say("Go where?")
            return
        direction = DIRECTIONS.get(tokens[-1], tokens[-1])
        room_key = self.player.room.exits.get(direction)
        if not room_key:
            say("You can't go that way.")
            return
        # Blocked passages
        if self._go_blocked(direction, room_key):
            return
        target = self._find_room(room_key)
        if not target:
            say("You can't go that way right now.")
            return
        self.player.room = target
        use_brief = not self._verbose and target.visited
        self._play_room_music()
        if target.on_enter:
            target.on_enter(brief=use_brief)
        else:
            target.describe(brief=use_brief, game=self)
        target.visited = True

    def _go_blocked(self, direction, room_key):
        room = self.player.room
        # Catwalk ladder blocked by steam until pipe is fixed
        if room.name == "Engine Room" and direction == "up":
            if not self._pipe_fixed:
                say(
                    "The burst steam pipe is spraying scalding vapor all "
                    "over the ladder. You'd be parboiled before you reached "
                    "the second rung. You should fix that pipe first."
                )
                return True
            if not self._oil_cleared:
                say(
                    "The oil slick at the base of the ladder is too slippery. "
                    "You'd fall flat on your face. You should clean it up first."
                )
                return True
        # CEO office north door blocked until CEO is distracted
        if room.name == "CEO Office" and direction == "north":
            if not self._ceo_distracted:
                # Feature 10: CEO physically ejects Roger
                if not self._ejected_by_ceo:
                    self._ejected_by_ceo = True
                    say(
                        "CEO Nigel Rancid rises from his desk like a corporate "
                        "kraken emerging from the deep. 'I don't THINK so,' he "
                        "growls. Before you can react, he grabs you by the collar "
                        "and the seat of your pants and hurls you bodily out of "
                        "his office. You sail through the hallway, through the "
                        "kitchen, past a startled manager, out the front door, "
                        "across the parking lot, and land face-first next to "
                        "your escape pod. The narrator is impressed by the "
                        "distance, if not the landing."
                    )
                else:
                    say(
                        "CEO Nigel Rancid doesn't even look up this time. "
                        "He just presses a button on his desk. A trapdoor opens "
                        "beneath your feet. You slide down a chute and land "
                        "next to your escape pod. Again. 'Stay out,' echoes "
                        "from a speaker above."
                    )
                # Move Roger to the escape pod (landed)
                target = self._find_room("escape_pod_(landed)")
                if target:
                    if self.sound:
                        self.sound.play_sfx('ceo_ejection')
                    self.player.room = target
                    self._play_room_music()
                    target.describe(game=self)
                return True
        # Holding cell requires Two Guys to be freed first to leave
        return False

    def cmd_use(self, tokens):
        if len(tokens) < 2:
            say("Use what?")
            return
        if "on" in tokens:
            idx = tokens.index("on")
            item_words = tokens[1:idx]
            target_words = tokens[idx+1:]
        else:
            item_words = tokens[1:]
            target_words = []
        item_name = item_words[-1] if item_words else ""
        target_name = target_words[-1] if target_words else ""

        item = self.player.get_inv_item(item_name) or self.player.room.get_item(item_name)
        if not item:
            say(f"You don't have a {item_name}.")
            return

        # If multiple items could match (e.g. "key"), prefer the one
        # that makes sense in the current room context.
        if item_name == "key" and self.player.room.name == "Holding Cell":
            hck = self.player.get_inv_item("cellkey") or self.player.get_inv_item("holding")
            if hck:
                item = hck

        room = self.player.room

        # Feature 7: "use button" redirects to press
        if item.name == "Button":
            self.cmd_press(["press", "button"])
            return

        # --- Wrench on steam pipe (engine room) ---
        if item.name == "Wrench" and room.name == "Engine Room":
            if self._pipe_fixed:
                say("The pipe is already fixed. Roger resists the urge to "
                    "unfix it just to feel useful.")
            else:
                say(
                    "You apply the wrench to the burst pipe with the "
                    "confidence of someone who has watched exactly one "
                    "plumbing video. The pipe groans, then seals. "
                    "The steam stops. The ladder is now accessible."
                )
                self._pipe_fixed = True
                self._engine_room.exits["up"] = "engine_room_catwalk"
                self._score(5)
            return

        # --- Mop on oil slick (engine room) ---
        if item.name == "Mop" and room.name == "Engine Room":
            if not self._pipe_fixed:
                say("You mop at the oil, but more keeps dripping from the "
                    "burst pipe above. Fix the pipe first.")
            elif self._oil_cleared:
                say("The floor is already clean. Roger feels a rare "
                    "professional satisfaction.")
            else:
                say(
                    "You mop up the oil slick with practiced efficiency. "
                    "This is, after all, what Roger Wilco was born to do. "
                    "The floor is clear. The ladder is safe to climb."
                )
                self._oil_cleared = True
                # Remove oil slick item
                room.items = [i for i in room.items if i.name != "Oil Slick"]
                self._score(5)
            return

        # --- Scrap metal on locker (catwalk) ---
        if item.name == "Scrap Metal" and room.name == "Engine Room Catwalk":
            if self._locker_opened:
                say("The locker is already open and empty.")
            else:
                say(
                    "You jam the scrap metal into the locker door gap and "
                    "lever it open with a satisfying CRACK. Inside, wedged "
                    "behind a spare jumpsuit, is a magnetic access card. "
                    "Someone has written 'NOT A MASTER KEY' on it in marker. "
                    "They were lying."
                )
                self._locker_opened = True
                room.items = [i for i in room.items if i.name != "Locker"]
                access_card = Item(
                    "Access Card", ["card", "access", "keycard"],
                    "A magnetic access card. Someone has written 'NOT A MASTER KEY' "
                    "on it in marker. They were lying."
                )
                room.items.append(access_card)
                self._score(5)
            return

        # --- Fuel cell on pod (escape pod bay) ---
        if item.name == "Fuel Cell" and room.name == "Escape Pod Bay":
            if self._fuel_cell_inserted:
                say("The fuel cell is already installed.")
            else:
                say(
                    "You slot the fuel cell into the pod's auxiliary power "
                    "port. The nav display flickers to life, showing a "
                    "destination: MONOLITH BURGER LOCATION 7. "
                    "Now you just need that access card."
                )
                self._fuel_cell_inserted = True
                self._score(5)
            return

        # --- Access card on pod bay reader ---
        if item.name == "Access Card" and room.name == "Escape Pod Bay":
            self._launch_pod()
            return

        # --- Grease trap key on incinerator panel ---
        if item.name == "Grease Trap Key" and room.name == "Incinerator Chamber":
            say(
                "You jam the key into the keyhole on the control panel. "
                "It fits! You turn it. A cheerful voice announces: "
                "'Emergency override accepted. Incineration cycle "
                "cancelled. Have a Monolith day!' "
                "The blast door to the south slides open."
            )
            self._incinerator_active = False
            self._incinerator.exits["south"] = "monolith_burger_kitchen"
            self._score(10)
            say("The south door is now open.")
            # Reveal flux capacitor as takeable item
            if not self._flux_capacitor_retrieved:
                flux = Item(
                    "Flux Capacitor",
                    ["flux", "capacitor", "device", "part"],
                    "The flux capacitor. It glows faintly and hums with "
                    "contained temporal energy. Or possibly it just needs "
                    "new batteries. Either way, your pod needs this."
                )
                self._incinerator.items.append(flux)
                say(
                    "With the heat off, you can now safely reach the flux "
                    "capacitor mounted on the east wall. It's right there "
                    "for the taking."
                )
            return

        # --- Flux capacitor taken (score) ---
        # (handled in cmd_take score dict, but flag it here)

        # --- Application form to manager ---
        if item.name == "Application Form":
            manager = room.get_npc("manager")
            if manager:
                self._hire_roger()
                return
            say("You wave the application around. Nobody relevant is here.")
            return

        # --- Spatula on CEO hallway door latch ---
        if item.name == "Spatula" and room.name == "CEO Hallway":
            say(
                "You slide the spatula into the gap between the CEO office "
                "door and the frame, flip the latch, and ease the door open. "
                "Years of flipping patties have finally paid off."
            )
            self._ceo_hallway_door_jammed = True
            # Already accessible via exit, just flavor
            self._score(5)
            return

        # --- Lunch box on CEO (distract him) ---
        if item.name == "Lunch Box" and room.name == "CEO Office":
            if self._ceo_distracted:
                say("The CEO is already gone. The lunch box did its job.")
            else:
                say(
                    "You open the lunch box. The aroma of a half-eaten "
                    "Monolith Burger fills the room. CEO Nigel Rancid's "
                    "nostrils flare. His eyes go wide. "
                    "'Is that... a Number Three? With extra sauce?' "
                    "He stands up, smooths his jacket, and walks briskly "
                    "out the west door, muttering about a 'working lunch.' "
                    "On his desk, you notice a key labeled 'HOLDING CELL.'"
                )
                self._distract_ceo()
            return

        # --- Feature 6: Monolith Meal on CEO (alternative distraction) ---
        if item.name == "Monolith Meal" and room.name == "CEO Office":
            if self._ceo_distracted:
                say("The CEO is already gone. No need for more food-based bribery.")
            else:
                say(
                    "You hold up the steaming Monolith Meal. The aroma hits "
                    "CEO Nigel Rancid like a freight train of grease and desire. "
                    "His nostrils flare. His pupils dilate. "
                    "'Is that... FRESH? A fresh Number Three?!' "
                    "He vaults over his desk with surprising agility and "
                    "snatches the meal from your hands, disappearing out the "
                    "west door in a blur of expensive suit and desperation. "
                    "On his desk, you notice a key labeled 'HOLDING CELL.'"
                )
                self._distract_ceo()
            return

        # --- Holding cell key on cell door ---
        if item.name == "Holding Cell Key" and room.name == "Holding Cell":
            if self._two_guys_freed:
                say("They're already free. The key is just a souvenir now.")
            else:
                say(
                    "You unlock the holding cell door. It swings open with "
                    "a dramatic creak. Mark Crowe leaps to his feet. "
                    "'FREEDOM!' he shouts. Scott Murphy stands up more "
                    "cautiously. 'Don't celebrate yet,' he mutters. "
                    "'Do you have a flux capacitor?' You hold it up. "
                    "Mark's eyes light up. Scott nods approvingly. "
                    "'XJ-7 housing. We can fix that. Lead the way!'"
                )
                self._two_guys_freed = True
                self._two_guys_following = True
                self._holding_cell.npcs = []
                if self.sound:
                    self.sound.play_sfx('unlock')
                self._score(15)
            return

        # --- Flux capacitor at landed pod (with Two Guys) ---
        if item.name == "Flux Capacitor" and room.name == "Escape Pod (Landed)":
            if not self._two_guys_following:
                say(
                    "You hold up the flux capacitor and stare at it. "
                    "You have absolutely no idea how to install this. "
                    "You need someone who does."
                )
            else:
                self._install_flux_capacitor()
            return

        # Feature 5: wrong-item snarky responses
        wrong_use = self._check_wrong_use(item, room)
        if wrong_use:
            say(wrong_use)
            return

        say(
            f"You use the {item.name}. Nothing interesting happens. "
            "Roger looks mildly disappointed, which is his default expression."
        )

    def _launch_pod(self):
        if not self._fuel_cell_inserted:
            say(
                "You swipe the card. The pod hatch opens, but the nav "
                "computer is dead — no power. You'll need a fuel cell "
                "to get the systems running first."
            )
            return
        say(
            "You swipe the access card. The pod hatch hisses open. "
            "You climb in, strap yourself to a seat designed for a "
            "species with three spines, and hit the launch button."
        )
        if self.sound:
            self.sound.stop_music()
            self.sound.play_sfx('pod_launch')
        say(
            "The pod rockets out of the freighter with all the grace "
            "of a thrown refrigerator. Through the porthole you watch "
            "the garbage freighter recede into the distance. Good riddance."
        )
        say(
            "After what feels like several hours of being compressed "
            "into a shape nature never intended, the pod crash-lands "
            "on a nearby planetoid. The hatch pops open. "
            "You smell grease. And something that was once a vegetable."
        )
        say("You have arrived at MONOLITH BURGER.")
        self._pod_launched = True
        self._score(15)
        self.player.room = self.rooms["escape_pod_(landed)"]
        self._play_room_music()
        self.player.room.describe(game=self)

    def _hire_roger(self):
        if self._hired:
            say(
                "The manager glances at you. 'You already work here, Wilco. "
                "Go check that incinerator. North door.'"
            )
            return
        say(
            "You hand the application to the manager. He squints at it. "
            "'Wilco? Roger Wilco? The janitor who saved the universe "
            "three times and still can't hold down a job?' "
            "He stamps it APPROVED. 'You start immediately. "
            "First task: check the incinerator.' He points north. "
            "You have a very bad feeling about this."
        )
        self._hired = True
        self._mb_kitchen.exits["north"] = "incinerator_chamber"
        self._mb_kitchen.exits["east"] = "ceo_hallway"
        self._score(10)

    def _distract_ceo(self):
        """Shared logic for distracting the CEO (lunch box or meal)."""
        self._ceo_distracted = True
        self._ceo_office.exits["north"] = "holding_cell"
        key = Item(
            "Holding Cell Key",
            ["holding", "cell", "key", "cellkey", "desk"],
            "A key labeled 'HOLDING CELL.' It's attached to a "
            "keychain shaped like a tiny Monolith Burger."
        )
        self._ceo_office.items.append(key)
        self._ceo_office.npcs = []
        self._score(10)

    def _install_flux_capacitor(self):
        say(
            "You hand the flux capacitor to Mark and Scott. They descend "
            "on the pod's open panel like caffeinated engineers at a "
            "hackathon. Sparks fly. Wrenches turn. Mark says "
            "'try it now' three times before Scott finally agrees it works."
        )
        say(
            "The pod's systems come fully online. The nav computer "
            "displays a destination: XENON. Home. "
            "'She's ready,' Scott announces, wiping his "
            "hands on his jumpsuit. 'And she'll hold three passengers. "
            "Barely. But she'll hold.' "
            "Mark is already climbing in."
        )
        self._score(20)
        win(
            "You climb into the pod with Mark Crowe and Scott Murphy. "
            "The hatch seals. The engines fire. "
            "Monolith Burger Location 7 shrinks to a greasy dot below you. "
            "Somewhere on that planetoid, CEO Nigel Rancid is still "
            "looking for his Number Three with extra sauce. "
            "Roger Wilco, Janitor First Class, has done it again."
        )

    def cmd_talk(self, tokens):
        if len(tokens) < 2:
            say("Talk to whom?")
            return
        target = tokens[-1]
        npc = self.player.room.get_npc(target)
        if not npc:
            say("There's nobody by that name here to talk to.")
            return
        # Special interactions
        if npc.name == "Manager" and self.player.has("Application Form"):
            self._hire_roger()
            return
        if npc.name == "Fester Blatz":
            self._customer_talked = True
        if npc.name in ("Mark Crowe", "Scott Murphy"):
            if self._two_guys_following and self.player.room.name == "Escape Pod (Landed)":
                if npc.name == "Mark Crowe":
                    say(
                        "Mark looks up from the pod, grinning. "
                        "'Almost done! Just need the flux capacitor installed. "
                        "This is going to be GREAT!'"
                    )
                else:
                    say(
                        "Scott looks up from the pod, frowning. "
                        "'Almost done. Just need the flux capacitor. "
                        "Assuming it doesn't explode when we install it.'"
                    )
                return
        npc.talk()

    def cmd_give(self, tokens):
        if len(tokens) < 2:
            say("Give what to whom?")
            return
        words = [w for w in tokens[1:] if w != "to"]
        if len(words) < 2:
            say("Give what to whom?")
            return
        item = self.player.get_inv_item(words[0])
        if not item:
            say(f"You're not carrying a {words[0]}.")
            return
        npc = self.player.room.get_npc(words[-1])
        if not npc:
            say(f"There's no {words[-1]} here to give things to.")
            return
        if item.name == "Application Form" and npc.name == "Manager":
            self._hire_roger()
            return
        if item.name == "Lunch Box" and npc.name == "CEO Nigel Rancid":
            # Redirect to use handler
            self.cmd_use(["use", "lunch", "on", "ceo"])
            return
        # Feature 6: give credits to cashier
        if item.name == "Credits" and npc.name == "Cashier":
            self._buy_meal()
            return
        # Feature 6: give meal to CEO
        if item.name == "Monolith Meal" and npc.name == "CEO Nigel Rancid":
            self.cmd_use(["use", "meal", "on", "ceo"])
            return
        say(
            f"{npc.name} looks at the {item.name} with polite disinterest. "
            "'I don't want that.'"
        )

    def cmd_buy(self, tokens):
        """Feature 6: buy meal from cashier."""
        room = self.player.room
        cashier = room.get_npc("cashier")
        if not cashier:
            say("There's nobody here to buy anything from.")
            return
        if self._bribed_cashier:
            say("The cashier shrugs. 'One per customer. Corporate policy.'")
            return
        if not self.player.has("Credits"):
            say("The cashier stares at you. 'You got money, pal? "
                "We don't do charity here.'")
            return
        self._buy_meal()

    def _buy_meal(self):
        """Handle the meal purchase transaction."""
        if self._bribed_cashier:
            say("You already bought a meal. The cashier won't sell you another.")
            return
        # Remove credits
        credits_item = self.player.get_inv_item("credits")
        if credits_item:
            self.player.drop_item(credits_item)
        self._bribed_cashier = True
        meal = Item(
            "Monolith Meal",
            ["meal", "food", "burger", "number", "monolith"],
            "A fresh Monolith Burger meal, still steaming. The aroma is "
            "powerful enough to lure anyone within a fifty-foot radius."
        )
        self.player.take(meal)
        say(
            "You slap your Buckazoids on the counter. The cashier's eyes "
            "light up — apparently 10 Buckazoids is a big tip around here. "
            "'One Number Three, extra sauce, coming right up!' "
            "She slides a steaming Monolith Meal across the counter. "
            "The smell is... magnificent. In a terrifying sort of way."
        )
        self._score(5)

    def cmd_press(self, tokens):
        """Feature 7: DO NOT PRESS button."""
        room = self.player.room
        button = room.get_item("button")
        if not button:
            say("There's nothing here to press.")
            return
        self._button_presses += 1
        if self._button_presses == 1:
            if self.sound:
                self.sound.play_sfx('button_press')
            say(
                "You press the button. A ship-wide alarm blares. Red lights "
                "flash. The intercom crackles to life: 'WARNING: UNAUTHORIZED "
                "BUTTON PRESS DETECTED IN SECTOR 7-G. INITIATING... "
                "INITIATING...' A long pause. '...never mind. False alarm.' "
                "The lights return to normal. Nothing bad happened. "
                "You feel strangely accomplished."
            )
            self._score(2)
        elif self._button_presses == 2:
            if self.sound:
                self.sound.play_sfx('button_press')
            say(
                "You press the button again. Somewhere deep in the ship, "
                "a hatch opens with a distant CLANG. The intercom sighs — "
                "actually sighs — and says: 'Please stop pressing that. "
                "The button is not a toy. It is a very important button "
                "that does very important things. None of which concern you.'"
            )
        elif self._button_presses == 3:
            if self.sound:
                self.sound.play_sfx('electric_shock')
            say(
                "You press the button a third time. A jolt of electricity "
                "shoots through your finger and up your arm. 'OW!' The "
                "intercom sounds almost satisfied: 'We warned you. Twice. "
                "The button has been recalibrated to discourage further "
                "interaction. Have a nice day.' Roger shakes his hand, "
                "nursing a singed fingertip."
            )
            self._score(-1)
        else:
            say(
                "You reach for the button. Your finger twitches. The memory "
                "of the electric shock is still fresh. You press it anyway, "
                "because you are Roger Wilco. Nothing happens. The button "
                "has apparently given up on you."
            )

    def cmd_enter(self, tokens):
        pod_words = {"pod", "escape", "ship", "vessel", "coffin"}
        targeting_pod = bool(set(tokens[1:]) & pod_words) or len(tokens) == 1
        room = self.player.room
        if targeting_pod:
            if room.name == "Escape Pod Bay":
                if self.player.has("Access Card"):
                    self._launch_pod()
                else:
                    say(
                        "You yank on the pod hatch. It doesn't budge. "
                        "A card reader on the wall blinks at you. "
                        "You'll need an access card."
                    )
                return
            if room.name == "Escape Pod (Landed)":
                if self._two_guys_following and self.player.has("Flux Capacitor"):
                    self._install_flux_capacitor()
                elif self._two_guys_following:
                    say(
                        "Scott blocks the hatch. "
                        "'Not yet — we still need the flux capacitor installed. "
                        "Hand it over and we'll have you flying in minutes.'"
                    )
                else:
                    say(
                        "You climb in and poke at the controls. The nav "
                        "computer shows one destination: GARBAGE FREIGHTER. "
                        "You climb back out."
                    )
                return
        say("There's nothing obvious to enter here.")

    def cmd_verbose(self, tokens):
        self._verbose = True
        say("Verbose mode on. You will now get full room descriptions every time.")

    def cmd_brief(self, tokens):
        self._verbose = False
        say("Brief mode on. Rooms you've visited will show only the name and exits.")

    def cmd_ascii_off(self, tokens):
        self._show_ascii_art = False
        say("ASCII art disabled. Rooms will display without visual art.")

    def cmd_ascii_on(self, tokens):
        self._show_ascii_art = True
        if not _ASCII_ART_AVAILABLE:
            say("ASCII art module not available. Make sure ascii_art.py is in the game directory.")
        else:
            say("ASCII art enabled. You will now see visual art when entering rooms.")

    def cmd_ascii_show(self, tokens):
        if not _ASCII_ART_AVAILABLE:
            say("ASCII art module not available.")
            return
        if not self._show_ascii_art:
            say("ASCII art is currently disabled. Use 'ascii on' to enable it.")
            return
        # Show ASCII art for current room
        art = get_room_art(self.player.room.name)
        if art:
            print(art)
        else:
            say("No ASCII art available for this room.")

    def cmd_score(self, tokens):
        pct = self.player.score
        say(f"Your current score is {pct} points out of 120. "
            f"{'Not bad.' if pct > 60 else 'Keep going.'}")

    def cmd_map(self, tokens):
        """Display an ASCII map of visited rooms with current location marked."""
        here = self.player.room.name

        # Cell width (label area inside brackets)
        C = 12

        def fc(name):
            """Return a [label] cell: >label< if current room, ??? if unvisited."""
            key = name.lower().replace(" - ", "_").replace(" ", "_").replace("-", "_")
            room = self._find_room(key)
            if room is None or (not room.visited and room is not self.player.room):
                label = "???"
            else:
                short = {
                    "Junk Pile":                  "JUNK PILE",
                    "Engine Room":                "ENGINE RM",
                    "Engine Room Catwalk":        "CATWALK",
                    "Airlock Corridor":           "AIRLOCK",
                    "Escape Pod Bay":             "POD BAY",
                    "Escape Pod (Landed)":        "POD LANDED",
                    "Monolith Burger - Exterior": "MB EXTERIOR",
                    "Monolith Burger - Counter":  "MB COUNTER",
                    "Monolith Burger - Kitchen":  "MB KITCHEN",
                    "Incinerator Chamber":        "INCINERATR",
                    "CEO Hallway":                "CEO HALLWY",
                    "CEO Office":                 "CEO OFFICE",
                    "Holding Cell":               "HOLD. CELL",
                }.get(name, name[:C])
                label = f">{short}<" if name == here else short
            return f"[{label.center(C)}]"

        # Geometry: each cell is C+2 wide (brackets), connector is 4 dashes
        W = C + 2        # cell width = 14
        hc = "----"      # horizontal connector (4 chars)
        sp = " " * W     # blank spacer same width as a cell
        vc = "|".center(W)  # vertical connector

        # Total inner width for 3-cell rows: 3*W + 2*len(hc) = 42+8 = 50
        # Box inner width (between ║  and  ║): 50 + 4 margins = 54
        # Full line: "  ║  " + 50 + "  ║" = 5+50+3 = 58 chars
        # Box border: "  ╔" + "═"*54 + "╗" = 58 chars
        BOX = 54
        border_top    = "  ╔" + "═" * BOX + "╗"
        border_mid    = "  ╠" + "═" * BOX + "╣"
        border_bot    = "  ╚" + "═" * BOX + "╝"

        def bline(content):
            """Pad content to BOX width and wrap in box sides."""
            return "  ║  " + content.ljust(BOX - 4) + "  ║"

        def mrow(a, b, c):
            """Three-cell row with horizontal connectors."""
            return "  ║  " + a + hc + b + hc + c + "  ║"

        def lrow(a, b_gap, c):
            """Left cell, spacer, right cell (no middle cell)."""
            return "  ║  " + a + hc + b_gap + hc + c + "  ║"

        def srow(a):
            """Single cell row, padded to full box width."""
            inner = a
            return "  ║  " + inner.ljust(BOX - 4) + "  ║"

        def vrow(col0=False, col1=False, col2=False):
            """Vertical connector row for up to 3 columns, padded to full box width."""
            c0 = vc if col0 else sp
            c1 = vc if col1 else sp
            c2 = vc if col2 else sp
            inner = c0 + "   " + c1 + "   " + c2
            return "  ║  " + inner.ljust(BOX - 4) + "  ║"

        lines = [
            "",
            border_top,
            bline("     SPACE QUEST 7  --  NAVIGATION MAP"),
            border_mid,
            bline("  GARBAGE FREIGHTER"),
            border_mid,
            #
            # Freighter layout:
            #
            #  AIRLOCK ---- JUNK PILE ---- ENGINE RM
            #    |                              |
            #  POD BAY  ----  (blank)  ----  CATWALK
            #    |
            #  POD LANDED
            #
            mrow(fc("Airlock Corridor"), fc("Junk Pile"), fc("Engine Room")),
            vrow(col0=True, col2=True),
            lrow(fc("Escape Pod Bay"), sp, fc("Engine Room Catwalk")),
            vrow(col0=True),
            srow(fc("Escape Pod (Landed)")),
            #
            border_mid,
            bline("  MONOLITH BURGER"),
            border_mid,
            #
            # MB layout:
            #
            #  MB EXTERIOR
            #       |
            #  MB COUNTER ---- MB KITCHEN ---- INCINERATR
            #                       |
            #               CEO HALLWY ---- CEO OFFICE ---- HOLD. CELL
            #
            srow(fc("Monolith Burger - Exterior")),
            vrow(col0=True),
            mrow(fc("Monolith Burger - Counter"), fc("Monolith Burger - Kitchen"), fc("Incinerator Chamber")),
            vrow(col1=True),
            mrow(sp, fc("CEO Hallway"), fc("CEO Office")),
            # Holding Cell hangs off CEO Office — show on same row shifted right
            # Actually append it inline: CEO HALLWY ---- CEO OFFICE ---- HOLD. CELL
            # Rewrite last two rows:
        ]
        # Remove the last two lines and redo them properly
        lines.pop()  # remove vrow(col1)
        lines.pop()  # remove mrow(sp, CEO Hallway, CEO Office)

        # CEO row: blank ---- CEO HALLWY ---- CEO OFFICE ---- HOLD. CELL
        # That's 4 cells wide — too wide. Instead indent with sp and do 3 cells:
        #   sp  ----  CEO HALLWY  ----  CEO OFFICE  ----  HOLD. CELL
        # = sp(14) + hc(4) + cell(14) + hc(4) + cell(14) + hc(4) + cell(14) = 68 inner — too wide
        # Solution: drop the leading spacer, just show 3 cells starting from col0:
        #   CEO HALLWY ---- CEO OFFICE ---- HOLD. CELL
        lines.append(vrow(col1=True))
        lines.append(mrow(fc("CEO Hallway"), fc("CEO Office"), fc("Holding Cell")))

        lines += [
            border_mid,
            bline(f"  You are here: {here}"),
            bline("  >NAME< = current room    ??? = not yet visited"),
            border_bot,
            "",
        ]

        print("\n".join(lines))



    def cmd_help(self, tokens):
        say(
            "COMMANDS:\n"
            "  look / look at [thing]    -- examine surroundings or an object\n"
            "  examine / x [thing]       -- examine something in detail\n"
            "  take [item]               -- pick up an item\n"
            "  drop [item]               -- drop an item\n"
            "  inventory / i             -- check what you're carrying\n"
            "  go [direction]            -- move (north/south/east/west/up/down)\n"
            "  use [item] on [target]    -- use an item\n"
            "  give [item] to [person]   -- give an item to someone\n"
            "  talk to [person]          -- talk to someone\n"
            "  enter [pod/room]          -- enter something\n"
            "  buy [item]                -- buy something (if a vendor is present)\n"
            "  press [thing]             -- press a button or switch\n"
            "  again / g                 -- repeat last command\n"
            "  brief                     -- short room descriptions on revisit\n"
            "  verbose                   -- full room descriptions always\n"
            "  ascii_on                  -- enable ASCII art display\n"
            "  ascii_off                 -- disable ASCII art display\n"
            "  ascii_show                -- show ASCII art for current room\n"
            "  score                     -- check your score\n"
            "  map                       -- show a map of explored rooms\n"
            "  hint                      -- get a context-sensitive hint\n"
            "  save [slot]               -- save your game (default slot: 1)\n"
            "  restore [slot]            -- restore a saved game\n"
            "  quit                      -- give up\n"
            "\n"
            "Directions: n, s, e, w, u, d"
        )

    def cmd_hint(self, tokens):
        room = self.player.room.name
        inv = [i.name for i in self.player.inventory]

        # Work out what the player should be doing right now
        if room in ("Junk Pile", "Engine Room", "Engine Room Catwalk",
                    "Airlock Corridor", "Escape Pod Bay") and not self._pod_launched:
            # On the freighter
            if not self._pipe_fixed:
                if "Wrench" in inv:
                    say("Hint: That burst steam pipe in the engine room is blocking "
                        "the ladder. Use your wrench on it to tighten it back up.")
                else:
                    say("Hint: That burst steam pipe in the engine room is blocking "
                        "the ladder. You need a tool that can tighten things. "
                        "There's a wrench in the engine room.")
            elif not self._oil_cleared:
                if "Mop" in inv:
                    say("Hint: The oil slick at the base of the ladder is still "
                        "slippery. Use your mop to clean it up.")
                else:
                    say("Hint: The oil slick at the base of the ladder is still "
                        "slippery. Roger's most iconic tool — a mop — should handle that. "
                        "There's one in the junk pile.")
            elif not self._locker_opened:
                if "Scrap Metal" in inv:
                    say("Hint: There's a jammed locker on the catwalk. "
                        "Use your scrap metal to pry it open.")
                else:
                    say("Hint: There's a jammed locker on the catwalk. "
                        "A jagged piece of hull plating could pry it open. "
                        "There's scrap metal in the junk pile.")
            elif "Access Card" not in inv:
                say("Hint: The access card is in the locker on the catwalk. "
                    "Use your scrap metal on it.")
            elif not self._fuel_cell_inserted:
                if "Fuel Cell" in inv:
                    say("Hint: The pod's nav computer needs power before you can "
                        "launch. Use the fuel cell on the pod.")
                else:
                    say("Hint: The pod's nav computer needs power before you can "
                        "launch. There's a fuel cell in the engine room.")
            else:
                say("Hint: You have everything you need. Use the access card "
                    "on the pod's card reader — or just type 'enter pod'.")

        elif room in ("Escape Pod (Landed)", "Monolith Burger - Exterior") \
                and not self._hired:
            say("Hint: Head north into Monolith Burger. Pick up the application "
                "form at the counter and take it to the manager in the kitchen.")

        elif room == "Monolith Burger - Counter" and not self._hired:
            if "Application Form" not in inv:
                say("Hint: There's a job application form right here on the "
                    "counter. Pick it up, then take it to the manager in the kitchen.")
            else:
                say("Hint: You have the application. The manager is in the "
                    "kitchen to the east. Talk to him or give him the form.")

        elif room == "Monolith Burger - Counter" and not self._customer_talked:
            say("Hint: That disgusting customer at the counter looks like he "
                "knows something. Try talking to him.")

        elif room == "Monolith Burger - Kitchen" and not self._hired:
            say("Hint: The manager wants your application form. "
                "Give it to him or talk to him while holding it.")

        elif room == "Monolith Burger - Kitchen" and self._hired \
                and "Grease Trap Key" not in inv:
            say("Hint: There's a key on the counter labeled 'INCINERATOR OVERRIDE.' "
                "Pick it up — you'll need it to access the incinerator.")

        elif room == "Incinerator Chamber":
            if "Grease Trap Key" in inv:
                say("Hint: There's a control panel on the north wall with a keyhole. "
                    "You're holding the key. Put two and two together.")
            else:
                say("Hint: You need the grease trap key from the kitchen counter "
                    "to override the incinerator. Unfortunately, you don't have it. "
                    "This is going to be a problem.")

        elif room in ("Monolith Burger - Kitchen", "CEO Hallway") \
                and not self._flux_capacitor_retrieved:
            say("Hint: You survived the incinerator but forgot the flux capacitor! "
                "It's still in there on the east wall. Go back and get it.")

        elif not self._customer_talked:
            say("Hint: Have you talked to the disgusting customer at the counter? "
                "He seems to know things. Unpleasant things, but useful ones.")

        elif room == "CEO Hallway" and not self._ceo_distracted:
            if "Spatula" in inv:
                say("Hint: The CEO office door latch looks like it could be "
                    "jimmied open with something thin and flat. Use your spatula on it.")
            else:
                say("Hint: You need something thin and flat to jam the CEO office "
                    "door open. There's a spatula in the kitchen.")

        elif room == "CEO Office" and not self._ceo_distracted:
            if "Lunch Box" in inv:
                say("Hint: The CEO can't resist the smell of a Monolith Burger. "
                    "You're carrying one. Open the lunch box in here to distract him.")
            else:
                say("Hint: You need to distract the CEO. Something that smells "
                    "irresistible would do the trick. There's a lunch box in the junk pile.")

        elif room == "CEO Office" and self._ceo_distracted \
                and "Holding Cell Key" not in inv:
            say("Hint: The CEO is gone. His desk is right there. "
                "There's a key on it labeled 'HOLDING CELL.' Take it.")

        elif room == "Holding Cell" and not self._two_guys_freed:
            say("Hint: The Two Guys are locked in. You should have a key "
                "labeled 'HOLDING CELL' from the CEO's desk. Use it.")

        elif self._two_guys_freed and not self._two_guys_following:
            say("Hint: Something went wrong — the Two Guys should be following "
                "you. Try heading back to the escape pod.")

        elif self._two_guys_following and "Flux Capacitor" not in inv:
            say("Hint: The Two Guys are with you but you don't have the flux "
                "capacitor. It's in the incinerator chamber — go get it.")

        elif self._two_guys_following and "Flux Capacitor" in inv:
            say("Hint: You have everything! Head back to the escape pod "
                "to the south of Monolith Burger and use the flux capacitor.")

        else:
            say("Hint: Roger scratches his head. Even the hint system is confused. "
                "Try examining everything in the room and checking your inventory.")

    # ------------------------------------------------------------------
    # Save / Restore
    # ------------------------------------------------------------------

    SAVE_FILE = "sq7_save.dat"

    def _autosave(self):
        """Feature 4: silently save before dangerous situations."""
        try:
            with open(AUTOSAVE_FILE, "wb") as f:
                pickle.dump(self._game_state(), f)
        except Exception:
            pass  # Silent failure — don't interrupt gameplay

    def _game_state(self):
        """Return a dict of everything needed to reconstruct game state."""
        return {
            "room": self.player.room.name,
            "score": self.player.score,
            "inventory": [(i.name, i.aliases, i.description, i.takeable,
                           i.examine_description)
                          for i in self.player.inventory],
            "flags": {
                "_pod_launched":             self._pod_launched,
                "_oil_cleared":              self._oil_cleared,
                "_pipe_fixed":               self._pipe_fixed,
                "_locker_opened":            self._locker_opened,
                "_fuel_cell_inserted":       self._fuel_cell_inserted,
                "_hired":                    self._hired,
                "_incinerator_active":       self._incinerator_active,
                "_incinerator_turns":        self._incinerator_turns,
                "_flux_capacitor_retrieved": self._flux_capacitor_retrieved,
                "_customer_talked":          self._customer_talked,
                "_ceo_distracted":           self._ceo_distracted,
                "_two_guys_freed":           self._two_guys_freed,
                "_two_guys_following":       self._two_guys_following,
                "_bribed_cashier":           self._bribed_cashier,
                "_button_presses":           self._button_presses,
                "_ejected_by_ceo":           self._ejected_by_ceo,
                "_intercom_index":           self._intercom_index,
                "_next_intercom":            self._next_intercom,
                "_verbose":                  self._verbose,
            },
            # Per-room item lists (names only — we rebuild from flags on restore)
            "room_items": {
                key: [i.name for i in room.items]
                for key, room in self.rooms.items()
            },
        }

    def _restore_state(self, state):
        """Apply a saved state dict to the current game."""
        # Restore flags
        for attr, val in state["flags"].items():
            setattr(self, attr, val)

        # Restore player score
        self.player.score = state["score"]

        # Restore player inventory
        self.player.inventory = []
        for item_data in state["inventory"]:
            if len(item_data) == 5:
                name, aliases, desc, takeable, exam_desc = item_data
            else:
                name, aliases, desc, takeable = item_data
                exam_desc = None
            self.player.inventory.append(
                Item(name, aliases, desc, takeable, exam_desc)
            )

        # Restore player room
        target = self._find_room(state["room"])
        if target:
            self.player.room = target

        # Re-apply flag-driven side effects (exits, NPC lists, room items)
        self._reapply_flags()

    def _reapply_flags(self):
        """Re-derive all room exits and dynamic state from flags after a restore."""
        # Engine room ladder
        if self._pipe_fixed:
            self._engine_room.exits["up"] = "engine_room_catwalk"
        else:
            self._engine_room.exits.pop("up", None)

        # Oil slick
        if self._oil_cleared:
            self._engine_room.items = [
                i for i in self._engine_room.items if i.name != "Oil Slick"
            ]

        # Locker / access card on catwalk
        if self._locker_opened:
            self._catwalk.items = [
                i for i in self._catwalk.items if i.name != "Locker"
            ]
            # Add access card back if not in inventory and not already there
            inv_names = [i.name for i in self.player.inventory]
            catwalk_names = [i.name for i in self._catwalk.items]
            if "Access Card" not in inv_names and "Access Card" not in catwalk_names:
                self._catwalk.items.append(Item(
                    "Access Card", ["card", "access", "keycard"],
                    "A magnetic access card. Someone has written 'NOT A MASTER KEY' "
                    "on it in marker. They were lying."
                ))

        # Kitchen exits
        if self._hired:
            self._mb_kitchen.exits["north"] = "incinerator_chamber"
            self._mb_kitchen.exits["east"] = "ceo_hallway"

        # Incinerator exits + flux capacitor
        if not self._incinerator_active:
            if self._hired:
                self._incinerator.exits["south"] = "monolith_burger_kitchen"
        if not self._flux_capacitor_retrieved:
            flux_names = [i.name for i in self._incinerator.items]
            inv_names = [i.name for i in self.player.inventory]
            # Only add flux cap to incinerator if incinerator was already unlocked
            # and it hasn't been picked up
            if "Flux Capacitor" not in inv_names and "Flux Capacitor" not in flux_names:
                if not self._incinerator_active and self._hired:
                    self._incinerator.items.append(Item(
                        "Flux Capacitor", ["flux", "capacitor", "device", "part"],
                        "The flux capacitor. It glows faintly and hums with "
                        "contained temporal energy. Your pod needs this."
                    ))

        # CEO office
        if self._ceo_distracted:
            self._ceo_office.exits["north"] = "holding_cell"
            self._ceo_office.npcs = []
            key_names = [i.name for i in self._ceo_office.items]
            inv_names = [i.name for i in self.player.inventory]
            if "Holding Cell Key" not in inv_names and "Holding Cell Key" not in key_names:
                self._ceo_office.items.append(Item(
                    "Holding Cell Key",
                    ["holding", "cell", "key", "cellkey", "desk"],
                    "A key labeled 'HOLDING CELL.' Keychain shaped like a "
                    "tiny Monolith Burger."
                ))
        else:
            self._ceo_office.exits = {"west": "ceo_hallway"}

        # Two Guys
        if self._two_guys_freed:
            self._holding_cell.npcs = []
        if self._two_guys_following:
            pod = self.rooms.get("escape_pod_(landed)")
            if pod and not pod.get_npc("mark"):
                pod.npcs.append(NPC(
                    "Mark Crowe",
                    ["mark", "crowe", "tall", "guys"],
                    [
                        "'Hand us that flux capacitor and we'll have you flying!'",
                        "'Just give us the flux capacitor. Please.'",
                    ]
                ))
            if pod and not pod.get_npc("scott"):
                pod.npcs.append(NPC(
                    "Scott Murphy",
                    ["scott", "murphy", "short"],
                    [
                        "'The flux capacitor housing is standard XJ-7.'",
                        "'Just give us the flux capacitor. Please.'",
                    ]
                ))

    def cmd_save(self, tokens):
        slot = tokens[1] if len(tokens) > 1 else "1"
        filename = f"sq7_save_{slot}.dat"
        try:
            with open(filename, "wb") as f:
                pickle.dump(self._game_state(), f)
            say(f"Game saved to slot {slot}. "
                "Roger Wilco's progress has been preserved for posterity, "
                "or at least until you delete that file.")
        except Exception as e:
            say(f"Save failed: {e}. The universe doesn't want you to save.")

    def cmd_restore(self, tokens):
        slot = tokens[1] if len(tokens) > 1 else "1"
        filename = f"sq7_save_{slot}.dat"
        if not os.path.exists(filename):
            say(f"No save file found in slot {slot}. "
                "Roger has no past to return to. Only forward.")
            return
        try:
            with open(filename, "rb") as f:
                state = pickle.load(f)
            self._restore_state(state)
            say(f"Game restored from slot {slot}.")
            self.player.room.describe(game=self)
            self._play_room_music()
        except Exception as e:
            say(f"Restore failed: {e}. The save file may be corrupted, "
                "much like Roger's career prospects.")

    def cmd_quit(self, tokens):
        if self.sound:
            self.sound.shutdown()
        say("You quit. Roger Wilco wanders off into the cosmos, "
            "presumably to mop something.")
        sys.exit(0)

    # ------------------------------------------------------------------
    # Main loop
    # ------------------------------------------------------------------

    COMMANDS = {
        "look":      cmd_look,   "l":       cmd_look,
        "examine":   cmd_examine, "x":      cmd_examine,
        "take":      cmd_take,   "pick":    cmd_take,
        "drop":      cmd_drop,
        "inventory": cmd_inventory, "inv": cmd_inventory, "i": cmd_inventory,
        "go":        cmd_go,     "move":    cmd_go,   "walk": cmd_go,
        "use":       cmd_use,
        "enter":     cmd_enter,
        "give":      cmd_give,   "hand":    cmd_give,
        "talk":      cmd_talk,   "speak":   cmd_talk,
        "buy":       cmd_buy,
        "press":     cmd_press,
        "verbose":   cmd_verbose,
        "brief":     cmd_brief,
        "ascii":     cmd_ascii_on,  # default to 'on' for 'ascii' command
        "ascii_on":  cmd_ascii_on,
        "ascii_off": cmd_ascii_off,
        "ascii_show": cmd_ascii_show,
        "again":     None,       "g":       None,  # handled in process()
        "score":     cmd_score,
        "map":       cmd_map,
        "hint":      cmd_hint,
        "save":      cmd_save,
        "restore":   cmd_restore,
        "help":      cmd_help,   "?":       cmd_help,
        "quit":      cmd_quit,   "q":       cmd_quit, "exit": cmd_quit,
    }

    def process(self, raw):
        tokens = tokenize(raw)
        if not tokens:
            return
        # Feature 1: again/g — repeat last command
        if tokens[0] in ("again", "g"):
            if not self._last_command:
                say("There is no previous command to repeat.")
                return
            raw = self._last_command
            tokens = tokenize(raw)
            if not tokens:
                return
        else:
            self._last_command = raw
        if tokens[0] in DIRECTIONS:
            self.cmd_go(["go", DIRECTIONS[tokens[0]]])
            return
        if tokens[0] in ("get", "climb") and len(tokens) > 1 and tokens[1] == "in":
            self.cmd_enter(["enter"] + tokens[2:])
            return
        # "get" alone or "get <item>" -> take
        verb = tokens[0]
        if verb == "get" and (len(tokens) == 1 or tokens[1] != "in"):
            self.cmd_take(tokens)
            return
        handler = self.COMMANDS.get(verb)
        if handler:
            handler(self, tokens)
        else:
            say(f"I don't know how to '{raw.strip()}'. Try 'help'.")

    def tick(self):
        self.turn += 1
        if self.player.room.on_tick:
            self.player.room.on_tick()
        # Feature 9: intercom messages
        self._maybe_intercom()

    def run(self):
        if _ASCII_ART_AVAILABLE:
            print_title_screen()
        else:
            say(
                "SPACE QUEST 7: THE SMELL OF FEAR\n"
                "A text adventure in the spirit of Sierra's Space Quest series.\n"
                "Type 'help' for commands."
            )
        say(
            "You are Roger Wilco, Janitor First Class, Hero of the Galaxy, "
            "and chronic underachiever. Right now you are face-down in a "
            "pile of garbage on a derelict freighter. The universe is, "
            "as usual, entirely indifferent to your prior contributions."
        )
        self.player.room.describe(game=self)
        self._play_room_music()
        while True:
            print()
            try:
                raw = input("What do you do? > ").strip()
            except (EOFError, KeyboardInterrupt):
                print()
                self.cmd_quit([])
                break
            if raw:
                self.process(raw)
                self.tick()


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------

def main():
    game = Game()
    game.run()

if __name__ == "__main__":
    main()
