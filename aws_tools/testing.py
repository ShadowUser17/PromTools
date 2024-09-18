import sys
import traceback

import rds


# AWS_DEFAULT_REGION
# AWS_PROFILE
# AWS_ACCESS_KEY_ID
# AWS_SECRET_ACCESS_KEY

try:
    rds_class = rds.RDS()
    rds_class.load_items()
    print(rds_class)

except Exception:
    traceback.print_exc()
    sys.exit(1)
