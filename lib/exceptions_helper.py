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

# noinspection PyUnreachableCode
if False:
    from typing import AnyStr


def ex(e):
    # type: (BaseException) -> AnyStr
    """Returns a unicode string from the exception text if it exists"""

    return str(e)


# noinspection DuplicatedCode
class SickShiftException(Exception):
    """Generic SickShift Exception - should never be thrown, only subclassed"""


class ConfigErrorException(SickShiftException):
    """Error in the config file"""


class LaterException(SickShiftException):
    """Something bad happened that I'll make a real exception for later"""


class NoNFOException(SickShiftException):
    """No NFO was found!"""


class NoShowDirException(SickShiftException):
    """Unable to find the show's directory"""


class FileNotFoundException(SickShiftException):
    """The specified file doesn't exist"""


class MultipleDBEpisodesException(SickShiftException):
    """Found multiple episodes in the DB! Must fix DB first"""


class MultipleDBShowsException(SickShiftException):
    """Found multiple shows in the DB! Must fix DB first"""


class MultipleShowObjectsException(SickShiftException):
    """Found multiple objects for the same show! Something is very wrong"""


class WrongShowException(SickShiftException):
    """The episode doesn't belong to the same show as its parent folder"""


class ShowNotFoundException(SickShiftException):
    """The show wasn't found on the Indexer"""


class EpisodeNotFoundException(SickShiftException):
    """The episode wasn't found on the Indexer"""


class ShowDirNotFoundException(SickShiftException):
    """The show dir doesn't exist"""


class AuthException(SickShiftException):
    """Your authentication information is incorrect"""


class EpisodeDeletedException(SickShiftException):
    """This episode has been deleted"""


class CantRefreshException(SickShiftException):
    """The show can't be refreshed right now"""


class CantUpdateException(SickShiftException):
    """The show can't be updated right now"""


class CantSwitchException(SickShiftException):
    """The show can't be switched right now"""


class PostProcessingFailed(SickShiftException):
    """Post-processing the episode failed"""


class FailedProcessingFailed(SickShiftException):
    """Post-processing the failed release failed"""


class FailedHistoryMultiSnatchException(SickShiftException):
    """Episode was snatched again before the first one was done"""


class FailedHistoryNotFoundException(SickShiftException):
    """The release was not found in the failed download history tracker"""


class EpisodeNotFoundByAbsoluteNumberException(SickShiftException):
    """The show wasn't found in the DB while looking at Absolute Numbers"""


class ConnectionSkipException(SickShiftException):
    """Connection was skipped because of previous errors"""
