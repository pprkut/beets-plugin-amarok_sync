# Amarok metadata synchronization plugin for beets
#
# Copyright 2013 Heinz Wiesinger, Amsterdam, The Netherlands
# All rights reserved.
#
# Redistribution and use of this script, with or without modification, is
# permitted provided that the following conditions are met:
#
# 1. Redistributions of this script must retain the above copyright
#    notice, this list of conditions and the following disclaimer.
#
# THIS SOFTWARE IS PROVIDED BY THE AUTHOR ''AS IS'' AND ANY EXPRESS OR IMPLIED
# WARRANTIES, INCLUDING, BUT NOT LIMITED TO, THE IMPLIED WARRANTIES OF
# MERCHANTABILITY AND FITNESS FOR A PARTICULAR PURPOSE ARE DISCLAIMED. IN NO
# EVENT SHALL THE AUTHOR BE LIABLE FOR ANY DIRECT, INDIRECT, INCIDENTAL,
# SPECIAL, EXEMPLARY, OR CONSEQUENTIAL DAMAGES (INCLUDING, BUT NOT LIMITED TO,
# PROCUREMENT OF SUBSTITUTE GOODS OR SERVICES; LOSS OF USE, DATA, OR PROFITS;
# OR BUSINESS INTERRUPTION) HOWEVER CAUSED AND ON ANY THEORY OF LIABILITY,
# WHETHER IN CONTRACT, STRICT LIABILITY, OR TORT (INCLUDING NEGLIGENCE OR
# OTHERWISE) ARISING IN ANY WAY OUT OF THE USE OF THIS SOFTWARE, EVEN IF
# ADVISED OF THE POSSIBILITY OF SUCH DAMAGE.

"""Fetch metadata from an Amarok database and store it along other data in
your library.
"""

import logging
import MySQLdb

from beets import ui
from beets.plugins import BeetsPlugin
from beets.util import displayable_path

log = logging.getLogger('beets')

def get_amarok_data(item, db):
    """Get data from an Amarok database. We fetch rating and score as well as Amarok's
    unique id for the track to have more reliable syncing after the initial import.
    """

    if hasattr(item, 'amarok_uid') and item.amarok_uid:
        condition = "REPLACE(uniqueid, 'amarok-sqltrackuid://', '') = '%s'" % MySQLdb.escape_string(item.amarok_uid)
    else:
        condition = "REPLACE(CONCAT_WS('/',lastmountpoint, rpath), '/./', '/') = '%s'" % MySQLdb.escape_string(displayable_path(item.path))

    query = "SELECT REPLACE(uniqueid, 'amarok-sqltrackuid://', '') AS uniqueid, rating, score \
             FROM statistics \
                INNER JOIN urls ON statistics.url = urls.id \
                INNER JOIN devices ON devices.id = urls.deviceid \
            WHERE %s \
            LIMIT 1" % condition

    try:
        cursor = db.cursor()

        cursor.execute(query)

        row = cursor.fetchone()

    except MySQLdb.Error, e:
        log.error(u'Could not fetch metadata from amarok database: {0}'.format(e))
        row = (None, 0, 0)

    if row is None:
        log.info(u'Could not find entry for \'{0}\' in amarok database'.format(displayable_path(item.path)))
        row = (None, 0, 0)

    item.amarok_uid = row[0]

    if hasattr(item, 'rating') and item.rating and long(item.rating) != row[1]:
        ui.commands._showdiff('rating', item.rating, row[1])
    if hasattr(item, 'score') and item.score and float(item.score) != row[2]:
        ui.commands._showdiff('score', item.score, row[2])

    item.rating = row[1]
    item.score = row[2]

class AmarokSync(BeetsPlugin):
    def __init__(self):
        super(AmarokSync, self).__init__()
        self.import_stages = [self.stage]

    def commands(self):
        def resync(lib, opts, args):
            db = None

            try:
                db = MySQLdb.connect(
                    host=self.config['db_host'].get(),
                    user=self.config['db_user'].get(),
                    passwd=self.config['db_passwd'].get(),
                    db=self.config['db_database'].get(),
                    charset="utf8")

                for item in lib.items(ui.decargs(args)):
                    get_amarok_data(item, db)
                    item.store()

            except MySQLdb.Error, e:
                log.error(u'Could not connect to Amarok database: {0}'.format(e))

            finally:
                if (db):
                    db.close();

        amarok_sync = ui.Subcommand('amarok_sync', help='Update metadata from amarok')
        amarok_sync.func = resync

        return [amarok_sync]

    def stage(self, config, task):
        db = None

        try:
            db = MySQLdb.connect(
                host=self.config['db_host'].get(),
                user=self.config['db_user'].get(),
                passwd=self.config['db_passwd'].get(),
                db=self.config['db_database'].get(),
                charset="utf8")

            for item in task.imported_items():
                get_amarok_data(item, db)

        except MySQLdb.Error, e:
            log.error(u'Could not connect to Amarok database: {0}'.format(e))

        finally:
            if (db):
                db.close();
