#!/usr/bin/env python
# Licensed to Cloudera, Inc. under one
# or more contributor license agreements.  See the NOTICE file
# distributed with this work for additional information
# regarding copyright ownership.  Cloudera, Inc. licenses this file
# to you under the Apache License, Version 2.0 (the
# "License"); you may not use this file except in compliance
# with the License.  You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

import logging
from datetime import datetime,  timedelta

from django.core.management.base import BaseCommand

from beeswax.models import Session
from beeswax.server import dbms


LOG = logging.getLogger(__name__)


class Command(BaseCommand):
  """
  Close HiveServer2 sessions.

  e.g.
  build/env/bin/hue close_sessions 7 all
  Closing (all=True) queries older than 7 days...
  0 queries closed.
  """
  args = '<age_in_days> (default is 7)'
  help = 'Close finished Hive queries older than 7 days.'

  def handle(self, *args, **options):
    days = int(args[0]) if len(args) >= 1 else 7
    close_all = args[1] == 'all' if len(args) >= 2 else False

    self.stdout.write('Closing (all=%s) HiveServer2 sessions older than %s days...\n' % (close_all, days))

    n = 0
    sessions = Session.objects.all()

    if not close_all:
      sessions = sessions.filter(application='beeswax')

    sessions = sessions.filter(last_used__lte=datetime.today() - timedelta(days=days))

    import os
    import beeswax
    from beeswax import conf
    from beeswax import hive_site
    try:
      beeswax.conf.HIVE_CONF_DIR.set_for_testing(os.environ['HIVE_CONF_DIR'])
    except:
      LOG.exception('failed to lookup HIVE_CONF_DIR in environment')
      self.stdout.write('Did you export HIVE_CONF_DIR=/etc/hive/conf?\n')
      raise

    hive_site.reset()
    hive_site.get_conf()

    for session in sessions:
      try:
        resp = dbms.get(user=session.owner).close_session(session)
        if not 'Session does not exist!' in str(resp):
          self.stdout.write('Info: %s\n' % resp)
          n += 1
      except Exception, e:
        if not 'Session does not exist!' in str(e):
          self.stdout.write('Info: %s\n' % e)

    self.stdout.write('%s sessions closed.\n' % n)
