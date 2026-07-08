"""Allow: python -m usb_daq_v20"""

import sys

from .list_cards import main

sys.exit(main())
