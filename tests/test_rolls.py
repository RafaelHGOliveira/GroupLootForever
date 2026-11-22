# /// script
# requires-python = ">=3.10"
# dependencies = ["lupa"]
# ///
"""Loads GroupLootForever.lua against a stubbed WoW API, plays loot roll events and chat
lines, and checks the counts on the panel and the names in the tooltips.
Run: uv run tests/test_rolls.py [-v]

The chat strings are Forever's own (GlobalStrings, build 1.60.1.70959, wago.tools). What
C_LootHistory returns in game is a guess here (the retail shape) until a debug log shows it.
"""
import pathlib
import sys

try:
    from lupa import lua51 as L
except ImportError:
    import lupa as L

ADDON = pathlib.Path(__file__).resolve().parent.parent / "GroupLootForever.lua"
VERBOSE = "-v" in sys.argv

STUBS = r"""
format, tinsert, tremove, strlower = string.format, table.insert, table.remove, string.lower
unpack = unpack or table.unpack
function strtrim(s) return (s:gsub("^%s+", ""):gsub("%s+$", "")) end
date = os.date
function GetTime() return 0 end

LOOT_ROLL_PASSED = "|HlootHistory:%d|h[Loot]|h: %s passed on: %s"
LOOT_ROLL_ALL_PASSED = "|HlootHistory:%d|h[Loot]|h: Everyone passed on: %s"
LOOT_ROLL_WON = "|HlootHistory:%d|h[Loot]|h: %s won: %s"
LOOT_ROLL_YOU_WON = "|HlootHistory:%d|h[Loot]|h: You won: %s"
LOOT_ROLL_PASSED_SELF = "|HlootHistory:%d|h[Loot]|h: You passed on: %s"
LOOT_ROLL_GREED_SELF = "|HlootHistory:%d|h[Loot]|h: You have selected Greed for: %s"
LOOT_ROLL_NEED_SELF = "|HlootHistory:%d|h[Loot]|h: You have selected Need for: %s"
LOOT_ROLL_GREED = "|HlootHistory:%d|h[Loot]|h: %s has selected Greed for: %s"
LOOT_ROLL_NEED = "|HlootHistory:%d|h[Loot]|h: %s has selected Need for: %s"
LOOT_ROLL_YOU_WON_NO_SPAM_NEED = "|HlootHistory:%d|h[Loot]|h: You (Need - %d, Main-Spec) Won: %s"
LOOT_ROLL_YOU_WON_NO_SPAM_GREED = "|HlootHistory:%d|h[Loot]|h: You (Greed - %d) Won: %s"
LOOT_ROLL_WON_NO_SPAM_NEED = "|HlootHistory:%d|h[Loot]|h: %s (Need - %d, Main-Spec) Won: %s"
LOOT_ROLL_WON_NO_SPAM_GREED = "|HlootHistory:%d|h[Loot]|h: %s (Greed - %d) Won: %s"
LOOT_ROLL_PASSED_SELF_AUTO = "|HlootHistory:%d|h[Loot]|h: You automatically passed on: %s because you cannot loot that item."
LOOT_ROLL_PASSED_AUTO = "%s automatically passed on: %s because he cannot loot that item."
LOOT_ROLL_PASSED_AUTO_FEMALE = "%s automatically passed on: %s because she cannot loot that item."
LOOT_ROLL_DISENCHANT_SELF = "|HlootHistory:%d|h[Loot]|h: You have selected Disenchant for: %s"
LOOT_ROLL_DISENCHANT = "%s has selected Disenchant for: %s"
LOOT_ROLL_NEED_SELF_OFF_SPEC = "|HlootHistory:%d|h[Loot]|h: You have selected Need for: %s"
NEED, GREED, PASS, ROLL_DISENCHANT = "Need", "Greed", "Pass", "Disenchant"

RAID_CLASS_COLORS = {
  ROGUE = { colorStr = "fffff468" }, SHAMAN = { colorStr = "ff0070dd" },
  MAGE = { colorStr = "ff3fc7eb" }, PALADIN = { colorStr = "fff48cba" },
  HUNTER = { colorStr = "ffaad372" },
}
ITEM_QUALITY_COLORS = { [2] = { hex = "|cff1eff00" }, [3] = { hex = "|cff0070dd" } }

-- The group: unit -> { name, class, level, online }.
group = {}
raid = false
function IsInRaid() return raid end
function IsInGroup() return next(group) ~= nil end
function GetNumGroupMembers() local n = 0 for k in pairs(group) do n = n + 1 end return n end
function GetNumSubgroupMembers()
  local n = 0 for k in pairs(group) do if k:match("^party") then n = n + 1 end end return n
end
function UnitName(u) return group[u] and group[u][1] end
function UnitClass(u) return group[u] and group[u][2], group[u] and group[u][2] end
function UnitLevel(u) return group[u] and group[u][3] or 0 end
function UnitIsConnected(u) return group[u] and group[u][4] end
function Ambiguate(name) return (name:gsub("%-.*$", "")) end

items = {}
function link(id) return "|cff1eff00|Hitem:" .. id .. "::::::::32:::::|h[item" .. id .. "]|h|r" end
function GetLootRollItemLink(id) return items[id] and link(items[id]) end
function GetLootRollItemInfo(id) return "icon", items[id] and ("item" .. items[id]), 1, 2 end

timers = {}
C_Timer = { After = function(t, fn) tinsert(timers, { t = t, fn = fn }) end }
chat = {}
DEFAULT_CHAT_FRAME = { AddMessage = function(_, m) tinsert(chat, m) end }
SlashCmdList = {}

frames = {}
local M = {}
local function noop() end
local meta = { __index = function(_, k) return M[k] or noop end }
local function newFrame(parent)
  local f = setmetatable({ scripts = {}, shown = true, parent = parent, width = 0 }, meta)
  tinsert(frames, f)
  return f
end
function M:Show() self.shown = true end
function M:Hide() self.shown = false end
function M:IsShown() return self.shown end
function M:SetScript(what, fn) self.scripts[what] = fn end
function M:CreateTexture() return newFrame(self) end
function M:SetText(t) self.text = t; self.fs = rawget(self, "fs") or newFrame(self); self.fs.text = t end
function M:GetText() return rawget(self, "text") end
function M:GetFontString() return rawget(self, "fs") end
function M:GetStringWidth() return #(rawget(self, "text") or "") * 5 end
function M:SetWidth(w) self.width = w end
function M:GetWidth() return self.width end
function M:SetSize(w, h) self.width, self.height = w, h end
function M:GetPoint() return "TOP", UIParent, "TOP", 10, -20 end
UIParent = newFrame()
function CreateFrame(_, name, parent)
  local f = newFrame(parent)
  if name then _G[name] = f end
  if name == nil and parent == nil then events = f end
  return f
end
function M:RegisterEvent(e) local r = rawget(self, "registered") or {}; r[e] = true; self.registered = r end

GameTooltip = setmetatable({ lines = {} }, meta)
function GameTooltip:SetOwner() self.lines = {} end
function GameTooltip:AddLine(t) tinsert(self.lines, t) end

-- History: [encounter:list] -> drop table.
history = {}
C_LootHistory = { GetSortedInfoForDrop = function(e, l) return history[e .. ":" .. l] end }

function fire(event, ...) events.scripts.OnEvent(events, event, ...) end

function visible(f)
  while f do
    if not rawget(f, "shown") then return false end
    f = rawget(f, "parent")
  end
  return true
end

-- The panel's rows, as { item text, { "Need 1", ... } } for the shown ones.
function shownRows()
  local out = {}
  for _, row in ipairs(GroupLootForever.rows) do
    if visible(row) then
      local counts = {}
      for _, cat in ipairs(GroupLootForever.CATS) do
        local b = row.counts[cat.key]
        if visible(b) then tinsert(counts, (b.text:gsub("|c%x%x%x%x%x%x%x%x", ""):gsub("|r", ""))) end
      end
      tinsert(out, { row.item.text, counts })
    end
  end
  return out
end

-- Tooltip lines when hovering one count of one row.
function hover(rowIndex, key)
  GameTooltip.lines = {}
  local b = GroupLootForever.rows[rowIndex].counts[key]
  b.scripts.OnEnter(b)
  return GameTooltip.lines
end
"""

PARTY = r"""
group = {
  player = { "Eraluna", "ROGUE", 32, true },
  party1 = { "Thrall", "SHAMAN", 34, true },
  party2 = { "Jaina", "MAGE", 33, true },
  party3 = { "Uther", "PALADIN", 35, true },
  party4 = { "Rexxar", "HUNTER", 31, false },
}
"""


def run(script, setup=PARTY):
    lua = L.LuaRuntime(unpack_returned_tuples=True)
    lua.execute(STUBS)
    lua.execute(setup)
    lua.globals().GroupLootForeverDB = None
    lua.execute(ADDON.read_text(encoding="utf-8"))
    lua.execute('fire("ADDON_LOADED", "GroupLootForever")')
    return lua.execute(script)


def table(v):
    """Lua table (possibly nested) to Python lists."""
    if hasattr(v, "values"):
        return [table(x) for x in v.values()]
    return v


CASES = []


def case(name):
    def deco(fn):
        CASES.append((name, fn))
        return fn
    return deco


@case("a new roll: everyone online in the group is pending, the offline one is not")
def _():
    rows = table(run('items[1] = 100; fire("START_LOOT_ROLL", 1, 60000); return shownRows()'))
    assert rows == [["|cff1eff00item100|r", ["Pending 4", "Need 0", "Greed 0", "Pass 0"]]], rows


@case("picks from chat: someone's Need, your Greed, an automatic pass")
def _():
    rows = table(run(r'''
      items[1] = 100; fire("START_LOOT_ROLL", 1, 60000)
      fire("CHAT_MSG_LOOT", format(LOOT_ROLL_NEED, 7, "Thrall", link(100)))
      fire("CHAT_MSG_LOOT", format(LOOT_ROLL_GREED_SELF, 7, link(100)))
      fire("CHAT_MSG_LOOT", format(LOOT_ROLL_PASSED_AUTO_FEMALE, "Jaina", link(100)))
      return shownRows()'''))
    assert rows[0][1] == ["Pending 1", "Need 1", "Greed 1", "Pass 1"], rows


@case("hover a count: class-coloured names with the level in brackets, sorted")
def _():
    lines = table(run(r'''
      items[1] = 100; fire("START_LOOT_ROLL", 1, 60000)
      fire("CHAT_MSG_LOOT", format(LOOT_ROLL_NEED, 7, "Uther", link(100)))
      fire("CHAT_MSG_LOOT", format(LOOT_ROLL_NEED, 7, "Thrall-Stormrage", link(100)))
      return { hover(1, "need"), hover(1, "pending"), hover(1, "pass") }'''))
    need, pending, passed = lines
    assert need == ["Need", "|cff0070ddThrall|r (34)", "|cfff48cbaUther|r (35)"], need
    assert pending == ["Pending", "|cfffff468Eraluna|r (32)", "|cff3fc7ebJaina|r (33)"], pending
    assert passed == [], passed  # a zero count shows no tooltip


@case("Disenchant shows up only once someone picks it")
def _():
    rows = table(run(r'''
      items[1] = 100; fire("START_LOOT_ROLL", 1, 60000)
      fire("CHAT_MSG_LOOT", format(LOOT_ROLL_DISENCHANT, "Jaina", link(100)))
      return shownRows()'''))
    assert rows[0][1] == ["Pending 3", "Need 0", "Greed 0", "Disenchant 1", "Pass 0"], rows


@case("'Everyone passed' ends the roll and is not read as a player named Everyone")
def _():
    rows = table(run(r'''
      items[1] = 100; fire("START_LOOT_ROLL", 1, 60000)
      fire("CHAT_MSG_LOOT", format(LOOT_ROLL_ALL_PASSED, 7, link(100)))
      return { shownRows(), GroupLootForeverFrame.shown }'''))
    assert rows == [[], False], rows


@case("'You passed on' counts as your pass, not a player named You")
def _():
    lines = table(run(r'''
      items[1] = 100; fire("START_LOOT_ROLL", 1, 60000)
      fire("CHAT_MSG_LOOT", format(LOOT_ROLL_PASSED_SELF, 7, link(100)))
      return hover(1, "pass")'''))
    assert lines == ["Pass", "|cfffff468Eraluna|r (32)"], lines


@case("two rolls for the same item: a second pick by the same player goes to the second")
def _():
    rows = table(run(r'''
      items[1], items[2] = 100, 100
      fire("START_LOOT_ROLL", 1, 60000); fire("START_LOOT_ROLL", 2, 60000)
      fire("CHAT_MSG_LOOT", format(LOOT_ROLL_NEED, 7, "Thrall", link(100)))
      fire("CHAT_MSG_LOOT", format(LOOT_ROLL_GREED, 8, "Thrall", link(100)))
      return shownRows()'''))
    assert [r[1][1:3] for r in rows] == [["Need 1", "Greed 0"], ["Need 0", "Greed 1"]], rows


@case("a 'won' line ends the oldest roll for that item; other rolls stay")
def _():
    rows = table(run(r'''
      items[1], items[2] = 100, 200
      fire("START_LOOT_ROLL", 1, 60000); fire("START_LOOT_ROLL", 2, 60000)
      fire("CHAT_MSG_LOOT", format(LOOT_ROLL_WON_NO_SPAM_NEED, 7, "Thrall", 87, link(100)))
      return shownRows()'''))
    assert [r[0] for r in rows] == ["|cff1eff00item200|r"], rows


@case("CANCEL_LOOT_ROLL keeps the row: it may only mean you picked")
def _():
    rows = table(run(r'''
      items[1] = 100; fire("START_LOOT_ROLL", 1, 60000); fire("CANCEL_LOOT_ROLL", 1)
      return shownRows()'''))
    assert len(rows) == 1, rows


@case("the roll time runs out: the row goes away")
def _():
    out = table(run(r'''
      items[1] = 100; fire("START_LOOT_ROLL", 1, 60000)
      local t = timers[1].t; timers[1].fn()
      return { t, GroupLootForeverFrame.shown }'''))
    assert out == [65, False], out


@case("loot history players replace the group, and its states are the picks")
def _():
    rows = table(run(r'''
      items[1] = 100; fire("START_LOOT_ROLL", 1, 60000)
      fire("CHAT_MSG_LOOT", format(LOOT_ROLL_GREED, 7, "Uther", link(100)))
      history["5:2"] = { itemHyperlink = link(100), rollInfos = {
        { playerName = "Thrall", playerClass = "SHAMAN", state = 0 },
        { playerName = "Jaina", playerClass = "MAGE", state = 4 },
        { playerName = "Uther", playerClass = "PALADIN", state = 4 },
        { playerName = "Eraluna", playerClass = "ROGUE", state = 5 } } }
      fire("LOOT_HISTORY_UPDATE_DROP", 5, 2)
      return shownRows()'''))
    # Uther's Greed came by chat before the history caught up: kept.
    assert rows[0][1] == ["Pending 1", "Need 1", "Greed 1", "Pass 1"], rows


@case("loot history with a winner ends the roll")
def _():
    shown = run(r'''
      items[1] = 100; fire("START_LOOT_ROLL", 1, 60000)
      history["5:2"] = { itemHyperlink = link(100), winner = { playerName = "Thrall" }, rollInfos = {} }
      fire("LOOT_HISTORY_UPDATE_DROP", 5, 2)
      return GroupLootForeverFrame.shown''')
    assert shown is False, shown


@case("a broken history call is logged, not raised")
def _():
    out = table(run(r'''
      GroupLootForeverDB.debug = true
      C_LootHistory.GetSortedInfoForDrop = function() error("boom") end
      items[1] = 100; fire("START_LOOT_ROLL", 1, 60000)
      fire("LOOT_HISTORY_UPDATE_DROP", 5, 2)
      return GroupLootForeverDB.log'''))
    assert any("history error" in l for l in out), out


@case("ordinary loot lines and other items change nothing")
def _():
    rows = table(run(r'''
      items[1] = 100; fire("START_LOOT_ROLL", 1, 60000)
      fire("CHAT_MSG_LOOT", "You receive loot: " .. link(100) .. ".")
      fire("CHAT_MSG_LOOT", format(LOOT_ROLL_NEED, 7, "Thrall", link(999)))
      return shownRows()'''))
    assert rows[0][1] == ["Pending 4", "Need 0", "Greed 0", "Pass 0"], rows


@case("/glf test shows a made-up roll with levels from its own table, solo")
def _():
    out = table(run(r'''
      SlashCmdList.GROUPLOOTFOREVER("test")
      return { shownRows(), hover(1, "pending") }''', setup="group = {}"))
    rows, pending = out
    assert rows == [["|cff0070ddElectrocutioner Leg|r", ["Pending 2", "Need 1", "Greed 1", "Pass 1"]]], rows
    assert pending == ["Pending", "|cffaad372Rexxar|r (31)", "|cfffff468Valeera|r (32)"], pending


@case("leaving the group clears the rolls")
def _():
    shown = run(r'''
      items[1] = 100; fire("START_LOOT_ROLL", 1, 60000)
      group = {}; fire("GROUP_ROSTER_UPDATE")
      return GroupLootForeverFrame.shown''')
    assert shown is False, shown


@case("the panel position is saved on drag and restored by /glf reset")
def _():
    out = table(run(r'''
      GroupLootForeverFrame.scripts.OnDragStop(GroupLootForeverFrame)
      local saved = GroupLootForeverDB.point and GroupLootForeverDB.point[3]
      SlashCmdList.GROUPLOOTFOREVER("reset")
      return { saved, GroupLootForeverDB.point == nil }'''))
    assert out == [10, True], out


failed = 0
for name, fn in CASES:
    try:
        fn()
        if VERBOSE:
            print("ok  ", name)
    except Exception as e:  # noqa: BLE001
        failed += 1
        print("FAIL", name, "-", repr(e))
print("ALL OK" if not failed else f"{failed} FAILED")
sys.exit(1 if failed else 0)
