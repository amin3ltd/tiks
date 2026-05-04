#
# This file is part of pretix (Community Edition).
#
# Copyright (C) 2014-2020  Raphael Michel and contributors
# Copyright (C) 2020-today pretix GmbH and contributors
#
# This program is free software: you can redistribute it and/or modify it under the terms of the GNU Affero General
# Public License as published by the Free Software Foundation in version 3 of the License.
#
# ADDITIONAL TERMS APPLY: Pursuant to Section 7 of the GNU Affero General Public License, additional terms are
# applicable granting you additional permissions and placing additional restrictions on your usage of this software.
# Please refer to the pretix LICENSE file to obtain the full terms applicable to this work. If you did not receive
# this file, see <https://tiks.cc/about/en/license>.
#
# This program is distributed in the hope that it will be useful, but WITHOUT ANY WARRANTY; without even the implied
# warranty of MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the GNU Affero General Public License for more
# details.
#
# You should have received a copy of the GNU Affero General Public License along with this program.  If not, see
# <https://www.gnu.org/licenses/>.
#
import sys
from datetime import datetime

from django.conf import settings
from django.utils.safestring import mark_safe
from django.utils.translation import gettext


POWERED_BY_LINK = '<a href="https://tiks.cc" target="_blank" rel="noopener">{}</a>'


def get_powered_by(request, safelink=True):
    year = datetime.now().year
    if safelink:
        return gettext("© {} tickets. All rights reserved.").format(year)
    return POWERED_BY_LINK.format(gettext("ticketing powered by tiks"))


def contextprocessor(request):
    ctx = {
        'rtl': getattr(request, 'LANGUAGE_CODE', 'en') in settings.LANGUAGES_RTL,
        'poweredby': mark_safe(get_powered_by(request)),
    }
    if settings.DEBUG and 'runserver' not in sys.argv:
        ctx['debug_warning'] = True
    elif 'runserver' in sys.argv:
        ctx['development_warning'] = True

    return ctx
