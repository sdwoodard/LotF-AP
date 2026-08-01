local State = {}

local data_root = os.getenv("LOTF_AP_GAME_DATA_DIR")
if not data_root or data_root == "" then
    local local_app_data = os.getenv("LOCALAPPDATA")
    if not local_app_data or local_app_data == "" then
        error("LOTF_AP_GAME_DATA_DIR and LOCALAPPDATA are unavailable; LotF Archipelago cannot create durable state")
    end
    data_root = local_app_data .. "\\LotFArchipelago"
end
State.root = data_root
State.path = State.root .. "\\state.txt"
State.checked = {}
State.granted = {}
State.kills = {}

os.execute('if not exist "' .. State.root .. '" mkdir "' .. State.root .. '"')

local function key(session, value)
    return tostring(session) .. ":" .. tostring(value)
end

local function load()
    local stream = io.open(State.path, "rb")
    if not stream then
        return
    end
    local size = stream:seek("end") or 0
    if size > 16 * 1024 * 1024 then
        stream:close()
        print("[LotF AP] state.txt exceeds 16 MiB; refusing to load potentially corrupt state\n")
        return
    end
    stream:seek("set", 0)
    for line in stream:lines() do
        if #line <= 4096 then
        local kind, session, value = string.match(line, "^(%u+)\t([^\t]+)\t([^\t]+)$")
        if kind and session and value then
            if kind == "CHECK" then
                State.checked[key(session, value)] = true
            elseif kind == "GRANT" then
                State.granted[key(session, value)] = true
            elseif kind == "KILL" then
                State.kills[key(session, value)] = true
            end
        end
        end
    end
    stream:close()
end

local function append(kind, session, value)
    local stream = io.open(State.path, "ab")
    if not stream then
        print("[LotF AP] Cannot append durable state " .. tostring(kind) .. "\n")
        return false
    end
    stream:write(kind, "\t", tostring(session), "\t", tostring(value), "\n")
    stream:flush()
    stream:close()
    return true
end

function State.is_checked(session, location)
    return State.checked[key(session, location)] == true
end

function State.mark_checked(session, location)
    local id = key(session, location)
    if State.checked[id] then
        return
    end
    State.checked[id] = true
    append("CHECK", session, location)
end

function State.checked_for_session(session)
    local prefix = tostring(session) .. ":"
    local locations = {}
    for id, _ in pairs(State.checked) do
        if string.sub(id, 1, #prefix) == prefix then
            local location = tonumber(string.sub(id, #prefix + 1))
            if location then
                table.insert(locations, location)
            end
        end
    end
    table.sort(locations)
    return locations
end

function State.is_granted(session, index)
    return State.granted[key(session, index)] == true
end

function State.mark_granted(session, index)
    local id = key(session, index)
    if State.granted[id] then
        return
    end
    State.granted[id] = true
    append("GRANT", session, index)
end

function State.granted_cursor_for_session(session)
    local cursor = 0
    while State.is_granted(session, cursor) do
        cursor = cursor + 1
    end
    return cursor
end

function State.is_kill_applied(session, event_id)
    return State.kills[key(session, event_id)] == true
end

function State.mark_kill_applied(session, event_id)
    local id = key(session, event_id)
    if State.kills[id] then
        return
    end
    State.kills[id] = true
    append("KILL", session, event_id)
end

load()
return State
