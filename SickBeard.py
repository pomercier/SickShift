#!/usr/bin/env python
#
# This file is part of SickShift.
#
# SickShift is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# SickShift is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with SickShift.  If not, see <http://www.gnu.org/licenses/>.

from time import sleep
import runpy
print(
    '--------------------------------------------------------------------------------------------------------------'
)
for _ in range(30, 0, -1):
    print(
        '2019 Jan: You can now run sickshift.py directly\n'
        '          (SickBeard.py now serves as a legacy convenience which prints this message on every startup)'
    )
    print(
        '--------------------------------------------------------------------------------------------------------------'
    )
    print(
        '2022 Nov: Nearly four years have passed, enough time for this `SickBeard.py` file to be deleted.\n'
        '          Starting SickShift with this `SickBeard.py` file is slower than using `sickshift.py`,\n'
        '(%02ds)     please change whatever starts SickShift to use the `sickshift.py` file instead.' % (_ * 2)
    )
    print(
        '--------------------------------------------------------------------------------------------------------------'
    )
    sleep(2)
runpy.run_module('sickshift', {'_legacy_sickbeard_runner': True}, '__main__')
