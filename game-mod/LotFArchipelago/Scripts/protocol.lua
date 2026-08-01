local Protocol = {}

local data_root = os.getenv("LOTF_AP_GAME_DATA_DIR")
if not data_root or data_root == "" then
    local local_app_data = os.getenv("LOCALAPPDATA")
    if not local_app_data or local_app_data == "" then
        error("LOTF_AP_GAME_DATA_DIR and LOCALAPPDATA are unavailable; LotF Archipelago cannot create its bridge")
    end
    data_root = local_app_data .. "\\LotFArchipelago"
end

Protocol.root = data_root .. "\\bridge"
Protocol.commands_path = Protocol.root .. "\\commands.txt"
Protocol.events_path = Protocol.root .. "\\events.txt"
Protocol.command_offset = 0
Protocol.partial_line = ""
Protocol.max_record_bytes = 65536
Protocol.max_records_per_poll = 2048

os.execute('if not exist "' .. Protocol.root .. '" mkdir "' .. Protocol.root .. '"')

local function percent_encode(value)
    return (tostring(value):gsub("([^%w%-%._/:])", function(char)
        return string.format("%%%02X", string.byte(char))
    end))
end

local function percent_decode(value)
    return (value:gsub("%%(%x%x)", function(hex)
        return string.char(tonumber(hex, 16))
    end))
end

local function split_tabs(line)
    local fields = {}
    local start = 1
    while true do
        local position = string.find(line, "\t", start, true)
        if not position then
            table.insert(fields, percent_decode(string.sub(line, start)))
            break
        end
        table.insert(fields, percent_decode(string.sub(line, start, position - 1)))
        start = position + 1
    end
    return fields
end

function Protocol.emit(verb, ...)
    local fields = {verb}
    for index = 1, select("#", ...) do
        table.insert(fields, percent_encode(select(index, ...)))
    end
    local record = table.concat(fields, "\t") .. "\n"
    if #record > Protocol.max_record_bytes then
        print("[LotF AP] Refusing oversized bridge event " .. tostring(verb) .. "\n")
        return false
    end
    local stream, reason = io.open(Protocol.events_path, "ab")
    if not stream then
        print("[LotF AP] Cannot open events file: " .. tostring(reason) .. "\n")
        return false
    end
    stream:write(record)
    stream:flush()
    stream:close()
    return true
end

function Protocol.poll()
    local stream = io.open(Protocol.commands_path, "rb")
    if not stream then
        return {}
    end
    local size = stream:seek("end") or 0
    if size < Protocol.command_offset then
        Protocol.command_offset = 0
        Protocol.partial_line = ""
    end
    stream:seek("set", Protocol.command_offset)
    local payload = stream:read("*a") or ""
    Protocol.command_offset = stream:seek() or size
    stream:close()

    payload = Protocol.partial_line .. payload
    local records = {}
    local start = 1
    while true do
        local newline = string.find(payload, "\n", start, true)
        if not newline then
            Protocol.partial_line = string.sub(payload, start)
            if #Protocol.partial_line > Protocol.max_record_bytes then
                Protocol.partial_line = ""
                Protocol.emit("MALFORMED", "none", "oversized incomplete command record")
            end
            break
        end
        local line = string.gsub(string.sub(payload, start, newline - 1), "\r$", "")
        if #line > Protocol.max_record_bytes then
            Protocol.emit("MALFORMED", "none", "oversized command record")
        elseif line ~= "" and #records < Protocol.max_records_per_poll then
            table.insert(records, split_tabs(line))
        end
        start = newline + 1
    end
    return records
end

return Protocol
