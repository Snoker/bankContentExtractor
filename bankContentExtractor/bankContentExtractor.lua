local function SaveBankContents(data)
    MyBankData = data or {}  -- Save the passed-in table or empty table
end

local function PrintBankContents()
    -- Check if the bank is open
    if not BankFrame or not BankFrame:IsVisible() then
        ChatFrame1:AddMessage("|cffff0000[bankContentExtractor] Please open the bank before scanning.|r")
        return
    end

    local allItems = {}
    local charName = UnitName("player") or "Unknown"

    -- Scan bank bags -1 (main bank) to 10
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

SLASH_BAGSCAN1 = "/bagscan"
SlashCmdList["BAGSCAN"] = function()
    PrintBankContents()
end
