import pytest

from webhooks.targets import ForbiddenTarget, check_target


@pytest.mark.parametrize(
    "url",
    [
        "http://127.0.0.1:8000/hook",
        "http://10.0.0.5/hook",
        "http://192.168.0.10/hook",
        "http://169.254.169.254/latest/meta-data",
        "http://[::1]/hook",
        "ftp://93.184.216.34/hook",
    ],
)
async def test_internal_or_odd_addresses_are_refused(url):
    with pytest.raises(ForbiddenTarget):
        await check_target(url)


async def test_public_addresses_are_accepted():
    await check_target("https://93.184.216.34/hook")


async def test_the_local_demo_can_reach_the_docker_network():
    await check_target("http://10.0.0.5/hook", allow_private=True)
