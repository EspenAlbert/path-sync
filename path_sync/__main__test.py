from unittest.mock import patch

from path_sync.__main__ import main


def test_main_calls_app():
    with patch("path_sync.__main__.app") as app:
        main()
        app.assert_called_once()
