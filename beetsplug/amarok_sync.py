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

import logging
import MySQLdb

from beets.plugins import BeetsPlugin
from beets.util import displayable_path

log = logging.getLogger('beets')

def get_amarok_data(item, db):
    query = "SELECT REPLACE(uniqueid, 'amarok-sqltrackuid://', '') AS uniqueid, rating, score \
             FROM statistics \
                INNER JOIN urls ON statistics.url = urls.id \
                INNER JOIN devices ON devices.id = urls.deviceid \
            WHERE REPLACE(CONCAT_WS('/',lastmountpoint, rpath), '/./', '/') = '%s' \
            LIMIT 1" % displayable_path(item.path)

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

    print(displayable_path(item.path))
    item.amarok_uid = row[0]
    item.rating = row[1]
    item.score = row[2]


class AmarokSync(BeetsPlugin):
    def __init__(self):
        super(AmarokSync, self).__init__()
        self.import_stages = [self.stage]

    def stage(self, config, task):
        print('Amarok sync on import!')

        db = None

        try:
            db = MySQLdb.connect(
                host=self.config['db_host'].get(),
                user=self.config['db_user'].get(),
                passwd=self.config['db_passwd'].get(),
                db=self.config['db_database'].get())

            for item in task.imported_items():
                get_amarok_data(item, db)
                print(item.amarok_uid)
                print(item.rating)

        except MySQLdb.Error, e:
            log.error(u'Could not connect to Amarok database: {0}'.format(e))

        finally:
            if (db):
                db.close();
