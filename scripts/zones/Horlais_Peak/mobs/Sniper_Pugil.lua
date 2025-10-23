-----------------------------------
-- Area: Horlais Peak
--  Mob: Sniper Pugil
-- BCNM Fight: Shooting Fish
-----------------------------------

---@type TMobEntity
local entity = {}

entity.onMobSpawn = function(mob)
    mob:setBehavior(xi.behavior.STANDBACK)
    mob:setMobMod(xi.mobMod.STANDBACK_RANGE, 12)
    mob:setMobSkillAttack(2062) -- Will use Counterspore as their auto-attack.
    

end

entity.onMobFight = function(mob, target)  -- Archer Pugils attack Sniper Pugils target
    local archerPugilOne = GetMobByID(mob:getID() + 1)
    local archerPugilTwo = GetMobByID(mob:getID() + 2)
    local mobTarget = mob:getTarget()

    archerPugilOne:addEnmity(mobTarget, 30000, 30000)
    archerPugilTwo:addEnmity(mobTarget, 30000, 30000)
end

entity.onMobDeath = function(mob, player, optParams)
end

return entity