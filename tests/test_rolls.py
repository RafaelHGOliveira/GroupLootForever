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
-- Show and Hide run OnShow / OnHide (the script, then a hook) when the state changes.
local function run(self, what)
  local sc = rawget(self, "scripts"); if sc and sc[what] then sc[what](self) end
  local h = rawget(self, "hooks"); if h and h[what] then h[what](self) end
end
function M:Show() if not rawget(self, "shown") then self.shown = true; run(self, "OnShow") end end
function M:Hide() if rawget(self, "shown") then self.shown = false; run(self, "OnHide") end end
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
-- The game's templates this client has; CreateFrame with another one raises an error.
templates = { GroupLootFrameTemplate = true }
local function rollFrame(f)
  f.LootButtonContainer = {}
  for _, k in ipairs(KEYS) do
    local b = newFrame(f)
    b.key = k
    b.scripts.OnEnter = function(self) GameTooltip:SetOwner(self); GameTooltip:AddLine(k) end
    b.scripts.OnClick = function() error("the game's own click on a made-up roll") end
    f.LootButtonContainer[k] = b
  end
  f.scripts.OnShow = function() error("the game's own OnShow on a made-up roll") end
end
KEYS = { "NeedButton", "GreedButton", "PassButton", "TransmogButton" }
function CreateFrame(_, name, parent, template)
  if template and not templates[template] then error("no template " .. template) end
  local f = newFrame(parent)
  if name then _G[name] = f end
  if name == nil and parent == nil then events = f end
  if template == "GroupLootFrameTemplate" then rollFrame(f) end
  return f
end
function M:HasScript() return true end
function M:GetChildren()
  local out = {}
  for _, f in ipairs(frames) do if rawget(f, "parent") == self then tinsert(out, f) end end
  return unpack(out)
end
function M:RegisterEvent(e) local r = rawget(self, "registered") or {}; r[e] = true; self.registered = r end
function M:HookScript(what, fn) local h = rawget(self, "hooks") or {}; h[what] = fn; self.hooks = h end
function M:GetFrameLevel() return 1 end

GameTooltip = setmetatable({ lines = {} }, meta)
function GameTooltip:SetOwner(owner) self.owner = owner; self.lines = {} end
function GameTooltip:IsOwned(owner) return rawget(self, "owner") == owner end
function GameTooltip:AddLine(t) tinsert(self.lines, t) end

-- The game's roll frame, Mainline layout: hidden until a roll opens it. Each button's own
-- OnEnter shows a tooltip with the button's name, as the game does.
CreateFrame("Frame", "GroupLootFrame1", UIParent, "GroupLootFrameTemplate").shown = false
GroupLootFrame1.scripts.OnShow = nil
function openFrame(id) GroupLootFrame1.rollID = id; GroupLootFrame1:Show() end
function closeFrame() GroupLootFrame1:Hide() end
-- The roll frame the helpers below look at.
function rf() return rollFrameUnderTest or GroupLootFrame1 end
-- The number on a button of the game's frame, or nil when hidden.
function badge(k)
  local b = rf().LootButtonContainer[k]
  for _, f in ipairs(frames) do
    if rawget(f, "parent") == b and f ~= rawget(b, "fs") and visible(f) then return f.text end
  end
end
-- "Pending N" beside the game's frame, or nil when hidden.
function pendingLabel()
  for _, f in ipairs(frames) do
    if rawget(f, "parent") == rf() and rawget(f, "cat") and visible(f) then
      return (f.text:gsub("|c%x%x%x%x%x%x%x%x", ""):gsub("|r", ""))
    end
  end
end
-- Hover a button of the game's frame: its own OnEnter, then the hooked one.
function enter(k)
  local b = rf().LootButtonContainer[k]
  GameTooltip.lines, GameTooltip.owner = {}, nil
  b.scripts.OnEnter(b)
  local h = rawget(b, "hooks"); if h and h.OnEnter then h.OnEnter(b) end
  return GameTooltip.lines
end

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
      for _, t in ipairs(timers) do
        if t.t > 0 then t.fn(); return { t.t, GroupLootForeverFrame.shown } end
      end'''))
    assert out == [65, False], out


@case("the game's frame open: numbers on its buttons, Pending beside it, no panel row")
def _():
    out = table(run(r'''
      items[1] = 100; fire("START_LOOT_ROLL", 1, 60000); openFrame(1)
      fire("CHAT_MSG_LOOT", format(LOOT_ROLL_NEED, 7, "Thrall", link(100)))
      fire("CHAT_MSG_LOOT", format(LOOT_ROLL_NEED, 7, "Uther", link(100)))
      fire("CHAT_MSG_LOOT", format(LOOT_ROLL_PASSED, 7, "Jaina", link(100)))
      return { badge("NeedButton") or "-", badge("GreedButton") or "-", badge("PassButton") or "-",
        badge("TransmogButton") or "-", pendingLabel() or "-", #shownRows(), GroupLootForeverFrame.shown }'''))
    assert out == [2, "-", 1, "-", "Pending 1", 0, False], out


@case("hovering the game's Need button adds the names under its own tooltip")
def _():
    lines = table(run(r'''
      items[1] = 100; fire("START_LOOT_ROLL", 1, 60000); openFrame(1)
      fire("CHAT_MSG_LOOT", format(LOOT_ROLL_NEED, 7, "Thrall", link(100)))
      return { enter("NeedButton"), enter("GreedButton") }'''))
    assert lines == [["NeedButton", "|cff0070ddThrall|r (34)"], ["GreedButton"]], lines


@case("you pick, the game closes its frame: the roll moves to the panel")
def _():
    out = table(run(r'''
      items[1] = 100; fire("START_LOOT_ROLL", 1, 60000); openFrame(1)
      fire("CHAT_MSG_LOOT", format(LOOT_ROLL_GREED_SELF, 7, link(100)))
      closeFrame()
      return { shownRows(), badge("GreedButton") or "-", pendingLabel() or "-" }'''))
    rows, greed, pending = out
    assert rows[0][1] == ["Pending 3", "Need 0", "Greed 1", "Pass 0"], rows
    assert (greed, pending) == ("-", "-"), out


@case("the frame reused for another roll shows that roll's counts")
def _():
    out = table(run(r'''
      items[1], items[2] = 100, 200
      fire("START_LOOT_ROLL", 1, 60000); fire("START_LOOT_ROLL", 2, 60000)
      fire("CHAT_MSG_LOOT", format(LOOT_ROLL_NEED, 7, "Thrall", link(100)))
      openFrame(2)
      return { badge("NeedButton") or "-", #shownRows() }'''))
    assert out == ["-", 1], out


@case("CANCEL_ALL_LOOT_ROLLS ends every roll")
def _():
    shown = run(r'''
      items[1], items[2] = 100, 200
      fire("START_LOOT_ROLL", 1, 60000); fire("START_LOOT_ROLL", 2, 60000)
      fire("CANCEL_ALL_LOOT_ROLLS")
      return GroupLootForeverFrame.shown''')
    assert shown is False, shown


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


@case("/glf test opens a copy of the game's roll frame with the counts on it, solo")
def _():
    out = table(run(r'''
      SlashCmdList.GROUPLOOTFOREVER("test")
      rollFrameUnderTest = GroupLootForeverTestFrame
      return { GroupLootForeverTestFrame.shown, badge("NeedButton") or "-", badge("GreedButton") or "-",
        badge("PassButton") or "-", pendingLabel() or "-", #shownRows(), enter("NeedButton") }''', setup="group = {}"))
    shown, need, greed, passed, pending, rows, tip = out
    assert (shown, need, greed, passed, pending, rows) == (True, 1, 1, 1, "Pending 2", 0), out
    assert tip == ["Need", "|cff0070ddThrall|r (34)"], tip


@case("/glf test: a click on the copy closes it, like a pick, and the roll moves to the panel")
def _():
    out = table(run(r'''
      SlashCmdList.GROUPLOOTFOREVER("test")
      local b = GroupLootForeverTestFrame.LootButtonContainer.GreedButton
      b.scripts.OnClick(b)
      return { GroupLootForeverTestFrame.shown, shownRows() }''', setup="group = {}"))
    shown, rows = out
    assert shown is False, out
    assert rows == [["|cff0070ddElectrocutioner Leg|r", ["Pending 2", "Need 1", "Greed 1", "Pass 1"]]], rows


@case("/glf test without the game's template: the made-up roll goes to the panel")
def _():
    out = table(run(r'''
      SlashCmdList.GROUPLOOTFOREVER("test")
      return { shownRows(), hover(1, "pending") }''', setup="group = {}; templates = {}"))
    rows, pending = out
    assert rows == [["|cff0070ddElectrocutioner Leg|r", ["Pending 2", "Need 1", "Greed 1", "Pass 1"]]], rows
    assert pending == ["Pending", "|cffaad372Rexxar|r (31)", "|cfffff468Valeera|r (32)"], pending


@case("/glf test over: the copy closes and the roll is gone")
def _():
    out = table(run(r'''
      SlashCmdList.GROUPLOOTFOREVER("test")
      for _, t in ipairs(timers) do if t.t == 30 then t.fn() end end
      return { GroupLootForeverTestFrame.shown, GroupLootForeverFrame.shown }''', setup="group = {}"))
    assert out == [False, False], out

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
