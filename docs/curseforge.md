*Who picked what, and who is still deciding.*

When an item drops in your group, the roll window only shows your own choice. Group Loot Forever adds a small panel that counts everyone's picks as they come in: how many chose Need, Greed or Pass, and how many have not picked yet. Hover a number to see who.

## At a glance

- **One line per item being rolled for:** the item, then **Pending**, **Need**, **Greed** and **Pass** counts. Disenchant and Transmog get a count too, once someone picks them.
- **Names on hover:** each name in its class colour, with the level in brackets, e.g. *Thrall (34)*.
- **Stays until the roll ends:** the panel does not close when you pick, so you can watch the rest of the group decide.
- **Works in combat**, and in any language: it reads the game's own loot messages.
- **Drag it anywhere.** The position is saved.

## Commands

- `/glf test`: show a made-up roll for 30 seconds, to see and place the panel without a group
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
