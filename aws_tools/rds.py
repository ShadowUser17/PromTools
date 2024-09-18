import common


# https://boto3.amazonaws.com/v1/documentation/api/latest/reference/services/rds.html
class RDS(common.API):
    def __init__(self) -> None:
        super().__init__('rds')

    def __repr__(self) -> str:
        tmp = [' '.join(item.values()) for item in self.items]
        return '\n'.join(tmp)

    def load_items(self) -> None:
        response = self.client.describe_db_instances()
        for item in response['DBInstances']:
            self.items.append({
                'id': item['DBInstanceIdentifier'],
                'class': item['DBInstanceClass']
            })
