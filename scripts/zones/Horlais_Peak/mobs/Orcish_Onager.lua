-----------------------------------
-- Area: Horlais Peak
--  Mob: Orcish Onager
-- BCNM: Shots in the Dark
-----------------------------------
---@type TMobEntity
local entity = {}

entity.onMobInitialize = function(mob)
    mob:addImmunity(xi.immunity.BIND)
    mob:addImmunity(xi.immunity.TERROR)
end

entity.onMobSpawn = function(mob)
    mob:setMobMod(xi.mobMod.MAGIC_COOL, 30)
    mob:setMobMod(xi.mod.UFASTCAST, 50)
    mob:setMod(xi.mobMod.RUN_SPEED_MULT, 200)
    mob:setMod(xi.mod.BLACK_MAGIC_RECAST, 50)
    mob:setMod(xi.mobMod.NO_STANDBACK, 1)
end

entity.onMobFight = function(mob, target)
end

entity.onMobDeath = function(mob, player, optParams)
end

return entity
