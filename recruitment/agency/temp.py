import boto3

from botocore.exceptions import NoRegionError
from typing import Iterable
from typing import Optional
from unittest.mock import patch

from recruitment.agency import Broker
from recruitment.agency import Communicator as ActualCommunicator
from recruitment.agency import Config


class Communicator(ActualCommunicator):

    def __init__(
        self,
        config: Config,
        expected_payload: Optional[dict] = None,
        expected_args: Optional[Iterable] = None,
        expected_kwargs: Optional[dict] = None
    ):
        self.config = config
        self.response_provider = lambda: expected_payload or {}
        self.args_provider = lambda: expected_args or {}
        self.kwargs_provider = lambda: expected_kwargs or {}
        # below replease super() call; is copied from recruitment.agency.Communicator
        broker = Broker(config.service_name)
        for alias, method in broker.interface.items():
            try:
                client = boto3.client(
                    service_name=config.service_name,
                    endpoint_url=config.endpoint_url,
                    region_name=config.region_name,
                )
            except (ValueError, NoRegionError) as e:
                print('-->>>', e, e.__class__.__name__)
                raise Communicator.FailedToInstantiate(given=config, cause=e) from e
            except Exception as uncaught:
                print('==>>>', uncaught, uncaught.__class__.__name__)
                raise Communicator.FailedToInstantiate(given=config, cause=uncaught) from uncaught
            setattr(self, alias, getattr(client, method))

    def __enter__(self):
        self.patcher = patch('botocore.client.BaseClient._make_api_call')
        self.mock = self.patcher.start()
        self.mock.return_value = self.response_provider()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """Given a call signature for `botocore.client.BaseClient._make_api_call` as follows:
            def _make_api_call(self, operation_name, api_params):
                ...
        where, for example, operation_name and api_params could be:
            * GetLogEvents
            * {'logGroupName': ..., 'logStreamName': ...}
        """
        self.mock.assert_called_with(*self.args_provider(), **self.kwargs_provider())
        self.patcher.stop()
