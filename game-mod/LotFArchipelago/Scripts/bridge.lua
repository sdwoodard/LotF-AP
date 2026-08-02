local Protocol = require("protocol")
local State = require("state")

local Bridge = {
    version = "0.2.2",
    protocol_version = 7,
    session = nil,
    ready = false,
    markers = {},
    pickup_guids = {},
    prepared_items = {},
    prepared_pickups = {},
    prepared_pickup_guids = {},
    items = {},
    placements = {},
    goal = nil,
    goal_reported = false,
    grants = {},
    restores = {},
    restored_ids = {},
    restore_invoked = {},
    kills = {},
    hooks = {},
    elapsed_ms = 0,
    last_hook_attempt_ms = -2000,
    last_death_ms = -5000,
    last_grant_ms = 0,
    last_pickup_scan_ms = -1000,
    last_offline_attempt_ms = -2000,
    offline_notice_emitted = false,
    last_player_name = nil,
    load_epoch = 0,
    active_cursor = 0,
    active_recovery = nil,
    pending_presentation = nil,
    pending_presentation_location = nil,
    presentation_expires_ms = 0,
    pending_suppression = nil,
    pending_suppression_identity = nil,
    pending_suppression_pickup = nil,
    suppression_expires_ms = 0,
    unmapped_pickups = {},
    error_times = {},
    archipelago_icon = nil,
    icon_load_attempted = false,
    icon_lookup_depth = 0,
    count_warning_reported = false,
    pickup_notification_registered = false,
    pickup_registry_reported = false,
    asset_classes = {},
    asset_lookup_errors = {},
    asset_catalog_reported = false,
    preserved_pickups = {
        -- Defiled Sepulchre tutorial Throwing Stone. This must remain vanilla
        -- so the player can knock down hanging corpses before or without a
        -- client connection.
        B21D92B8406214F0AEAF6B9B239BB661 = "tutorial Throwing Stone",
    },
    preserved_pickups_reported = {},
    delivery_delay = 1000,
    death_link = false,
    boot_id = tostring(os.time()) .. "-" .. tostring(math.random(100000, 999999)),
    replacement_asset = "/Game/Blueprints/Data/Equipment/Items/Usables/VigorStones/ITM_CON_VigorStone_01.ITM_CON_VigorStone_01_C",
}

local function now_ms()
    return Bridge.elapsed_ms
end

local function log(message)
    print("[LotF AP] " .. message .. "\n")
    if Bridge.session then
        Protocol.emit("LOG", Bridge.session, message)
    end
end

local function report_error(message)
    local previous = Bridge.error_times[message]
    if previous and Bridge.elapsed_ms - previous < 30000 then
        return
    end
    Bridge.error_times[message] = Bridge.elapsed_ms
    print("[LotF AP] ERROR: " .. message .. "\n")
    if Bridge.session then
        Protocol.emit("ERROR", Bridge.session, message)
    end
end

local function enforce_offline_mode()
    local ok, settings = pcall(function()
        return FindFirstOf("HexGameUserSettings")
    end)
    if not ok or not settings or not settings:IsValid() then
        return
    end

    local status_ok, online = pcall(function()
        return settings:IsOnlineModeEnabled()
    end)
    if status_ok and not online then
        if not Bridge.offline_notice_emitted then
            Bridge.offline_notice_emitted = true
            log("Confirmed the game online-mode setting is disabled")
        end
        return
    end

    local changed = pcall(function()
        settings:SetOnlineModeEnabled(false)
    end)
    pcall(function()
        settings:SetCrossplayEnabled(false)
    end)
    pcall(function()
        settings:SetAllowInvasionsEnabled(false)
    end)
    pcall(function()
        settings:ApplySettings(false)
    end)
    pcall(function()
        settings:SaveSettings()
    end)
    if changed and not Bridge.offline_notice_emitted then
        Bridge.offline_notice_emitted = true
        log("Disabled the game online-mode setting for Archipelago play")
    end
end

local function reset(session)
    Bridge.session = session
    Bridge.ready = false
    Bridge.markers = {}
    Bridge.pickup_guids = {}
    Bridge.prepared_items = {}
    Bridge.prepared_pickups = {}
    Bridge.prepared_pickup_guids = {}
    Bridge.items = {}
    Bridge.placements = {}
    Bridge.server_checked = {}
    Bridge.goal = nil
    Bridge.goal_reported = false
    Bridge.grants = {}
    Bridge.restores = {}
    Bridge.restored_ids = {}
    Bridge.restore_invoked = {}
    Bridge.kills = {}
    Bridge.death_link = false
    Bridge.active_cursor = 0
    Bridge.active_recovery = nil
    Bridge.pending_presentation = nil
    Bridge.pending_presentation_location = nil
    Bridge.pending_suppression = nil
    Bridge.pending_suppression_identity = nil
    Bridge.pending_suppression_pickup = nil
    Bridge.unmapped_pickups = {}
    Bridge.preserved_pickups_reported = {}
    Bridge.error_times = {}
    Bridge.last_player_name = nil
end

local function object_name(value)
    if value == nil then
        return nil
    end
    if type(value) == "string" then
        return value
    end
    local ok, name = pcall(function()
        if value:IsValid() then
            return value:GetFullName()
        end
        return nil
    end)
    if ok then
        return name
    end
    return nil
end

local function normalize_guid(value)
    if value == nil then
        return nil
    end
    local text = string.upper(tostring(value))
    -- GetStringId normally returns four groups of eight hexadecimal digits.
    -- Candidate scanning also accepts braces and conventional GUID grouping.
    for candidate in string.gmatch(text, "[%x%-{}]+") do
        local compact = string.gsub(candidate, "[^0-9A-F]", "")
        if #compact == 32 then
            return compact
        end
    end
    return nil
end

local function unwrap(parameter)
    local ok, value = pcall(function()
        return parameter:get()
    end)
    if ok then
        return value
    end
    return parameter
end

local function marker_in_name(name)
    if not name then
        return nil, nil
    end
    for marker, row in pairs(Bridge.markers) do
        if string.find(name, marker, 1, true) then
            return marker, row
        end
    end
    return nil, nil
end

local function marker_for_value(value)
    value = unwrap(value)
    local name = object_name(value)
    local prepared = name and Bridge.prepared_items[name] or nil
    if prepared then
        return prepared.marker, prepared.row, true
    end
    local marker, row = marker_in_name(name)
    if row then
        return marker, row, false
    end
    if not value then
        return nil, nil, false
    end
    -- Reading the reflected fields is safer than speculatively invoking
    -- methods on arbitrary hook parameters. The latter can enter invalid
    -- native thunks in UE4SS when the value is not an inventory item.
    for _, property in ipairs({"ItemData", "ItemDataClass"}) do
        local ok, nested = pcall(function()
            return value[property]
        end)
        if ok then
            marker, row = marker_in_name(object_name(unwrap(nested)))
            if row then
                return marker, row, true
            end
        end
    end
    return nil, nil, false
end

local function find_class(path)
    if not path or path == "" then
        return nil
    end
    local cached = Bridge.asset_classes[path]
    if cached and cached:IsValid() then
        return cached
    end

    local function accept(object)
        if object and object:IsValid() then
            Bridge.asset_classes[path] = object
            return object
        end
        return nil
    end

    local object = accept(StaticFindObject(path))
    if object then
        return object
    end

    local package_path = string.gsub(path, "%.[^%.]+_C$", "")
    local package_leaf = string.match(package_path, "/([^/]+)$")
    local load_errors = {}
    for _, load_path in ipairs({package_path .. "." .. tostring(package_leaf), package_path, path}) do
        local load_ok, loaded = pcall(function()
            return LoadAsset(load_path)
        end)
        if not load_ok then
            table.insert(load_errors, load_path .. ": " .. tostring(loaded))
        end
        object = accept(StaticFindObject(path))
        if object then
            return object
        end
        -- Some UE4SS builds return the generated class directly from
        -- LoadAsset instead of requiring a follow-up lookup.
        object = accept(loaded)
        if object then
            local is_class = false
            pcall(function()
                is_class = object:IsClass()
            end)
            if is_class then
                return object
            end
            Bridge.asset_classes[path] = nil
        end
    end
    local short_name = string.match(path, "%.([^%.]+)$")
    if short_name then
        for _, class_name in ipairs({"BlueprintGeneratedClass", "Class"}) do
            local found_ok, found = pcall(function()
                return FindObject(class_name, short_name)
            end)
            if not found_ok then
                table.insert(load_errors, class_name .. ": " .. tostring(found))
            end
            if found_ok then
                object = accept(found)
                if object then
                    return object
                end
            end
        end
    end
    Bridge.asset_lookup_errors[path] = table.concat(load_errors, " | ")
    return nil
end

local function suppress_parameter(parameter)
    local replacement = find_class(Bridge.replacement_asset)
    if not replacement then
        return false
    end
    local ok = pcall(function()
        parameter:set(replacement)
    end)
    return ok
end

local function validate_item_assets()
    local missing = {}
    local count = 0
    local replacement = find_class(Bridge.replacement_asset)
    if not replacement then
        table.insert(missing, "pickup replacement")
    end
    for item_id, row in pairs(Bridge.items) do
        count = count + 1
        if not find_class(row.asset) then
            if #missing < 8 then
                table.insert(missing, tostring(item_id) .. " (" .. tostring(row.name) .. ")")
            end
        end
    end
    if #missing > 0 then
        local detail = Bridge.asset_lookup_errors[Bridge.replacement_asset]
        local suffix = detail and detail ~= "" and ("; lookup detail: " .. detail) or ""
        report_error("Could not resolve required retail item classes: " .. table.concat(missing, ", ") .. suffix)
        return false
    end
    if not Bridge.asset_catalog_reported then
        Bridge.asset_catalog_reported = true
        log("Resolved pickup replacement and " .. tostring(count) .. " Archipelago item classes")
    end
    return true
end

local function suppress_data_parameter(parameter)
    local replacement = find_class(Bridge.replacement_asset)
    if not replacement then
        return false
    end
    local replacement_data = replacement
    pcall(function()
        replacement_data = replacement:GetDefaultObject()
    end)
    return pcall(function()
        parameter:set(replacement_data)
    end)
end

local function suppress_inventory_item(value)
    value = unwrap(value)
    if not value then
        return false
    end
    local replacement = find_class(Bridge.replacement_asset)
    if not replacement then
        return false
    end
    local replacement_data = replacement
    pcall(function()
        replacement_data = replacement:GetDefaultObject()
    end)
    local class_ok = pcall(function()
        value:SetItemDataClass(replacement)
    end)
    local data_ok = pcall(function()
        value:SetItemData(replacement_data)
    end)
    pcall(function()
        value:SetStock(1)
    end)
    return class_ok or data_ok
end

local function presentation_for_row(row)
    if not row or not row.location then
        return nil
    end
    return Bridge.placements[tostring(row.location)]
end

local function set_pending_presentation(row)
    Bridge.pending_presentation = presentation_for_row(row)
    Bridge.pending_presentation_location = row and row.location or nil
    Bridge.presentation_expires_ms = now_ms() + 5000
end

local function record_row(row, identity)
    set_pending_presentation(row)
    if row.location and row.location > 0 and not State.is_checked(Bridge.session, row.location) then
        State.mark_checked(Bridge.session, row.location)
        Protocol.emit("CHECK", Bridge.session, row.location)
        log("Checked location " .. tostring(row.location) .. " from " .. tostring(identity))
    end
end

local function observe_parameter(parameter)
    if not Bridge.ready or not Bridge.session then
        return
    end
    local value = unwrap(parameter)
    local _marker, row, inventory_item = marker_for_value(value)
    if row then
        set_pending_presentation(row)
        local suppressed = not row.suppress
            or (inventory_item and suppress_inventory_item(value))
            or (not inventory_item and suppress_parameter(parameter))
        if suppressed then
            record_row(row, _marker)
        else
            report_error("Could not suppress marker " .. tostring(_marker) .. "; use the Safe First Seed preset for this build")
        end
    end
end

local function observe_call(context, ...)
    observe_parameter(context)
    for index = 1, select("#", ...) do
        observe_parameter(select(index, ...))
    end
end

local function pickup_identity(context)
    local pickup = unwrap(context)
    if not pickup then
        return nil
    end
    for _, property in ipairs({"LOTF2SerializationComponent", "SerializationComponent"}) do
        local ok, component = pcall(function()
            return pickup[property]
        end)
        component = ok and unwrap(component) or nil
        if component then
            local string_ok, string_id = pcall(function()
                return component:GetStringId()
            end)
            local guid = string_ok and normalize_guid(string_id) or nil
            if guid then
                return guid
            end
        end
    end
    return normalize_guid(object_name(pickup))
end

local function pickup_inventory_item(pickup)
    local ok, inventory_item = pcall(function()
        return pickup:GetInventoryItem()
    end)
    inventory_item = ok and unwrap(inventory_item) or nil
    if inventory_item and object_name(inventory_item) then
        return inventory_item
    end
    return nil
end

local function prepare_pickup(pickup)
    pickup = unwrap(pickup)
    if not pickup or not object_name(pickup) then
        return nil, nil, nil
    end
    local guid = pickup_identity(pickup)
    if guid and Bridge.preserved_pickups[guid] then
        return guid, nil, nil
    end
    local row = guid and Bridge.pickup_guids[guid] or nil
    local marker = nil
    local inventory_item = pickup_inventory_item(pickup)
    if not row and inventory_item then
        marker, row = marker_for_value(inventory_item)
    end
    if not row then
        if guid and not Bridge.unmapped_pickups[guid] then
            Bridge.unmapped_pickups[guid] = true
            log("Observed unmapped pickup GUID " .. guid)
        end
        return guid, nil, nil
    end

    local pickup_name = object_name(pickup)
    Bridge.prepared_pickups[pickup_name] = row
    local item_name = object_name(inventory_item)
    if not inventory_item or not item_name then
        return guid, row, nil
    end
    Bridge.prepared_items[item_name] = {
        marker = marker or ("AP_GUID_" .. guid),
        row = row,
    }
    local preparation_key = guid or pickup_name
    if row.suppress and Bridge.prepared_pickup_guids[preparation_key] ~= item_name then
        if suppress_inventory_item(inventory_item) then
            Bridge.prepared_pickup_guids[preparation_key] = item_name
            if marker then
                log("Prepared randomized pickup marker " .. marker)
            else
                log("Prepared randomized pickup GUID " .. guid .. " (" .. tostring(row.retail_row) .. ")")
            end
        else
            report_error("Could not prepare randomized pickup " .. tostring(marker or guid))
        end
    end
    return guid, row, inventory_item
end

local function prepare_loaded_pickups()
    local ok, subsystem = pcall(function()
        return FindFirstOf("HexObjectTrackingSubsystem")
    end)
    if not ok or not subsystem or not subsystem:IsValid() then
        return 0
    end
    local array_ok, pickups = pcall(function()
        return subsystem.RegisteredPickups
    end)
    if not array_ok or not pickups then
        return 0
    end
    local count = 0
    local iterated = pcall(function()
        pickups:ForEach(function(_index, element)
            local pickup = unwrap(element)
            if pickup and object_name(pickup) then
                count = count + 1
                pcall(prepare_pickup, pickup)
            end
        end)
    end)
    if not iterated then
        return 0
    end
    if count > 0 and not Bridge.pickup_registry_reported then
        Bridge.pickup_registry_reported = true
        log("Pickup registry active with " .. tostring(count) .. " loaded pickups")
    end
    return count
end

local function register_pickup_notifications()
    if Bridge.pickup_notification_registered then
        return true
    end
    local ok = pcall(function()
        NotifyOnNewObject("/Script/LOTF2.Pickup", function(pickup)
            if Bridge.ready and Bridge.session then
                pcall(prepare_pickup, pickup)
            end
        end)
    end)
    if ok then
        Bridge.pickup_notification_registered = true
        log("Watching newly streamed pickup actors")
        return true
    end
    return false
end

local function observe_pickup(context)
    if not Bridge.ready or not Bridge.session then
        return
    end
    local pickup = unwrap(context)
    local guid, row, inventory_item = prepare_pickup(pickup)
    local preserved = guid and Bridge.preserved_pickups[guid] or nil
    if preserved then
        if not Bridge.preserved_pickups_reported[guid] then
            Bridge.preserved_pickups_reported[guid] = true
            log("Preserved vanilla " .. preserved .. " at pickup GUID " .. guid)
        end
        return
    end
    local marker = nil
    if not row and inventory_item then
        marker, row = marker_for_value(inventory_item)
    end
    if not row then
        return
    end


    local identity = guid and ("pickup GUID " .. guid .. " (" .. tostring(row.retail_row) .. ")")
        or ("pickup marker " .. tostring(marker))
    set_pending_presentation(row)
    if not row.suppress then
        record_row(row, identity)
        return
    end

    Bridge.pending_suppression = row
    Bridge.pending_suppression_identity = identity
    Bridge.pending_suppression_pickup = object_name(pickup)
    Bridge.suppression_expires_ms = now_ms() + 1000

    -- Most pre-placed pickups already own their UInventoryItem before
    -- TryTakePickup enters the inventory component. Mutating that instance is
    -- the earliest and most reliable way to keep the vanilla item out.
    if inventory_item and not suppress_inventory_item(inventory_item) then
        report_error("Could not suppress vanilla inventory item for " .. identity)
    end
end

local function observe_interaction(_component, context, ...)
    if not Bridge.ready or not Bridge.session then
        return
    end
    local interaction = unwrap(context)
    local ok, pickup = pcall(function()
        return interaction:GetInteractableObject()
    end)
    pickup = ok and unwrap(pickup) or nil
    if pickup then
        observe_pickup(pickup)
    end
end

local function pending_suppression()
    if Bridge.pending_suppression and now_ms() <= Bridge.suppression_expires_ms then
        return Bridge.pending_suppression
    end
    Bridge.pending_suppression = nil
    Bridge.pending_suppression_identity = nil
    Bridge.pending_suppression_pickup = nil
    return nil
end

local function complete_pending_suppression(method)
    local row = Bridge.pending_suppression
    if not row then
        return
    end
    record_row(row, Bridge.pending_suppression_identity or method)
    Bridge.pending_suppression = nil
    Bridge.pending_suppression_identity = nil
    Bridge.pending_suppression_pickup = nil
    log("Suppressed vanilla pickup through " .. method)
end

local function observe_pickup_completed(context, result)
    local succeeded = unwrap(result)
    if succeeded == false then
        return
    end
    observe_pickup(context)
    if pending_suppression() then
        complete_pending_suppression("Pickup:OnTakePickupEndDelegate")
    end
end

local function observe_add_item(_context, item, ...)
    if pending_suppression() and suppress_inventory_item(item) then
        complete_pending_suppression("InventoryComponent:AddItem")
    end
    observe_call(_context, item, ...)
end

local function observe_add_item_by_class(_context, item_class, count, ...)
    if pending_suppression() and suppress_parameter(item_class) then
        pcall(function()
            count:set(1)
        end)
        complete_pending_suppression("InventoryComponent:AddItemByClass")
    end
    observe_call(_context, item_class, count, ...)
end

local function observe_add_item_by_data(_context, item_data, count, ...)
    if pending_suppression() and suppress_data_parameter(item_data) then
        pcall(function()
            count:set(1)
        end)
        complete_pending_suppression("InventoryComponent:AddItemByData")
    end
    observe_call(_context, item_data, count, ...)
end

local death_hooks = {
    "/Script/LOTF2.AnathemaPlayerCharacter:OnNotifyPlayerDeath",
    "/Script/LOTF2.AnathemaPlayerCharacter:OnLocalPlayerKilled",
    "/Game/Core/Characters/Player/AnathemaPlayerCharacter_BP.AnathemaPlayerCharacter_BP_C:OnLocalPlayerKilled",
}

local completion_hooks = {
    "/Script/LOTF2.HexFinishGameManager:OnCreditScreenEndedCallback",
}

local function register_hook(path, pre_callback, post_callback)
    if Bridge.hooks[path] then
        return true
    end
    local ok, pre_id, post_id = pcall(function()
        return RegisterHook(path, pre_callback, post_callback)
    end)
    if ok and pre_id then
        Bridge.hooks[path] = {pre_id, post_id}
        log("Hooked " .. path)
        return true
    end
    return false
end

local function lifecycle_hint(context, ...)
    local values = {}
    local function add(parameter)
        if #values >= 8 then
            return
        end
        local value = unwrap(parameter)
        local name = object_name(value)
        if name then
            table.insert(values, name)
        elseif type(value) == "number" or type(value) == "string" then
            table.insert(values, tostring(value))
        end
    end
    add(context)
    local owner = unwrap(context)
    if owner then
        for _, property in ipairs({
            "CurrentSaveGameSlot",
            "CurrentSaveGameIndex",
            "CurrentSaveSlot",
            "CurrentSlotIndex",
            "SelectedSaveSlot",
            "SaveGameSlot",
            "SaveSlotName",
        }) do
            local ok, value = pcall(function()
                return owner[property]
            end)
            value = ok and unwrap(value) or nil
            if type(value) == "number" and value >= 0 and value <= 99 then
                table.insert(values, string.format("Save%02d.sav", value))
                break
            elseif type(value) == "string" and value ~= "" then
                table.insert(values, value)
                break
            end
        end
    end
    for index = 1, select("#", ...) do
        add(select(index, ...))
    end
    local hint = table.concat(values, "|")
    if #hint > 512 then
        hint = string.sub(hint, 1, 512)
    end
    return hint
end

local function report_loaded(reason, context, ...)
    if not Bridge.ready or not Bridge.session then
        return
    end
    Bridge.load_epoch = Bridge.load_epoch + 1
    Bridge.grants = {}
    Bridge.restores = {}
    Bridge.active_recovery = nil
    Bridge.active_cursor = 0
    Protocol.emit(
        "LOADED",
        Bridge.session,
        Bridge.boot_id,
        Bridge.load_epoch,
        reason,
        lifecycle_hint(context, ...),
        State.granted_cursor_for_session(Bridge.session)
    )
    log("Detected game-save load epoch " .. tostring(Bridge.load_epoch) .. " (" .. tostring(reason) .. ")")
end

local function report_saved(context, ...)
    if Bridge.ready and Bridge.session then
        Protocol.emit(
            "SAVED",
            Bridge.session,
            Bridge.boot_id,
            Bridge.load_epoch,
            Bridge.active_cursor,
            lifecycle_hint(context, ...)
        )
    end
end

local load_hooks = {
    "/Script/LOTF2.LOTF2SaveGameManager:LoadGame",
    "/Script/LOTF2.LOTF2SaveGameManager:LoadGameFromCurrentSaveGameObject",
    "/Script/LOTF2.LOTF2SaveGameManager:LoadGameFromLastSavedSlot",
}

local save_hooks = {
    "/Script/LOTF2.LOTF2SaveGameManager:SaveGameAsync",
    "/Script/LOTF2.LOTF2SaveGameManager:SaveGameSync",
    "/Script/LOTF2.LOTF2SaveGameManager:SaveGameToSlot_Async",
    "/Script/LOTF2.LOTF2SaveGameManager:SaveGameToSlot_Sync",
}

local function presentation_for_context(context)
    if Bridge.icon_lookup_depth > 0 then
        return nil
    end
    local value = unwrap(context)
    local name = object_name(value)
    if not name then
        return nil
    end
    local _marker, row = marker_in_name(name)
    if Bridge.pending_presentation and now_ms() <= Bridge.presentation_expires_ms then
        -- GUID-backed pickups are changed to the harmless replacement item.
        -- Scripted key/quest checks may retain their vanilla object when that
        -- shuffle is disabled, but their pickup UI must still identify the
        -- generated Archipelago placement rather than the safety item.
        if string.find(name, "ITM_CON_VigorStone_01", 1, true)
            or (row and row.location == Bridge.pending_presentation_location) then
            return Bridge.pending_presentation
        end
    end
    if row and row.shop then
        return presentation_for_row(row)
    end
    return nil
end

local function archipelago_icon()
    if Bridge.archipelago_icon and Bridge.archipelago_icon:IsValid() then
        return Bridge.archipelago_icon
    end
    if Bridge.icon_load_attempted then
        return nil
    end
    Bridge.icon_load_attempted = true
    local ok, texture = pcall(function()
        local directories = IterateGameDirectories()
        local binaries = directories.Game.Binaries.Win64.__absolute_path
        local library = StaticFindObject("/Script/Engine.Default__KismetRenderingLibrary")
        local world_context = FindFirstOf("AnathemaPlayerCharacter_BP_C")
        if not library or not library:IsValid() or not world_context or not world_context:IsValid() then
            return nil
        end
        local paths = {
            binaries .. "\\ue4ss\\Mods\\LotFArchipelago\\Assets\\archipelago.png",
            binaries .. "\\Mods\\LotFArchipelago\\Assets\\archipelago.png",
        }
        for _, path in ipairs(paths) do
            local loaded, icon = pcall(function()
                return library:ImportFileAsTexture2D(world_context, path)
            end)
            if loaded and icon and icon:IsValid() then
                return icon
            end
        end
        return nil
    end)
    if ok and texture and texture:IsValid() then
        Bridge.archipelago_icon = texture
        log("Loaded the Archipelago item icon")
        return texture
    end
    report_error("Could not load Assets\\archipelago.png; foreign items will use the fallback icon")
    return nil
end

local function icon_for_presentation(presentation, hd)
    if not presentation then
        return nil
    end
    if presentation.same_game then
        local row = Bridge.items[tostring(presentation.item_id)]
        if row then
            local item_class = find_class(row.asset)
            if item_class then
                local ok, icon = pcall(function()
                    Bridge.icon_lookup_depth = Bridge.icon_lookup_depth + 1
                    local item_data = item_class:GetDefaultObject()
                    local value
                    if hd then
                        value = item_data:GetHDIcon()
                    else
                        value = item_data:GetItemIcon()
                    end
                    Bridge.icon_lookup_depth = Bridge.icon_lookup_depth - 1
                    return value
                end)
                Bridge.icon_lookup_depth = 0
                if ok and icon then
                    return icon
                end
            end
        end
    end
    return archipelago_icon()
end

local function original_text_for_presentation(presentation, method)
    if not presentation or not presentation.same_game then
        return nil
    end
    local row = Bridge.items[tostring(presentation.item_id)]
    if not row then
        return nil
    end
    local item_class = find_class(row.asset)
    if not item_class then
        return nil
    end
    local ok, value = pcall(function()
        Bridge.icon_lookup_depth = Bridge.icon_lookup_depth + 1
        local item_data = item_class:GetDefaultObject()
        local text = item_data[method](item_data)
        Bridge.icon_lookup_depth = Bridge.icon_lookup_depth - 1
        return text
    end)
    Bridge.icon_lookup_depth = 0
    return ok and value or nil
end

local function register_presentation_hooks()
    register_hook("/Script/LOTF2.ItemData:GetItemName", function(context)
        local presentation = presentation_for_context(context)
        if presentation and presentation.title ~= "" then
            return presentation.title
        end
    end)
    for _, function_name in ipairs({"GetItemDescription", "GetItemShortDescription"}) do
        register_hook("/Script/LOTF2.ItemData:" .. function_name, function(context)
            local presentation = presentation_for_context(context)
            if presentation and presentation.description ~= "" then
                return presentation.description
            end
            return original_text_for_presentation(presentation, function_name)
        end)
    end
    register_hook("/Script/LOTF2.ItemData:GetItemIcon", function(context)
        return icon_for_presentation(presentation_for_context(context), false)
    end)
    register_hook("/Script/LOTF2.ItemData:GetHDIcon", function(context)
        return icon_for_presentation(presentation_for_context(context), true)
    end)
end

local function register_hooks()
    register_pickup_notifications()
    register_presentation_hooks()
    register_hook("/Script/LOTF2.Pickup:TryTakePickup", observe_pickup)
    register_hook("/Script/LOTF2.Pickup:OnTakePickupEndDelegate", observe_pickup_completed)
    register_hook("/Script/LOTF2.InteractionComponent:NotifyOnInteractionActivate", observe_interaction)
    register_hook("/Script/LOTF2.InteractionComponent:OnInteractionActivate", observe_interaction)
    register_hook("/Script/LOTF2.AnathemaItemContainer:TryOpenInteraction", observe_call)
    register_hook("/Script/LOTF2.AnathemaItemContainer:AddItemToInventory", observe_call)
    register_hook("/Script/LOTF2.InventoryComponent:AddItem", observe_add_item)
    register_hook("/Script/LOTF2.InventoryComponent:OnItemAdded", observe_add_item)
    register_hook("/Script/LOTF2.InventoryComponent:AddItemByClass", observe_add_item_by_class)
    register_hook("/Script/LOTF2.InventoryComponent:AddItemByData", observe_add_item_by_data)
    register_hook(
        "/Game/Core/Characters/Player/AnathemaPlayerCharacter_BP.AnathemaPlayerCharacter_BP_C:OnItemAddedToInventory",
        observe_call
    )
    if Bridge.death_link then
        for _, path in ipairs(death_hooks) do
            register_hook(path, function()
                if Bridge.ready and Bridge.death_link and Bridge.session and now_ms() - Bridge.last_death_ms >= 5000 then
                    Bridge.last_death_ms = now_ms()
                    Protocol.emit("DEATH", Bridge.session, 0)
                end
            end)
        end
    end
    if Bridge.goal == 0 then
        for _, path in ipairs(completion_hooks) do
            register_hook(path, function()
                if Bridge.ready and Bridge.session and Bridge.goal == 0 and not Bridge.goal_reported then
                    Bridge.goal_reported = true
                    Protocol.emit("GOAL", Bridge.session)
                    log("Any Ending goal completed after the credits sequence")
                end
            end)
        end
    end
    for _, path in ipairs(load_hooks) do
        if path == "/Script/LOTF2.LOTF2SaveGameManager:LoadGame" then
            register_hook(path, function() end, function(context, slot_index, ...)
                local slot = unwrap(slot_index)
                local hint = type(slot) == "number" and string.format("Save%02d.sav", slot) or ""
                report_loaded("save_manager", context, hint, slot_index, ...)
            end)
        else
            register_hook(path, function() end, function(context, ...)
                report_loaded("save_manager", context, ...)
            end)
        end
    end
    for _, path in ipairs(save_hooks) do
        register_hook(path, function() end, function(context, ...)
            report_saved(context, ...)
        end)
    end
end

local function player_character()
    local names = {
        "AnathemaPlayerCharacter_BP_C",
        "AnathemaPlayerCharacter",
        "HexPlayerCharacter",
    }
    for _, name in ipairs(names) do
        local player = FindFirstOf(name)
        if player and player:IsValid() then
            return player
        end
    end
    return nil
end

local function inventory_for(player)
    local ok, inventory = pcall(function()
        return player:GetInventoryComponent()
    end)
    if ok and inventory and inventory:IsValid() then
        return inventory
    end
    return nil
end

local function numeric_value(value)
    value = unwrap(value)
    if type(value) == "number" then
        return math.max(0, math.floor(value))
    end
    return tonumber(value)
end

local function inventory_count(item_id)
    local row = Bridge.items[tostring(item_id)]
    if not row then
        return nil, "item is not mapped"
    end
    local item_class = find_class(row.asset)
    if not item_class then
        return nil, "item asset could not be loaded"
    end
    local player = player_character()
    local inventory = player and inventory_for(player) or nil
    if not inventory then
        return nil, "player inventory is not ready"
    end

    local ok, inventory_item = pcall(function()
        return inventory.GetInventoryItemFromClass(inventory, item_class)
    end)
    if not ok then
        ok, inventory_item = pcall(function()
            local item_data = item_class:GetDefaultObject()
            return inventory.GetInventoryItemFromItemData(inventory, item_data)
        end)
    end
    if not ok then
        return nil, "inventory lookup functions are unavailable"
    end
    inventory_item = unwrap(inventory_item)
    if not inventory_item then
        return 0, "ok"
    end
    local valid_ok, is_valid = pcall(function()
        return inventory_item:IsValid()
    end)
    if not valid_ok or not is_valid then
        return 0, "ok"
    end

    for _, method in ipairs({"GetFullStock", "GetUsableStock"}) do
        local count_ok, count = pcall(function()
            return inventory_item[method](inventory_item)
        end)
        count = count_ok and numeric_value(count) or nil
        if count then
            return count, "ok"
        end
    end
    for _, property in ipairs({"FullStock", "Stock", "Quantity", "StackCount", "UsableStock"}) do
        local count_ok, count = pcall(function()
            return inventory_item[property]
        end)
        count = count_ok and numeric_value(count) or nil
        if count then
            return count, "ok"
        end
    end
    return nil, "inventory item stock could not be read"
end

local function emit_inventory_snapshot(request_id)
    local count = 0
    for item_id, _ in pairs(Bridge.items) do
        local quantity, status = inventory_count(tonumber(item_id))
        Protocol.emit(
            "COUNT",
            Bridge.session,
            request_id,
            item_id,
            quantity == nil and -1 or quantity,
            status
        )
        count = count + 1
    end
    Protocol.emit(
        "COUNT_END",
        Bridge.session,
        request_id,
        Bridge.boot_id,
        Bridge.load_epoch,
        Bridge.active_cursor,
        count
    )
end

local function call_grant(target, item_class, quantity)
    if not target then
        return false
    end
    local item_data = item_class
    pcall(function()
        item_data = item_class:GetDefaultObject()
    end)
    local methods = {
        {name = "AddItemToInventory", argument = item_class},
        {name = "DEBUG_SeverAddInventoryItem", argument = item_class},
        {name = "AddItemByClass", argument = item_class},
        {name = "AddItemByData", argument = item_data},
    }
    for _, method in ipairs(methods) do
        local ok = pcall(function()
            target[method.name](target, method.argument, quantity)
        end)
        if ok then
            return true
        end
    end
    return false
end

local function call_grant_and_measure(item_id, player, inventory, item_class, quantity, before)
    local attempted = call_grant(player, item_class, quantity)
    local after, reason = inventory_count(item_id)
    if after ~= nil and after > before then
        return true, after, reason
    end
    if attempted then
        -- A successful reflected call can still apply on a later game tick.
        -- Never invoke a second target until a subsequent audit proves no
        -- mutation occurred; doing so could duplicate a delayed grant.
        return true, after, reason
    end
    attempted = call_grant(inventory, item_class, quantity) or attempted
    after, reason = inventory_count(item_id)
    return attempted, after, reason
end

local function acknowledge_grant(index, item_id, quantity, detail)
    State.mark_granted(Bridge.session, index)
    if index >= Bridge.active_cursor then
        Bridge.active_cursor = index + 1
    end
    Protocol.emit("ACK", Bridge.session, "GRANT", index, item_id, quantity, detail)
end

local function grant_item(index, grant)
    local item_id = grant.item_id
    local row = Bridge.items[tostring(item_id)]
    if not row then
        report_error("No game asset is mapped for AP item " .. tostring(item_id))
        return false
    end
    local item_class = find_class(row.asset)
    if not item_class then
        report_error("Could not load item asset " .. tostring(row.asset))
        return false
    end
    local player = player_character()
    if not player then
        return false
    end
    local inventory = inventory_for(player)
    local before, count_reason = inventory_count(item_id)
    if before == nil then
        report_error(
            "Item delivery paused for AP item " .. tostring(item_id) .. ": " .. tostring(count_reason)
            .. "; refusing a blind duplicate-prone grant"
        )
        return false
    end
    if row.unique and before > 0 then
        acknowledge_grant(index, item_id, 0, "unique_already_present")
        log("Did not duplicate unique AP item " .. tostring(item_id) .. " at index " .. tostring(index))
        return true
    end
    if not grant.expected then
        grant.expected = before + row.quantity
    end
    local quantity = math.max(0, grant.expected - before)
    if quantity == 0 then
        acknowledge_grant(index, item_id, 0, grant.invoked and "delayed_grant_verified" or "already_present")
        return true
    end
    if grant.invoked then
        report_error(
            "Item delivery remains unverified for AP item " .. tostring(item_id)
            .. "; automatic mutation retry is paused to prevent a duplicate. Use /resync after checking the inventory."
        )
        return false
    end
    local attempted, after, after_reason = call_grant_and_measure(
        item_id, player, inventory, item_class, quantity, before
    )
    if attempted then
        grant.invoked = true
        if after == nil then
            report_error("Item grant could not be verified: " .. tostring(after_reason))
            return false
        end
        if after < grant.expected then
            report_error(
                "Item grant was only partially applied for AP item " .. tostring(item_id)
                .. " (expected " .. tostring(grant.expected) .. ", observed " .. tostring(after)
                .. "); automatic mutation retry is paused to prevent a duplicate"
            )
            return false
        end
        acknowledge_grant(index, item_id, after - before, "verified")
        log(
            "Granted AP item " .. tostring(item_id) .. " at index " .. tostring(index)
            .. " (observed " .. tostring(before) .. " -> " .. tostring(after) .. ")"
        )
        return true
    end
    report_error("The installed build exposes no supported item-grant function")
    return false
end

local function restore_item(recovery_id, item_id, requested, expected)
    local dedupe_key = tostring(recovery_id) .. ":" .. tostring(item_id)
    if Bridge.restored_ids[dedupe_key] then
        Protocol.emit("ACK", Bridge.session, "RESTORE", recovery_id, item_id, 0, "duplicate")
        return true
    end
    local before, reason = inventory_count(item_id)
    if before == nil then
        report_error(
            "Recovery paused for AP item " .. tostring(item_id) .. ": " .. tostring(reason)
            .. "; refusing a blind duplicate-prone grant"
        )
        return false
    end
    local quantity = math.min(math.max(0, requested), math.max(0, expected - before))
    if quantity == 0 then
        Bridge.restored_ids[dedupe_key] = true
        Protocol.emit("ACK", Bridge.session, "RESTORE", recovery_id, item_id, 0, before, before)
        return true
    end
    if Bridge.restore_invoked[dedupe_key] then
        report_error(
            "Recovery remains unverified for AP item " .. tostring(item_id)
            .. "; automatic mutation retry is paused to prevent a duplicate. Use /resync after checking the inventory."
        )
        return false
    end
    local row = Bridge.items[tostring(item_id)]
    local item_class = row and find_class(row.asset) or nil
    local player = player_character()
    local inventory = player and inventory_for(player) or nil
    if not row or not item_class or not player then
        return false
    end
    local attempted, after, after_reason = call_grant_and_measure(
        item_id, player, inventory, item_class, quantity, before
    )
    if attempted then
        Bridge.restore_invoked[dedupe_key] = true
        if after == nil then
            report_error("Recovery grant could not be verified: " .. tostring(after_reason))
            return false
        end
        if after < expected then
            report_error(
                "Recovery grant was only partially applied for AP item " .. tostring(item_id)
                .. " (expected " .. tostring(expected) .. ", observed " .. tostring(after)
                .. "); automatic mutation retry is paused to prevent a duplicate"
            )
            return false
        end
        Bridge.restored_ids[dedupe_key] = true
        Protocol.emit("ACK", Bridge.session, "RESTORE", recovery_id, item_id, quantity, before, after)
        log(
            "Recovery restored " .. tostring(quantity) .. " of AP item " .. tostring(item_id)
            .. " (observed " .. tostring(before) .. " -> " .. tostring(after) .. ")"
        )
        return true
    end
    report_error("The installed build exposes no supported recovery item-grant function")
    return false
end

local function apply_kill(event_id)
    if State.is_kill_applied(Bridge.session, event_id) then
        return true
    end
    local player = player_character()
    if not player then
        return false
    end
    local methods = {"Suicide", "ServerSuicide", "Client_PlayerKilled", "Kill"}
    for _, method in ipairs(methods) do
        local ok = pcall(function()
            player[method](player)
        end)
        if ok then
            State.mark_kill_applied(Bridge.session, event_id)
            Protocol.emit("ACK", Bridge.session, "KILL", event_id)
            return true
        end
    end
    report_error("DeathLink was received, but no supported player-kill function is exposed")
    return false
end

local function process_record(fields)
    local verb = fields[1]
    if verb == "RESET" then
        local protocol_version = tonumber(fields[2])
        local session = fields[3]
        if protocol_version ~= Bridge.protocol_version then
            local message = "Protocol mismatch: client " .. tostring(protocol_version)
                .. ", mod " .. tostring(Bridge.protocol_version)
            reset(nil)
            print("[LotF AP] ERROR: " .. message .. "\n")
            Protocol.emit("ERROR", session, message)
            return
        end
        reset(session)
        Protocol.emit("HELLO", Bridge.session, Bridge.version, Bridge.protocol_version, Bridge.boot_id)
        return
    end
    if not Bridge.session or fields[2] ~= Bridge.session then
        return
    end
    if verb == "MARK" then
        local row = {
            location = tonumber(fields[3]),
            suppress = fields[5] == "1",
            shop = fields[6] == "1",
            guid = fields[7],
            retail_row = fields[8],
        }
        Bridge.markers[fields[4]] = row
        local guid = normalize_guid(fields[7])
        if guid then
            Bridge.pickup_guids[guid] = row
        end
    elseif verb == "ITEM" then
        Bridge.items[fields[3]] = {
            asset = fields[4],
            quantity = tonumber(fields[5]) or 1,
            name = fields[6] or ("AP item " .. tostring(fields[3])),
            unique = fields[7] == "1",
        }
    elseif verb == "PLACE" then
        Bridge.placements[fields[3]] = {
            recipient = tonumber(fields[4]),
            player = fields[5],
            game = fields[6],
            item_id = tonumber(fields[7]),
            title = fields[8],
            own = fields[9] == "1",
            same_game = fields[10] == "1",
            description = fields[11] or "",
        }
    elseif verb == "CHECKED" then
        local location = tonumber(fields[3])
        Bridge.server_checked[location] = true
        State.mark_checked(Bridge.session, location)
    elseif verb == "OPTIONS" then
        Bridge.death_link = (tonumber(fields[3]) or 0) ~= 0
        Bridge.delivery_delay = tonumber(fields[4]) or 1000
        Bridge.goal = tonumber(fields[5]) or 0
    elseif verb == "READY" then
        if not validate_item_assets() then
            return
        end
        Bridge.ready = true
        Protocol.emit("HELLO", Bridge.session, Bridge.version, Bridge.protocol_version, Bridge.boot_id)
        for _, location in ipairs(State.checked_for_session(Bridge.session)) do
            if not Bridge.server_checked[location] then
                Protocol.emit("CHECK", Bridge.session, location)
                log("Replayed locally durable check " .. tostring(location))
            end
        end
    elseif verb == "GRANT" then
        local index = tonumber(fields[3])
        if State.is_granted(Bridge.session, index) then
            if index >= Bridge.active_cursor then
                Bridge.active_cursor = index + 1
            end
            Protocol.emit("ACK", Bridge.session, "GRANT", index, fields[4], 0, "durable")
        else
            Bridge.grants[index] = {item_id = fields[4], expected = nil}
        end
    elseif verb == "BASELINE" then
        Bridge.active_recovery = fields[3]
        Bridge.active_cursor = tonumber(fields[4]) or 0
        Bridge.grants = {}
        Bridge.restores = {}
        Bridge.restored_ids = {}
        Bridge.restore_invoked = {}
        Protocol.emit("ACK", Bridge.session, "BASELINE", Bridge.active_recovery, Bridge.active_cursor)
    elseif verb == "AUDIT" then
        emit_inventory_snapshot(fields[3])
    elseif verb == "RESTORE" then
        local recovery_id = fields[3]
        local item_id = tonumber(fields[4])
        local dedupe_key = tostring(recovery_id) .. ":" .. tostring(item_id)
        Bridge.restores[dedupe_key] = {
            recovery_id = recovery_id,
            item_id = item_id,
            quantity = tonumber(fields[5]) or 0,
            expected = tonumber(fields[6]) or 0,
        }
    elseif verb == "COMMIT" then
        if fields[3] == Bridge.active_recovery then
            Bridge.active_cursor = tonumber(fields[4]) or Bridge.active_cursor
            for index = 0, Bridge.active_cursor - 1 do
                State.mark_granted(Bridge.session, index)
            end
            Protocol.emit("ACK", Bridge.session, "COMMIT", fields[3], Bridge.active_cursor)
            Bridge.active_recovery = nil
        end
    elseif verb == "KILL" then
        if not State.is_kill_applied(Bridge.session, fields[3]) then
            Bridge.kills[fields[3]] = true
        end
    elseif verb == "PING" then
        Protocol.emit("ACK", Bridge.session, "PING", now_ms())
    end
end

function Bridge.tick()
    Bridge.elapsed_ms = Bridge.elapsed_ms + 100
    for _, fields in ipairs(Protocol.poll()) do
        local ok, reason = pcall(process_record, fields)
        if not ok then
            report_error("Command processing failed: " .. tostring(reason))
        end
    end

    if now_ms() - Bridge.last_offline_attempt_ms >= 2000 then
        enforce_offline_mode()
        Bridge.last_offline_attempt_ms = now_ms()
    end

    if not Bridge.ready or not Bridge.session then
        return
    end
    if now_ms() - Bridge.last_hook_attempt_ms >= 2000 then
        register_hooks()
        Bridge.last_hook_attempt_ms = now_ms()
    end

    if now_ms() - Bridge.last_pickup_scan_ms >= 500 then
        prepare_loaded_pickups()
        Bridge.last_pickup_scan_ms = now_ms()
    end

    if Bridge.pending_presentation and now_ms() > Bridge.presentation_expires_ms then
        Bridge.pending_presentation = nil
        Bridge.pending_presentation_location = nil
    end
    if Bridge.pending_suppression and now_ms() > Bridge.suppression_expires_ms then
        report_error(
            "A randomized pickup was checked but its vanilla inventory mutation was not observed ("
            .. tostring(Bridge.pending_suppression.retail_row) .. ")"
        )
        Bridge.pending_suppression = nil
        Bridge.pending_suppression_identity = nil
    end

    local player = player_character()
    local player_name = object_name(player)
    if player_name and player_name ~= Bridge.last_player_name then
        Bridge.last_player_name = player_name
        report_loaded("player_ready", player)
    end

    if now_ms() - Bridge.last_grant_ms >= Bridge.delivery_delay then
        local restore_key = nil
        for key, _ in pairs(Bridge.restores) do
            if not restore_key or key < restore_key then
                restore_key = key
            end
        end
        if restore_key then
            local row = Bridge.restores[restore_key]
            Bridge.last_grant_ms = now_ms()
            local completed = false
            local ok, reason = pcall(function()
                completed = restore_item(row.recovery_id, row.item_id, row.quantity, row.expected)
            end)
            if not ok then
                report_error("Recovery delivery failed safely: " .. tostring(reason))
            elseif completed then
                Bridge.restores[restore_key] = nil
            end
            return
        end

        local first_index = nil
        for index, _ in pairs(Bridge.grants) do
            if not first_index or index < first_index then
                first_index = index
            end
        end
        if first_index and not Bridge.active_recovery then
            Bridge.last_grant_ms = now_ms()
            local completed = false
            local ok, reason = pcall(function()
                completed = grant_item(first_index, Bridge.grants[first_index])
            end)
            if not ok then
                report_error("Item delivery failed safely: " .. tostring(reason))
            elseif completed then
                Bridge.grants[first_index] = nil
            end
        end
    end

    for event_id, _ in pairs(Bridge.kills) do
        if apply_kill(event_id) then
            Bridge.kills[event_id] = nil
        end
        break
    end
end

return Bridge
