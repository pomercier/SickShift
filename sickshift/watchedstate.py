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

import sickshift
from .scheduler import Job
from sickshift import watchedstate_queue


class WatchedStateUpdater(Job):
    def __init__(self, name, queue_item):
        super(WatchedStateUpdater, self).__init__(self.job_run, silent=True, kwargs={}, thread_lock=True)

        self.name = name
        self.queue_item = queue_item

    @property
    def prevent_run(self):
        return sickshift.watched_state_queue_scheduler.action.is_in_queue(self.queue_item)

    @staticmethod
    def is_enabled():
        return True

    def job_run(self):
        # noinspection PyUnresolvedReferences
        if self.is_enabled():
            new_item = self.queue_item()
            sickshift.watched_state_queue_scheduler.action.add_item(new_item)


class EmbyWatchedStateUpdater(WatchedStateUpdater):

    def __init__(self):
        super(EmbyWatchedStateUpdater, self).__init__('Emby', watchedstate_queue.EmbyWatchedStateQueueItem)

    @staticmethod
    def is_enabled():
        return sickshift.USE_EMBY and sickshift.EMBY_WATCHEDSTATE_SCHEDULED


class PlexWatchedStateUpdater(WatchedStateUpdater):

    def __init__(self):
        super(PlexWatchedStateUpdater, self).__init__('Plex', watchedstate_queue.PlexWatchedStateQueueItem)

    @staticmethod
    def is_enabled():
        return sickshift.USE_PLEX and sickshift.PLEX_WATCHEDSTATE_SCHEDULED
