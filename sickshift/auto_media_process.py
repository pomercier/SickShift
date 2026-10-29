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

import os.path

import sickshift
from . import logger, processTV
from .scheduler import Job


class MediaProcess(Job):
    def __init__(self):
        super(MediaProcess, self).__init__(self.job_run, kwargs={})

    @staticmethod
    def is_enabled():
        return sickshift.PROCESS_AUTOMATICALLY

    def job_run(self):
        if self.is_enabled():
            self._main()

    @staticmethod
    def _main():

        if not os.path.isdir(sickshift.TV_DOWNLOAD_DIR):
            logger.error(f'Automatic media processing attempted but dir {sickshift.TV_DOWNLOAD_DIR} doesn\'t exist')
            return

        if not os.path.isabs(sickshift.TV_DOWNLOAD_DIR):
            logger.error('Automatic media processing attempted but dir %s is relative '
                         '(and probably not what you really want to process)' % sickshift.TV_DOWNLOAD_DIR)
            return

        processTV.process_dir(sickshift.TV_DOWNLOAD_DIR, is_basedir=True)
