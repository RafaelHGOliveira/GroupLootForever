# /// script
# requires-python = ">=3.10"
# dependencies = ["lupa"]
# ///
"""Loads GroupLootForever.lua against a stubbed WoW API, plays loot roll events and chat
lines, and checks the counts on the game's roll frame and the names in the tooltips.
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
-- A widget method (CamelCase) the stub lacks is a no-op; a missing data field is nil, as in
-- the game, so `frame.someField` checks in the addon see the truth.
local meta = { __index = function(_, k)
  if M[k] ~= nil then return M[k] end
  if type(k) == "string" and k:match("^%u") then return noop end
end }
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
function M:GetPoint()
  local p = rawget(self, "point")
  if p then return p[1], p[2], p[3], p[4], p[5] end
  return "TOP", UIParent, "TOP", 10, -20
end
UIParent = newFrame()
-- The game's templates this client has; CreateFrame with another one raises an error.
-- Forever has no GroupLootFrameTemplate (seen in game, 2026-11-22).
templates = {}
local function rollFrame(f)
  f.LootButtonContainer = newFrame(f)
  for _, k in ipairs(KEYS) do
    local b = newFrame(f.LootButtonContainer)
    b.key = k
    b.scripts.OnEnter = function(self) GameTooltip:SetOwner(self); GameTooltip:AddLine(k) end
    b.scripts.OnClick = function() error("the game's own click on a made-up roll") end
    f.LootButtonContainer[k] = b
  end
  f.scripts.OnShow = function() error("the game's own OnShow on a made-up roll") end
  return f
end
KEYS = { "NeedButton", "GreedButton", "PassButton", "TransmogButton" }
function CreateFrame(_, name, parent, template)
  if template and not templates[template] then error("no template " .. template) end
  local f = newFrame(parent)
  if name then _G[name] = f end
  if name == nil and parent == nil then events = f end
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
function M:GetObjectType() return "Frame" end
function M:GetNumPoints() return rawget(self, "point") and 1 or 0 end
function M:SetPoint(p, rel, rp, x, y) self.point = { p, rel, rp, x, y } end
function M:ClearAllPoints() self.point = nil end

GameTooltip = setmetatable({ lines = {} }, meta)
function GameTooltip:SetOwner(owner) self.owner = owner; self.lines = {} end
function GameTooltip:IsOwned(owner) return rawget(self, "owner") == owner end
function GameTooltip:AddLine(t) tinsert(self.lines, t) end

-- The game's roll frame, Mainline layout: hidden until a roll opens it. Each button's own
-- OnEnter shows a tooltip with the button's name, as the game does.
rollFrame(CreateFrame("Frame", "GroupLootFrame1", UIParent)).shown = false
GroupLootFrame1.scripts.OnShow = nil
function GroupLootFrame1:GetCenter() return 640, 213 end
function GroupLootFrame1:GetBottom() return 180 end
function M:GetEffectiveScale() return 1 end
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
-- The pending count on the game's frame, or nil when hidden.
function pendingLabel()
  for _, f in ipairs(frames) do
    if rawget(f, "parent") == rf() and rawget(f, "cat") and visible(f) then
      return (f.text:gsub("|c%x%x%x%x%x%x%x%x", ""):gsub("|r", ""))
    end
  end
end
-- What the pending count hangs on: inside the frame, never outside its edge.
function pendingAnchor()
  for _, f in ipairs(frames) do
    if rawget(f, "parent") == rf() and rawget(f, "cat") then return f.point[2] end
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

-- Shown and with a place on screen: in the game a frame anchored to a frame with no points
-- (GroupLootContainer before any roll) has no rect and is not drawn.
function drawn(f)
  if not visible(f) then return false end
  local p = rawget(f, "point")
  while p and type(p[2]) == "table" and p[2] ~= UIParent do
    if p[2]:GetNumPoints() == 0 then return false end
    p = rawget(p[2], "point")
  end
  return true
end

-- Each active roll as { item name, { "Need 1", ... } }: the counts the roll frame shows,
-- with Disenchant and Transmog only once someone picks them.
function shownRows()
  local out = {}
  for _, r in ipairs(GroupLootForever.rolls) do
    local counts = {}
    for _, cat in ipairs(GroupLootForever.CATS) do
      local n = #GroupLootForever.names(r, cat.key)
      if not cat.optional or n > 0 then tinsert(counts, cat.label .. " " .. n) end
    end
    tinsert(out, { r.name, counts })
  end
  return out
end

-- Tooltip lines when hovering the pending count on the game's frame.
function hoverPending()
  for _, f in ipairs(frames) do
    if rawget(f, "parent") == rf() and rawget(f, "cat") then
      GameTooltip.lines = {}
      f.scripts.OnEnter(f)
      return GameTooltip.lines
    end
  end
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
    lua.execute("GroupLootForeverDB = GroupLootForeverDB_seed")  # saved variables: nil unless a case seeds them
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
    assert rows == [["item100", ["Pending 4", "Need 0", "Greed 0", "Pass 0"]]], rows


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
      items[1] = 100; fire("START_LOOT_ROLL", 1, 60000); openFrame(1)
      fire("CHAT_MSG_LOOT", format(LOOT_ROLL_NEED, 7, "Uther", link(100)))
      fire("CHAT_MSG_LOOT", format(LOOT_ROLL_NEED, 7, "Thrall-Stormrage", link(100)))
      return { enter("NeedButton"), hoverPending(), enter("PassButton") }'''))
    need, pending, passed = lines
    assert need == ["NeedButton", "|cff0070ddThrall|r (34)", "|cfff48cbaUther|r (35)"], need
    assert pending == ["Pending", "|cfffff468Eraluna|r (32)", "|cff3fc7ebJaina|r (33)"], pending
    assert passed == ["PassButton"], passed  # nobody passed: only the game's own line


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
      return shownRows()'''))
    assert rows == [], rows


@case("'You passed on' counts as your pass, not a player named You")
def _():
    lines = table(run(r'''
      items[1] = 100; fire("START_LOOT_ROLL", 1, 60000); openFrame(1)
      fire("CHAT_MSG_LOOT", format(LOOT_ROLL_PASSED_SELF, 7, link(100)))
      return enter("PassButton")'''))
    assert lines == ["PassButton", "|cfffff468Eraluna|r (32)"], lines


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
    assert [r[0] for r in rows] == ["item200"], rows


@case("CANCEL_LOOT_ROLL keeps the roll: it may only mean you picked")
def _():
    rows = table(run(r'''
      items[1] = 100; fire("START_LOOT_ROLL", 1, 60000); fire("CANCEL_LOOT_ROLL", 1)
      return shownRows()'''))
    assert len(rows) == 1, rows


@case("the roll time runs out: the roll goes away")
def _():
    out = table(run(r'''
      items[1] = 100; fire("START_LOOT_ROLL", 1, 60000)
      for _, t in ipairs(timers) do
        if t.t > 0 then t.fn(); return { t.t, #shownRows() } end
      end'''))
    assert out == [65, 0], out


@case("the game's frame open: numbers on its buttons, pending left of Need")
def _():
    out = table(run(r'''
      items[1] = 100; fire("START_LOOT_ROLL", 1, 60000); openFrame(1)
      fire("CHAT_MSG_LOOT", format(LOOT_ROLL_NEED, 7, "Thrall", link(100)))
      fire("CHAT_MSG_LOOT", format(LOOT_ROLL_NEED, 7, "Uther", link(100)))
      fire("CHAT_MSG_LOOT", format(LOOT_ROLL_PASSED, 7, "Jaina", link(100)))
      return { badge("NeedButton") or "-", badge("GreedButton") or "-", badge("PassButton") or "-",
        badge("TransmogButton") or "-", pendingLabel() or "-",
        pendingAnchor() == GroupLootFrame1.LootButtonContainer.NeedButton }'''))
    assert out == [2, "-", 1, "-", "1", True], out


@case("hovering the game's Need button adds the names under its own tooltip")
def _():
    lines = table(run(r'''
      items[1] = 100; fire("START_LOOT_ROLL", 1, 60000); openFrame(1)
      fire("CHAT_MSG_LOOT", format(LOOT_ROLL_NEED, 7, "Thrall", link(100)))
      return { enter("NeedButton"), enter("GreedButton") }'''))
    assert lines == [["NeedButton", "|cff0070ddThrall|r (34)"], ["GreedButton"]], lines


@case("you pick, the game closes its frame: nothing of the addon shows, the roll stays counted")
def _():
    out = table(run(r'''
      items[1] = 100; fire("START_LOOT_ROLL", 1, 60000); openFrame(1)
      fire("CHAT_MSG_LOOT", format(LOOT_ROLL_GREED_SELF, 7, link(100)))
      closeFrame()
      return { shownRows(), badge("GreedButton") or "-", pendingLabel() or "-", GroupLootForeverFrame == nil }'''))
    rows, greed, pending, nopanel = out
    assert rows[0][1] == ["Pending 3", "Need 0", "Greed 1", "Pass 0"], rows
    assert (greed, pending, nopanel) == ("-", "-", True), out


@case("the frame reused for another roll shows that roll's counts")
def _():
    out = table(run(r'''
      items[1], items[2] = 100, 200
      fire("START_LOOT_ROLL", 1, 60000); fire("START_LOOT_ROLL", 2, 60000)
      fire("CHAT_MSG_LOOT", format(LOOT_ROLL_NEED, 7, "Thrall", link(100)))
      openFrame(2)
      return { badge("NeedButton") or "-", #shownRows() }'''))
    assert out == ["-", 2], out


@case("CANCEL_ALL_LOOT_ROLLS ends every roll")
def _():
    shown = run(r'''
      items[1], items[2] = 100, 200
      fire("START_LOOT_ROLL", 1, 60000); fire("START_LOOT_ROLL", 2, 60000)
      fire("CANCEL_ALL_LOOT_ROLLS")
      return #shownRows()''')
    assert shown == 0, shown


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
      return #shownRows()''')
    assert shown == 0, shown


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
        badge("PassButton") or "-", pendingLabel() or "-", enter("NeedButton") }''', setup="group = {}"))
    shown, need, greed, passed, pending, tip = out
    assert (shown, need, greed, passed, pending) == (True, 1, 1, 1, "2"), out
    assert tip == ["Need", "|cff0070ddThrall|r (34)"], tip


@case("/glf test: a click on the copy closes it, like a pick; the roll stays until the test ends")
def _():
    out = table(run(r'''
      SlashCmdList.GROUPLOOTFOREVER("test")
      local b = GroupLootForeverTestFrame.LootButtonContainer.GreedButton
      b.scripts.OnClick(b)
      return { GroupLootForeverTestFrame.shown, shownRows() }''', setup="group = {}"))
    shown, rows = out
    assert shown is False, out
    assert rows == [["Electrocutioner Leg", ["Pending 2", "Need 1", "Greed 1", "Pass 1"]]], rows


@case("/glf test without GroupLootFrame1 to copy: says so")
def _():
    out = table(run(r'''
      local said
      DEFAULT_CHAT_FRAME = { AddMessage = function(_, t) said = t end }
      SlashCmdList.GROUPLOOTFOREVER("test")
      return { said }''', setup="group = {}; GroupLootFrame1 = nil"))
    assert "no roll frame" in out[0], out


@case("the copy is a clone: the same keys, not the game's scripts, not this addon's own parts")
def _():
    out = table(run(r'''
      items[1] = 100; fire("START_LOOT_ROLL", 1, 60000); openFrame(1); closeFrame()
      SlashCmdList.GROUPLOOTFOREVER("test")
      local f = GroupLootForeverTestFrame
      local b = f.LootButtonContainer.NeedButton
      local ownParts = 0
      for _, x in ipairs(frames) do
        if rawget(x, "glfOwn") and rawget(x, "parent") == b then ownParts = ownParts + 1 end
      end
      return { f ~= GroupLootFrame1, b ~= GroupLootFrame1.LootButtonContainer.NeedButton,
        f.LootButtonContainer.TransmogButton.shown, ownParts }''', setup="group = {}"))
    # One number on the copy's Need button: its own, not also the one cloned from the real frame.
    assert out == [True, True, False, 1], out

@case("/glf dump logs the real roll frame and the copy (debug on)")
def _():
    out = table(run(r'''
      GroupLootForeverDB.debug = true
      SlashCmdList.GROUPLOOTFOREVER("test")
      SlashCmdList.GROUPLOOTFOREVER("dump")
      return GroupLootForeverDB.log''', setup="group = {}"))
    assert any(" dump GroupLootFrame1.LootButtonContainer" in l for l in out), out
    assert any(" dump GroupLootForeverTestFrame.LootButtonContainer" in l for l in out), out

@case("/glf test over: the copy closes and the roll is gone")
def _():
    out = table(run(r'''
      SlashCmdList.GROUPLOOTFOREVER("test")
      for _, t in ipairs(timers) do if t.t == 30 then t.fn() end end
      return { GroupLootForeverTestFrame.shown, #shownRows() }''', setup="group = {}"))
    assert out == [False, 0], out

@case("leaving the group clears the rolls")
def _():
    shown = run(r'''
      items[1] = 100; fire("START_LOOT_ROLL", 1, 60000)
      group = {}; fire("GROUP_ROSTER_UPDATE")
      return #shownRows()''')
    assert shown == 0, shown


@case("roll frame position: container without anchor -> bottom centre guess, and drawn")
def _():
    out = table(run(r'''
      GroupLootContainer:Hide()
      SlashCmdList.GROUPLOOTFOREVER("test")
      local f = GroupLootForeverTestFrame
      local b = f.LootButtonContainer.GreedButton
      local t, copyDrawn = f.point, drawn(f)
      return { t[1], t[2] == UIParent, t[3], t[4], t[5], copyDrawn }''',
        setup="group = {}; GroupLootContainer = CreateFrame('Frame', nil, UIParent)"))
    assert out == ["BOTTOM", True, "BOTTOM", 0, 200, True], out


@case("roll frame position: a real roll frame seen -> saved, and the copy goes there")
def _():
    out = table(run(r'''
      items[1] = 100; fire("START_LOOT_ROLL", 1, 60000); openFrame(1); closeFrame()
      SlashCmdList.GROUPLOOTFOREVER("test")
      local t = GroupLootForeverTestFrame.point
      return { GroupLootForeverDB.rollAt, t[3], t[4], t[5] }'''))
    assert out == [[640, 180], "BOTTOMLEFT", 640, 180], out


@case("roll frame position: the container once it has an anchor")
def _():
    out = table(run(r'''
      function GroupLootContainer:GetNumPoints() return 1 end
      SlashCmdList.GROUPLOOTFOREVER("test")
      local t = GroupLootForeverTestFrame.point
      return { t[1], t[2] == GroupLootContainer, t[3] }''',
        setup="group = {}; GroupLootContainer = CreateFrame('Frame', nil, UIParent)"))
    assert out == ["BOTTOM", True, "BOTTOM"], out

@case("the removed panel's saved position is dropped at load")
def _():
    out = run(r'''return GroupLootForeverDB.point == nil''',
        setup=PARTY + "GroupLootForeverDB_seed = { point = { 'TOP', 'TOP', 10, -20 } }")
    assert out is True, out


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
