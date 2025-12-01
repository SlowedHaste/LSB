/*
===========================================================================

  Copyright (c) 2010-2015 Darkstar Dev Teams

  This program is free software: you can redistribute it and/or modify
  it under the terms of the GNU General Public License as published by
  the Free Software Foundation, either version 3 of the License, or
  (at your option) any later version.

  This program is distributed in the hope that it will be useful,
  but WITHOUT ANY WARRANTY; without even the implied warranty of
  MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
  GNU General Public License for more details.

  You should have received a copy of the GNU General Public License
  along with this program.  If not, see http://www.gnu.org/licenses/

===========================================================================
*/

#ifndef _MOBSKILL_PARAM_H
#define _MOBSKILL_PARAM_H

#include <string>
#include <cstdint>
#include <unordered_map>
#include <variant>

using MobSkillParamValue = std::variant<double, int64_t, bool, std::string>;
using MobSkillParamMap   = std::unordered_map<std::string, MobSkillParamValue>;

#endif // _MOBSKILL_PARAM_H
