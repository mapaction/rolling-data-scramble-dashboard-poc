from mapy_rds_dashboard import __version__


def test_version():
    """It is the application version."""
    assert len(__version__) > 0
