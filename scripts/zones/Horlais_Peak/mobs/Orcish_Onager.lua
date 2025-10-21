---@type TMobEntity
local entity = {}

local points =
{
    {
        { -396, 94, -65 }, { -390, 94, -76 }, { -409, 84, -70 }, { -383, 94, -59 }, { -401, 94, -51 }, -- Arena
        { -415, 94, -68 }, { -420, 94, -55 }, { -410, 94, -40 }, { -385, 94, -47 }, { -375, 94, -66 }, -- Arena
        { -378, 98, -106 }, { -373, 100, -114 }, { -368, 102, -120 }, { -360, 104, -127 }, { -349, 106, -130 }, -- Ramp
        { -339, 108, -127 }, { -330, 110, -120 }, { -321, 111, -108 }, { -314, 113, -97 }, { -309, 115, -85 }, -- Ramp
        { -307, 116, -72 }, { -310, 118, -59 }, { -318, 118, -43 }, { -328, 119, -30 }, { -340, 119, -21 }, -- Ramp
        { -352, 120, -20 }, { -365, 120, -25 }, { -377, 120, -30 }, { -395, 118, -27 }, { -416, 118, -27 }, -- Ramp

    },
    {
        { -156, -25, 115.5 }, { -150, -26, 103.3 }, { -168, -25, 108.8 }, { -143, -25, 120.5 }, { -161, -26, 128.6 },
        { -175, -25, 115.9 }, { -170, -25, 134.2 }, { -145, -25, 133.7 }, { -132, -25, 122.0 }, { -137, -25, 107.8 },
    },
    {
        { 83.8, -145, 295.5 }, { 89.4, -146, 283.0 }, { 71.6, -146, 288.5 }, { 96.7, -146, 300.6 }, { 78.4, -146, 308.1 },
        { 102.2, -146, 292.3 }, { 92.5, -146, 310.4 }, { 66.9, -146, 299.2 }, { 75.3, -146, 278.5 }, { 86.8, -146, 316.8 },
    },
}

entity.onMobInitialize = function(mob)
    mob:addImmunity(xi.immunity.BIND)
    mob:addImmunity(xi.immunity.TERROR)
end

entity.onMobSpawn = function(mob)
        mob:setMobMod(xi.mod.UFASTCAST, 50)
        mob:setMod(xi.mobMod.RUN_SPEED_MULT, 200)
    mob:setMod(xi.mod.BLACK_MAGIC_RECAST, 50)
    mob:setMod(xi.mobMod.NO_STANDBACK, 1)
end

entity.onMobFight = function(mob, target)
    local battlefield = mob:getBattlefield()
    if not battlefield then
        return
    end

    -- Check to see if any players or pets are bound, if so set anyoneBound to true.
    local bfNum = battlefield:getArea()
    local bindCast = mob:getLocalVar('bindCast')
    local pos = mob:getPos()
    local anyoneBound = false
    local mobHPP = mob:getHPP()
    local now = os.time()
    local last = mob:getLocalVar('lastBindCast')

    for _, player in pairs(battlefield:getPlayers()) do
        if player:hasStatusEffect(xi.effect.BIND)
        or (player:hasPet() and player:getPet():hasStatusEffect(xi.effect.BIND)) then
            anyoneBound = true
            break
        end
    end

    -- If anyone is bound, set standback behavior.
    if anyoneBound then
        mob:setBehavior(xi.behavior.STANDBACK)
        if mobHPP > 50 then
            mob:setMod(xi.mod.REGAIN, 1000)
        elseif mobHPP > 25 then
            mob:setMod(xi.mod.REGAIN, 667)
        elseif mobHPP > 0 then
            mob:setMod(xi.mod.REGAIN, 334)
        end
        -- Check to see if bind was cast, if so, fetch points and calculate their distances.
        if bindCast == 1 then
            local pointSet = points[bfNum]
            if pointSet then
                local distances = {}
                for i, p in ipairs(pointSet) do
                    local dx, dy, dz = p[1] - pos.x, p[2] - pos.y, p[3] - pos.z
                    distances[#distances + 1] = { index = i, dist = dx * dx + dy * dy + dz * dz }
                end

                -- Once distances are calculated, sort them.
                table.sort(distances, function(a, b) return a.dist < b.dist end)

                -- After sorting, choose the second closest point.
                if #distances >= 2 then
                    local dest = pointSet[distances[2].index]
                    mob:pathTo(dest[1], dest[2], dest[3], xi.path.flag.PATH)
                end
            end
        end
        mob:setLocalVar('bindCast', 0)
    else
        mob:setBehavior(xi.behavior.NONE)
        mob:setMod(xi.mod.REGAIN, 0)
    end

    if last == 0 then mob:setLocalVar('lastBindCast', now) last = now end
    if (now - last) >= 30 and not anyoneBound then
        mob:castSpell(xi.magic.spell.BINDGA, target)
        mob:setLocalVar('bindCast', 1)
        mob:setLocalVar('lastBindCast', now)
    end
end

entity.onMobDeath = function(mob, player, optParams)
end

return entity
