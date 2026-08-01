local Bridge = require("bridge")

print("[LotF AP] Lords of the Fallen Archipelago mod " .. Bridge.version .. " loaded\n")

if LoopInGameThreadWithDelay then
    LoopInGameThreadWithDelay(100, function()
        Bridge.tick()
    end)
else
    LoopAsync(100, function()
        ExecuteInGameThread(function()
            Bridge.tick()
        end)
        return false
    end)
end

