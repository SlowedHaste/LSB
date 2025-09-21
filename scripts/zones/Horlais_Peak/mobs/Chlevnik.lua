-----------------------------------
-- Area: Horlais Peak
-- Mob: Chlevnik
-- KSNM99 : Horns of War

-- TODO : Update Howl to give 25% Attack instead of 15% - Update Meteor to 1.6 fTP + dINT * 3(!)
-----------------------------------
local entity = {}

entity.onMobSpawn = function(mob)
    mob:setAnimationSub(3)
    mob:setUnkillable(true)
    mob:setMod(xi.mod.TRIPLE_ATTACK, 5)
    mob:addMod(xi.mod.STUNRES, 90)
    mob:addMod(xi.mod.SLEEPRES, 90)
    mob:setMod(xi.mod.DELAY, -1000)
    mob:setMobMod(xi.mobMod.NO_MOVE, 0)
    mob:setMobMod(xi.mobMod.ADD_EFFECT, 1)
    mob:setTP(3000) -- opens fight with a skill
    mob:addListener("TAKE_DAMAGE", "CHLEVNIK_TAKE_DAMAGE", function(mobArg, amount, attacker, attackType, damageType)
        if amount >= mobArg:getHP() and mob:getLocalVar("control") == 0 then
            mob:setLocalVar("control", 1) -- Prevents multiple uses of meteor
            mob:setUnkillable(true)
            mob:setAutoAttackEnabled(false)
            mob:setMagicCastingEnabled(false)
            mob:setMobAbilityEnabled(false)
            mob:setLocalVar("Meteor", 1)
        end
    end)
end

entity.onMobEngaged = function(mob, target)
    mob:setLocalVar("delay", GetSystemTime() + 30)
end

entity.onMobFight = function(mob, target)
    if mob:getHPP() > 25 then
        mob:setMod(xi.mod.REGAIN, 80)
    else
        mob:setMod(xi.mod.REGAIN, 50)
    end

    local delay = mob:getLocalVar("delay")
    if GetSystemTime() > delay then -- Cooldown on Meteor is 30 seconds.
        mob:castSpell(218, target) -- Meteor
        mob:setLocalVar("delay", GetSystemTime() + 30)
    end

    if mob:getLocalVar("Meteor") == 1 then
        if mob:checkDistance(target) > 40 then
            mob:resetEnmity(target)
        else
            mob:setLocalVar("Meteor", 2)
            mob:useMobAbility(634) -- Final Meteor
            mob:setLocalVar("FM_Check", GetSystemTime() + 10)
        end
    end

    --Delayed Check to see if Final Meteor was cast, if not retry
    if mob:getLocalVar("Meteor") == 2 then
        local checkBy = mob:getLocalVar("FM_Check")
        if checkBy > 0 and GetSystemTime() >= checkBy then
            if mob:getLocalVar("FM_Done") == 0 then
                -- Final Meteor didn't go off; try again next tick
                mob:setLocalVar("Meteor", 1)
            end
            mob:setLocalVar("FM_Check", 0)
        end
    end
end

entity.onAdditionalEffect = function(mob, target, damage)
    return xi.mob.onAddEffect(mob, target, damage, xi.mob.ae.STUN, { power = math.random(5, 10), chance = 25 }) -- 25% chance to stun for 5-10 seconds.
end

entity.onMobWeaponSkill = function(target, mob, skill)
    if skill:getID() == 634 then -- Final Meteor
        mob:setMobMod(xi.mobMod.NO_MOVE, 1)
        mob:setAnimationSub(1)
        mob:setLocalVar("FM_Done", 1)
        mob:timer(7000, function(mobArg)
            mobArg:setMagicCastingEnabled(true)
            mobArg:setAutoAttackEnabled(true)
            mobArg:setMobAbilityEnabled(true)
            mobArg:setUnkillable(false)
            mobArg:setHP(0)
        end)
    end
end

entity.onSpellPrecast = function(mob, spell)
    if spell:getID() == 218 then
        spell:setAoE(xi.magic.aoe.RADIAL)
        spell:setFlag(xi.magic.spellFlag.HIT_ALL)
        spell:setRadius(30)
        spell:setAnimation(280)
        spell:setMPCost(0)
    end
end

entity.onMobDeath = function(mob, player, optParams)
    mob:removeListener("CHLEVNIK_TAKE_DAMAGE")
end

return entity