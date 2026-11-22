# Group Loot Forever

<p align="center"><img src="Media/logo-256.png" width="200" alt="Group Loot Forever logo"></p>

A [WoW Forever](https://www.wowhead.com/forever) addon for group loot rolls. While an
item is rolled for, a small panel lists it and counts who picked Need, Greed or Pass,
and who has not picked yet. Hover a count for the names, in class colours, each with
its level.

```
┌───────────────────────────────────────────────────────────────┐
│ [icon] Electrocutioner Leg  Pending 2  Need 1  Greed 1  Pass 1 │
└───────────────────────────────────────────────────────────────┘
                                  hover "Pending 2":
                                  Pending
                                  Rexxar (31)
                                  Valeera (32)
```

Disenchant and Transmog get a count too, once someone picks them. The panel stays
after you pick, until the roll is over, and it works in combat.

## Install

Copy the `GroupLootForever` folder to
`World of Warcraft\_forever_\Interface\AddOns\GroupLootForever`, then log in or `/reload`.

## Commands

| Command | |
|---|---|
| `/glf test` | show a made-up roll for 30 seconds, to see the panel without a group |
| `/glf reset` | put the panel back in its place (drag it to move it) |
| `/glf debug` | turn the debug log on or off |

## How it knows

Each pick is read from the loot lines in chat ("Thrall has selected Need for: ..."), in
the game's own wording, so other languages work too. Who can roll is the group, online,
when the roll starts. The game's loot history, when it lists the players of a drop,
replaces that list and adds Transmog.

Someone out of range gets no roll. Unless the loot history says otherwise, they show as
pending until the roll ends.

## Debug log

Tick it with `/glf debug`, roll for something and `/reload`. The log is in
`WTF\Account\<account>\SavedVariables\GroupLootForever.lua`.

## License

MIT. See [LICENSE](LICENSE).
