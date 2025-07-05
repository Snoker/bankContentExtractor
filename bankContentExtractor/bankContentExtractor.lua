local function SaveBankContents(data)
    MyBankData = data or {}
end

local function PrintBankContents()
    if not BankFrame or not BankFrame:IsVisible() then
        ChatFrame1:AddMessage("|cffff0000[bankContentExtractor] Please open the bank before scanning.|r")
        return
    end

    local allItems = {}
    local charName = UnitName("player") or "Unknown"

    for bag = -1, 10 do
        local bagSlots = GetContainerNumSlots(bag)
        if bagSlots and bagSlots > 0 then
            for slot = 1, bagSlots do
                local itemLink = GetContainerItemLink(bag, slot)
                if itemLink then
                    local _, itemCount = GetContainerItemInfo(bag, slot)
                    table.insert(allItems, {charName, bag, itemLink, itemCount or 1})
                end
            end
        end
    end

    ChatFrame1:AddMessage("---- Writing bank data to variable ----")
    SaveBankContents(allItems)
    ChatFrame1:AddMessage("---- Bank information successfully saved ----")
end

-- Initialization frame
local initFrame = CreateFrame("Frame")
initFrame:RegisterEvent("PLAYER_LOGIN")
initFrame:SetScript("OnEvent", function(self, event)
    -- Register /bagscan command
    SLASH_BAGSCAN1 = "/bagscan" --no use atm (since runs on bank open, however I would like to run this for the future for bags only (not only when bank is open))
    SlashCmdList["BAGSCAN"] = function()
        PrintBankContents()
    end

    -- Register BANKFRAME_OPENED
    local bankEventFrame = CreateFrame("Frame")
    bankEventFrame:RegisterEvent("BANKFRAME_OPENED")
    bankEventFrame:SetScript("OnEvent", function()
        PrintBankContents()
    end)
end)
