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


class RecentSearcher(Job):
    def __init__(self):
        super(RecentSearcher, self).__init__(self.job_run, kwargs={}, thread_lock=True)

    def job_run(self):

        recentsearch_queue_item = sickshift.search_queue.RecentSearchQueueItem()
        sickshift.search_queue_scheduler.action.add_item(recentsearch_queue_item)
