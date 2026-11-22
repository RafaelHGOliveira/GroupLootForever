-- Group Loot Forever: while an item is being rolled for in your group, a small panel
-- lists it and counts who picked Need, Greed, Disenchant, Transmog or Pass, and who has
-- not picked yet. Hover a count for the names, in class colours, each with its level.
--
-- Where the picks come from:
-- 1. The loot chat lines. Forever's GlobalStrings (build 1.60.1.70959, wago.tools) have
--    "|HlootHistory:%d|h[Loot]|h: %s has selected Need for: %s" and the like; the
--    patterns below are built from those globals, so another locale works too. Who can
--    roll is then the group, online, when the roll starts. Someone out of range gets no
--    roll and stays pending.
-- 2. C_LootHistory, the modern client's loot history (the "Waiting on:" list of the loot
--    rolls window). When it returns players for the drop, that list replaces the group.
-- Not confirmed in game (2026-11-22): what C_LootHistory returns on Forever, and whether
-- CANCEL_LOOT_ROLL fires when you pick or when the roll ends. So a row goes away on the
-- "won" or "Everyone passed" line, when the history names a winner, or when the roll time
-- runs out, never on CANCEL_LOOT_ROLL. /glf debug logs all of it.
--
-- Nothing here is secure code: the panel moves and updates in combat. Names and chat
-- text can be secret values on the modern client; those are skipped.
--
-- Text sits only on button font strings (SetText): on Forever a separate font string
-- stayed blank in Rogue Poison (2026-11-19), for a reason never found.

local addon = {}
GroupLootForever = addon

local ROW_H, ICON, PAD, GAP = 22, 20, 6, 4
local LOG_MAX = 1000
local TIMEOUT_EXTRA = 5 -- seconds past the roll time before a row is dropped anyway
local TEST_TIME = 30

local CATS = {
  { key = "pending", label = "Pending", color = "ffd100" },
  { key = "need", label = NEED or "Need", color = "40ff40" },
  { key = "greed", label = GREED or "Greed", color = "40c0ff" },
  { key = "de", label = ROLL_DISENCHANT or "Disenchant", color = "c080ff", optional = true },
  { key = "transmog", label = "Transmog", color = "ff80ff", optional = true },
  { key = "pass", label = PASS or "Pass", color = "b0b0b0" },
}
addon.CATS = CATS

local function secret(v) return issecretvalue ~= nil and issecretvalue(v) end

local function log(fmt, ...)
  if not (GroupLootForeverDB and GroupLootForeverDB.debug) then return end
  local args = { ... }
  for i = 1, select("#", ...) do
    local v = args[i]
    args[i] = secret(v) and "<secret>" or tostring(v):gsub("|", "||")
  end
  local line = format("%s %.2f " .. fmt, date("%H:%M:%S"), GetTime(), unpack(args, 1, select("#", ...)))
  local l = GroupLootForeverDB.log
  tinsert(l, line)
  while #l > LOG_MAX do tremove(l, 1) end
end

-- Chat lines. "done" ends the roll. Order matters: "Everyone passed on: %s" would also
-- match "%s passed on: %s", and "You passed on: %s" would match it with the name "You",
-- so the end lines go first, then your own lines, then everyone else's.
local LINES = {
  { "LOOT_ROLL_ALL_PASSED", "done", true },
  { "LOOT_ROLL_YOU_WON", "done", true },
  { "LOOT_ROLL_WON", "done" },
  { "LOOT_ROLL_YOU_WON_NO_SPAM_NEED", "done", true },
  { "LOOT_ROLL_YOU_WON_NO_SPAM_NEED_OFF_SPEC", "done", true },
  { "LOOT_ROLL_YOU_WON_NO_SPAM_GREED", "done", true },
  { "LOOT_ROLL_YOU_WON_NO_SPAM_DE", "done", true },
  { "LOOT_ROLL_YOU_WON_NO_SPAM_TRANSMOG", "done", true },
  { "LOOT_ROLL_WON_NO_SPAM_NEED", "done" },
  { "LOOT_ROLL_WON_NO_SPAM_NEED_OFF_SPEC", "done" },
  { "LOOT_ROLL_WON_NO_SPAM_GREED", "done" },
  { "LOOT_ROLL_WON_NO_SPAM_DE", "done" },
  { "LOOT_ROLL_WON_NO_SPAM_TRANSMOGRIFICATION", "done" },
  { "LOOT_ROLL_NEED_SELF", "need", true },
  { "LOOT_ROLL_NEED_SELF_OFF_SPEC", "need", true },
  { "LOOT_ROLL_GREED_SELF", "greed", true },
  { "LOOT_ROLL_DISENCHANT_SELF", "de", true },
  { "LOOT_ROLL_PASSED_SELF", "pass", true },
  { "LOOT_ROLL_PASSED_SELF_AUTO", "pass", true },
  { "LOOT_ROLL_NEED", "need" },
  { "LOOT_ROLL_GREED", "greed" },
  { "LOOT_ROLL_DISENCHANT", "de" },
  { "LOOT_ROLL_PASSED", "pass" },
  { "LOOT_ROLL_PASSED_AUTO", "pass" },
  { "LOOT_ROLL_PASSED_AUTO_FEMALE", "pass" },
}

-- "%s" and "%d" become captures; the player is the first "%s" (unless the line is your
-- own) and the item link is the last one.
local patterns
local function compile()
  patterns = {}
  for _, l in ipairs(LINES) do
    local fmt = _G[l[1]]
    if type(fmt) == "string" then
      local order = {}
      local p = fmt:gsub("%%([sd])", function(t) order[#order + 1] = t; return "\1" end)
      p = p:gsub("[%^%$%(%)%%%.%[%]%*%+%-%?]", "%%%0"):gsub("\1", "(.-)")
      local nameAt, linkAt
      for i, t in ipairs(order) do
        if t == "s" then nameAt = nameAt or i; linkAt = i end
      end
      tinsert(patterns, { pat = "^" .. p .. "$", cat = l[2], mine = l[3], nameAt = nameAt, linkAt = linkAt })
    end
  end
end

local function itemKey(link) return type(link) == "string" and link:match("item:(%d+)") or nil end

local function short(name)
  if type(name) ~= "string" or secret(name) then return nil end
  return Ambiguate and Ambiguate(name, "short") or name:match("^[^-]+")
end

-- Group member name -> unit.
local function units()
  local map, list = {}, {}
  if IsInRaid() then
    for i = 1, GetNumGroupMembers() do list[#list + 1] = "raid" .. i end
  else
    list[1] = "player"
    for i = 1, GetNumSubgroupMembers() do list[#list + 1] = "party" .. i end
  end
  for _, unit in ipairs(list) do
    local name = UnitName(unit)
    if name and not secret(name) then map[name] = unit end
  end
  return map
end

local rolls = {} -- active rolls, oldest first
addon.rolls = rolls
local refresh

local function finish(r, why)
  for i, x in ipairs(rolls) do
    if x == r then
      tremove(rolls, i)
      log("finish roll %s (%s)", r.id, why)
      refresh()
      return
    end
  end
end

-- Names in one category of a roll, sorted.
function addon.names(r, key)
  local list = {}
  for name in pairs(r.who) do
    if (r.choice[name] or "pending") == key then list[#list + 1] = name end
  end
  table.sort(list)
  return list
end

-- "Name (32)" with the name in its class colour.
function addon.describe(name, class, level)
  local color = class and RAID_CLASS_COLORS and RAID_CLASS_COLORS[class]
  local text = color and color.colorStr and ("|c" .. color.colorStr .. name .. "|r") or name
  return format("%s (%s)", text, (level and level > 0) and level or "??")
end

local function startRoll(id, rollTime)
  for _, r in ipairs(rolls) do
    if r.id == id then return r end
  end
  local link = GetLootRollItemLink(id)
  local texture, name, _, quality = GetLootRollItemInfo(id)
  local r = { id = id, link = link, key = itemKey(link), texture = texture, name = name,
    quality = quality, who = {}, choice = {}, class = {}, level = {} }
  for n, unit in pairs(units()) do
    if UnitIsConnected(unit) then
      r.who[n] = true
      r.class[n] = select(2, UnitClass(unit))
    end
  end
  tinsert(rolls, r)
  log("start roll %s %s time %s", id, link, rollTime)
  if type(rollTime) == "number" and rollTime > 0 then
    C_Timer.After(rollTime / 1000 + TIMEOUT_EXTRA, function() finish(r, "timeout") end)
  end
  refresh()
  return r
end
addon.startRoll = startRoll

local function onChat(msg)
  if type(msg) ~= "string" or secret(msg) then return end
  if not patterns then compile() end
  for _, p in ipairs(patterns) do
    local caps = { msg:match(p.pat) }
    if caps[1] then
      local key = itemKey(caps[p.linkAt])
      local who = p.mine and UnitName("player") or short(caps[p.nameAt])
      log("chat %s %s item %s", p.cat, who, key)
      for _, r in ipairs(rolls) do
        if r.key == key then
          if p.cat == "done" then finish(r, "chat"); return end
          -- Two rolls for the same item: the pick goes to the oldest one still open for
          -- this player.
          if who and not r.choice[who] then
            r.who[who], r.choice[who] = true, p.cat
            refresh()
            return
          end
        end
      end
      return
    end
  end
end
addon.onChat = onChat

-- Enum.EncounterLootDropRollState on the modern client: NeedMainSpec 0, NeedOffSpec 1,
-- Transmog 2, Greed 3, NoRoll 4 (not picked yet), Pass 5.
local STATES
local function states()
  local E = Enum and Enum.EncounterLootDropRollState or {}
  return { [E.NeedMainSpec or 0] = "need", [E.NeedOffSpec or 1] = "need",
    [E.Transmog or 2] = "transmog", [E.Greed or 3] = "greed", [E.Pass or 5] = "pass" }
end

local function onHistory(encounterID, lootListID)
  local H = C_LootHistory
  if not (H and H.GetSortedInfoForDrop) then return end
  local drop = H.GetSortedInfoForDrop(encounterID, lootListID)
  if type(drop) ~= "table" then log("history %s %s: no drop", encounterID, lootListID) return end
  local tag = tostring(encounterID) .. ":" .. tostring(lootListID)
  local infos = type(drop.rollInfos) == "table" and drop.rollInfos or {}
  log("history %s %s winner %s allPassed %s players %d", tag, drop.itemHyperlink,
    drop.winner and drop.winner.playerName, drop.allPassed, #infos)
  for _, info in ipairs(infos) do
    log("  %s %s state %s roll %s", info.playerName, info.playerClass, info.state, info.roll)
  end
  local r
  for _, x in ipairs(rolls) do
    if x.drop == tag then r = x break end
  end
  if not r then
    local key = itemKey(drop.itemHyperlink)
    for _, x in ipairs(rolls) do
      if not x.drop and x.key == key then r = x break end
    end
  end
  if not r then return end
  r.drop = tag
  if #infos > 0 then
    STATES = STATES or states()
    local who, choice = {}, {}
    for _, info in ipairs(infos) do
      local name = short(info.playerName)
      if name then
        who[name] = true
        if type(info.playerClass) == "string" then r.class[name] = info.playerClass end
        -- The chat line can arrive before the history catches up: keep that pick.
        choice[name] = STATES[info.state] or r.choice[name]
      end
    end
    r.who, r.choice = who, choice
  end
  if drop.winner or drop.allPassed then finish(r, "history") else refresh() end
end
addon.onHistory = onHistory

-- Panel -----------------------------------------------------------------------------

local panel = CreateFrame("Frame", "GroupLootForeverFrame", UIParent,
  BackdropTemplateMixin and "BackdropTemplate" or nil)
panel:Hide()
panel:SetFrameStrata("MEDIUM")
panel:SetClampedToScreen(true)
panel:SetMovable(true)
panel:EnableMouse(true)
panel:RegisterForDrag("LeftButton")
panel:SetScript("OnDragStart", panel.StartMoving)
panel:SetScript("OnDragStop", function(self)
  self:StopMovingOrSizing()
  local point, _, rel, x, y = self:GetPoint()
  GroupLootForeverDB.point = { point, rel, x, y }
end)
if panel.SetBackdrop then
  panel:SetBackdrop({ bgFile = "Interface\\Tooltips\\UI-Tooltip-Background",
    edgeFile = "Interface\\Tooltips\\UI-Tooltip-Border", edgeSize = 12,
    insets = { left = 3, right = 3, top = 3, bottom = 3 } })
  panel:SetBackdropColor(0, 0, 0, 0.8)
end
addon.panel = panel

local function place()
  local p = GroupLootForeverDB.point
  panel:ClearAllPoints()
  if p then panel:SetPoint(p[1], UIParent, p[2], p[3], p[4])
  else panel:SetPoint("TOP", UIParent, "TOP", 0, -260) end
end

local function hideTooltip() GameTooltip:Hide() end

local function showNames(self)
  local r, cat = self.roll, self.cat
  local names = addon.names(r, cat.key)
  if #names == 0 then return end
  GameTooltip:SetOwner(self, "ANCHOR_TOP")
  GameTooltip:AddLine(cat.label)
  local map = units()
  for _, name in ipairs(names) do
    local unit = map[name]
    local level = unit and UnitLevel(unit) or r.level[name]
    local class = r.class[name] or (unit and select(2, UnitClass(unit)))
    GameTooltip:AddLine(addon.describe(name, class, level))
  end
  GameTooltip:Show()
end

local function showItem(self)
  local r = self.roll
  if not r.link then return end
  GameTooltip:SetOwner(self, "ANCHOR_TOP")
  GameTooltip:SetHyperlink(r.link)
  GameTooltip:Show()
end

local function textButton(parent)
  local b = CreateFrame("Button", nil, parent)
  b:SetHeight(ROW_H)
  b:SetNormalFontObject("GameFontHighlightSmall")
  b:SetText(" ")
  b:SetScript("OnLeave", hideTooltip)
  return b
end

local rows = {}
addon.rows = rows

local function newRow(i)
  local row = CreateFrame("Frame", nil, panel)
  row:SetHeight(ROW_H)
  row:SetPoint("TOPLEFT", panel, "TOPLEFT", PAD, -PAD - (i - 1) * ROW_H)
  row.icon = row:CreateTexture(nil, "ARTWORK")
  row.icon:SetSize(ICON, ICON)
  row.icon:SetPoint("LEFT")
  row.item = textButton(row)
  row.item:SetPoint("LEFT", row.icon, "RIGHT", GAP, 0)
  row.item:SetScript("OnEnter", showItem)
  row.counts = {}
  for _, cat in ipairs(CATS) do
    local b = textButton(row)
    b.cat = cat
    b:SetScript("OnEnter", showNames)
    row.counts[cat.key] = b
  end
  rows[i] = row
  return row
end

local function fit(b)
  local fs = b:GetFontString()
  b:SetWidth((fs and fs:GetStringWidth() or 40) + 6)
  return b:GetWidth()
end

function refresh()
  if #rolls == 0 then panel:Hide() return end
  local width = 0
  for i, r in ipairs(rolls) do
    local row = rows[i] or newRow(i)
    row.roll, row.item.roll = r, r
    row.icon:SetTexture(r.texture)
    local q = ITEM_QUALITY_COLORS and ITEM_QUALITY_COLORS[r.quality or 1]
    row.item:SetText((q and q.hex or "") .. (r.name or "?") .. (q and "|r" or ""))
    local x = ICON + GAP + fit(row.item) + GAP
    for _, cat in ipairs(CATS) do
      local b = row.counts[cat.key]
      local n = #addon.names(r, cat.key)
      b.roll = r
      if cat.optional and n == 0 then
        b:Hide()
      else
        b:SetText(format("|cff%s%s %d|r", n > 0 and cat.color or "707070", cat.label, n))
        b:ClearAllPoints()
        b:SetPoint("LEFT", row, "LEFT", x, 0)
        x = x + fit(b) + GAP
        b:Show()
      end
    end
    width = math.max(width, x)
    row:Show()
  end
  for i = #rolls + 1, #rows do rows[i]:Hide() end
  for i = 1, #rolls do rows[i]:SetWidth(width) end
  panel:SetSize(width + 2 * PAD, #rolls * ROW_H + 2 * PAD)
  panel:Show()
end

-- /glf test: a made-up roll, to see and place the panel without a group.
local TEST = {
  { "Thrall", "SHAMAN", 34, "need" }, { "Jaina", "MAGE", 33, "greed" },
  { "Uther", "PALADIN", 35, "pass" }, { "Valeera", "ROGUE", 32 }, { "Rexxar", "HUNTER", 31 },
}
local function testRoll()
  local r = { id = "test", name = "Electrocutioner Leg", quality = 3,
    texture = "Interface\\Icons\\INV_Sword_04", who = {}, choice = {}, class = {}, level = {} }
  for _, t in ipairs(TEST) do
    r.who[t[1]], r.class[t[1]], r.level[t[1]], r.choice[t[1]] = true, t[2], t[3], t[4]
  end
  for _, x in ipairs(rolls) do
    if x.id == "test" then finish(x, "test again") break end
  end
  tinsert(rolls, r)
  C_Timer.After(TEST_TIME, function() finish(r, "test over") end)
  refresh()
end
addon.testRoll = testRoll

-- Events ----------------------------------------------------------------------------

local events = CreateFrame("Frame")
events:RegisterEvent("ADDON_LOADED")
events:SetScript("OnEvent", function(_, event, ...)
  if event == "ADDON_LOADED" then
    if ... ~= "GroupLootForever" then return end
    GroupLootForeverDB = GroupLootForeverDB or {}
    GroupLootForeverDB.log = {}
    place()
    for _, e in ipairs({ "START_LOOT_ROLL", "CANCEL_LOOT_ROLL", "CHAT_MSG_LOOT",
      "LOOT_HISTORY_UPDATE_DROP", "GROUP_ROSTER_UPDATE" }) do
      -- An event the client lacks would raise an error when registered.
      if not pcall(events.RegisterEvent, events, e) then log("no event %s", e) end
    end
    -- After a /reload in the middle of a roll.
    if GetActiveLootRollIDs then
      for _, id in ipairs(GetActiveLootRollIDs() or {}) do startRoll(id) end
    end
  elseif event == "START_LOOT_ROLL" then
    startRoll(...)
  elseif event == "CANCEL_LOOT_ROLL" then
    log("cancel roll %s", ...)
  elseif event == "CHAT_MSG_LOOT" then
    onChat(...)
  elseif event == "LOOT_HISTORY_UPDATE_DROP" then
    local ok, err = pcall(onHistory, ...)
    if not ok then log("history error %s", err) end
  elseif event == "GROUP_ROSTER_UPDATE" then
    if not IsInGroup() then
      for i = #rolls, 1, -1 do
        if rolls[i].id ~= "test" then tremove(rolls, i) end
      end
    end
    refresh()
  end
end)

SLASH_GROUPLOOTFOREVER1 = "/glf"
SlashCmdList.GROUPLOOTFOREVER = function(msg)
  msg = strtrim(strlower(msg or ""))
  local say = function(t) DEFAULT_CHAT_FRAME:AddMessage("|cff40c0ffGroup Loot Forever:|r " .. t) end
  if msg == "test" then
    testRoll()
    say(format("a test roll for %d seconds. Drag the panel to move it.", TEST_TIME))
  elseif msg == "reset" then
    GroupLootForeverDB.point = nil
    place()
    say("panel back in its place.")
  elseif msg == "debug" then
    GroupLootForeverDB.debug = not GroupLootForeverDB.debug
    say("debug log " .. (GroupLootForeverDB.debug and "on: /reload saves it." or "off."))
  else
    say("/glf test (show a test roll), /glf reset (panel position), /glf debug (log for bug reports).")
  end
end
