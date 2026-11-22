*Who picked what, and who is still deciding.*

When an item drops in your group, the roll window only shows your own choice. Group Loot Forever counts everyone's picks as they come in: how many chose Need, Greed or Pass, and how many have not picked yet. Hover to see who.

## At a glance

- **On the game's own roll window:** a number in the corner of the Need, Greed and Pass buttons, and **Pending N** beside the window.
- **Names on hover:** hover a button and its tooltip lists who picked it, each name in its class colour with the level in brackets, e.g. *Thrall (34)*.
- **After you pick:** the game closes its roll window, so the roll moves to a small panel with the same counts (Pending, Need, Greed, Pass) until it ends. You can watch the rest of the group decide.
- **Disenchant and Transmog** get a count too, once someone picks them.
- **Works in combat**, and in any language: it reads the game's own loot messages.
- **Drag it anywhere.** The position is saved.

## Commands

- `/glf test`: a made-up roll for 30 seconds on a copy of the game's roll window, to see it all without a group; click a button and the roll moves to the panel, as after a real pick
- `/glf reset`: put the panel back in its default place
- `/glf debug`: turn the debug log on or off

## FAQ

**Someone shows as pending but never picks.**
Players out of range of the loot get no roll. The addon counts everyone online in the group when the roll starts, so they stay pending until the roll ends, unless the game's loot history lists the real participants.

**Something looks wrong. What do I send?**
Type `/glf debug`, roll for some loot in a group, then `/reload`. Attach `WTF\Account\<account>\SavedVariables\GroupLootForever.lua` to a comment here.

## Supported versions

WoW Forever (1.60.1). This is a first version: feedback from real groups is welcome.

MIT license.
