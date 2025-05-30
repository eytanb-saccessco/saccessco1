# saccessco/tests/extension/custom_channels_live_server_test_case.py
import os
from functools import partial
from daphne.testing import DaphneProcess
from django.contrib.staticfiles.handlers import ASGIStaticFilesHandler
from django.core.exceptions import ImproperlyConfigured
from django.db import connections, DEFAULT_DB_ALIAS
from django.test import TransactionTestCase # Inherit directly from a base TestCase
from django.test.utils import modify_settings
from channels.routing import get_default_application # For Daphne app discovery

class CustomChannelsLiveServerTestCase(TransactionTestCase):
    """
    A custom test case that mimics ChannelsLiveServerTestCase functionality
    by directly managing the Daphne server, thus avoiding the problematic
    _pre_setup call from Django's core TestCase.setUpClass.
    """
    host = "localhost"
    ProtocolServerProcess = DaphneProcess
    static_wrapper = ASGIStaticFilesHandler
    serve_static = True

    # Class-level attributes to store server process and port
    _port = None
    _server_process = None
    _live_server_modified_settings = None

    @classmethod
    def setUpClass(cls):
        # IMPORTANT: Do NOT call super().setUpClass() from TestCase/TransactionTestCase here.
        # This custom setUpClass takes full control to avoid the problematic chain.

        # 1. Check for in-memory databases (mimics _pre_setup logic)
        cls._check_in_memory_db()

        # 2. Modify ALLOWED_HOSTS (mimics _pre_setup logic)
        cls._live_server_modified_settings = modify_settings(
            ALLOWED_HOSTS={"append": cls.host}
        )
        cls._live_server_modified_settings.enable()

        # 3. Start the Daphne server process (mimics _pre_setup logic)
        # get_application_callable = partial(
        #     get_default_application, # This is the actual callable for your Channels app
        #     static_wrapper=cls.static_wrapper if cls.serve_static else None,
        # )

        # --- START OF FIX for TypeError: get_default_application() got an unexpected keyword argument 'static_wrapper' ---

        # 1. Get the base ASGI application (e.g., from settings.ASGI_APPLICATION)
        # This function does NOT take 'static_wrapper'
        base_asgi_application = get_default_application()

        # 2. Conditionally wrap the base application with static files handler
        final_asgi_application = base_asgi_application
        if cls.static_wrapper is not None and cls.serve_static:
            # ASGIStaticFilesHandler expects the application to wrap as its argument
            final_asgi_application = cls.static_wrapper(base_asgi_application)

        # 3. Create a factory function (or a simple lambda) that DaphneProcess can call
        # This function should take no arguments and return the final, wrapped application.
        # This replaces the role of the original 'make_application' function.
        def application_factory():
            return final_asgi_application

        # Pass this factory function to DaphneProcess
        cls._server_process = cls.ProtocolServerProcess(cls.host, application_factory)

        # --- END OF FIX ---

        # cls._server_process = cls.ProtocolServerProcess(cls.host, get_application_callable)
        cls._server_process.start()
        cls._server_process.ready.wait()
        cls._port = cls._server_process.port.value

        print(f"\nINFO: CustomChannelsLiveServerTestCase: Daphne server started at {cls.live_server_url}")

    @classmethod
    def tearDownClass(cls):
        # IMPORTANT: Do NOT call super().tearDownClass() from TestCase/TransactionTestCase here.
        # This custom tearDownClass takes full control of cleanup.

        # Terminate and join the server process
        if cls._server_process:
            cls._server_process.terminate()
            cls._server_process.join()
            print("INFO: CustomChannelsLiveServerTestCase: Daphne server terminated.")

        # Disable modified settings
        if cls._live_server_modified_settings:
            cls._live_server_modified_settings.disable()


    @classmethod
    def _check_in_memory_db(cls):
        # Determine if a file-based 'test' alias is properly configured
        test_alias_is_file_based = False
        if 'test' in connections:
            test_connection = connections['test']
            # A connection is in-memory if its name is ':memory:' or similar internal strings
            # We explicitly check that it's NOT in-memory if it's pointing to a file path
            if test_connection.vendor == "sqlite" and not test_connection.is_in_memory_db():
                test_alias_is_file_based = True

        # Iterate through all active database connections
        for connection in connections.all():
            # If this connection is an in-memory SQLite database
            if connection.vendor == "sqlite" and connection.is_in_memory_db():
                # Special case: If the in-memory database is the 'default' alias
                # AND we have confirmed that a separate, file-based 'test' alias exists,
                # then we can safely ignore this in-memory 'default'.
                # The LiveServer process will use the 'test' database.
                if connection.alias == 'default' and test_alias_is_file_based:
                    print(f"INFO: Allowing in-memory 'default' database during test setup as a file-based 'test' alias exists.")
                    continue # Skip this specific connection and check others

                # If any other in-memory database is found (e.g., 'test' is also in-memory,
                # or some other custom alias is unexpectedly in-memory), then raise the error.
                raise ImproperlyConfigured(
                    "CustomChannelsLiveServerTestCase cannot be used with in-memory databases. "
                    f"Found in-memory database for alias: '{connection.alias}'. "
                    "Please ensure all database aliases used during testing (especially 'default' and 'test') "
                    "are configured to use file-based databases."
                )
    @property
    def live_server_url(self):
        """Returns the URL of the running Daphne server."""
        # Note: _port is a class variable, so access it via cls in setUpClass,
        # but via self in an instance method like this property.
        return f"http://{self.host}:{self.__class__._port}"

    @property
    def live_server_ws_url(self):
        """Returns the WebSocket URL of the running Daphne server."""
        return f"ws://{self.host}:{self.__class__._port}"


    # You would then put your setUp and tearDown (instance methods) here as before.
    # These *should* call super().setUp() and super().tearDown() if you want
    # TransactionTestCase's database setup/teardown per test.
    def setUp(self):
        super().setUp() # Call TransactionTestCase's setUp (handles transactions)
        # Your Selenium driver setup goes here (as it did in your old abstract_extension_page_test.py)

    def tearDown(self):
        # Your Selenium driver teardown goes here
        super().tearDown() # Call TransactionTestCase's tearDown