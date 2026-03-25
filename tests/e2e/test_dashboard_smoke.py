"""E2E tests for Dashboard smoke test (L6)."""

import sys
from unittest.mock import MagicMock, patch


class TestDashboardSmoke:
    """Test all Dashboard pages can load without exceptions.

    Implements L6: E2E Dashboard smoke test.
    Note: Uses module import verification since Streamlit AppTest requires
    the streamlit package which may not be installed in test environments.
    """

    def _mock_streamlit_and_pandas(self):
        """Set up mocks for streamlit and pandas."""
        mock_st = MagicMock()
        mock_pd = MagicMock()
        sys.modules['streamlit'] = mock_st
        sys.modules['pandas'] = mock_pd

    def _cleanup_mocks(self):
        """Clean up mocked modules."""
        for mod in ['streamlit', 'pandas']:
            if mod in sys.modules:
                del sys.modules[mod]

    def test_dashboard_module_imports(self):
        """Test that dashboard module can be imported."""
        self._mock_streamlit_and_pandas()

        try:
            from src.dashboard import app
            assert app is not None
        finally:
            self._cleanup_mocks()

    def test_all_page_functions_exist(self):
        """Test that all page functions are defined and callable."""
        self._mock_streamlit_and_pandas()

        try:
            from src.dashboard import app

            # List of expected page functions
            page_functions = [
                'overview_page',
                'knowledge_browser_page',
                'memory_viewer_page',
                'query_traces_page',
                'quality_page',
                'evaluation_panel_page',
                'audit_logs_page',
            ]

            for page_name in page_functions:
                assert hasattr(app, page_name), f"Missing page function: {page_name}"
                func = getattr(app, page_name)
                assert callable(func), f"Page function is not callable: {page_name}"
        finally:
            self._cleanup_mocks()

    def test_page_functions_have_proper_signatures(self):
        """Test that page functions have proper signatures (no required params)."""
        self._mock_streamlit_and_pandas()

        try:
            from src.dashboard import app

            # All page functions should take no required arguments
            page_functions = [
                app.overview_page,
                app.knowledge_browser_page,
                app.memory_viewer_page,
                app.query_traces_page,
                app.quality_page,
                app.evaluation_panel_page,
                app.audit_logs_page,
            ]

            for func in page_functions:
                # Page functions should be callable with no arguments
                import inspect
                sig = inspect.signature(func)
                required_params = [
                    p for p in sig.parameters.values()
                    if p.default == inspect.Parameter.empty
                    and p.kind != inspect.Parameter.VAR_KEYWORD
                    and p.kind != inspect.Parameter.VAR_POSITIONAL
                ]
                # Allow self parameter for methods, but no other required params
                param_names = [p.name for p in required_params if p.name != 'self']
                assert len(param_names) == 0, f"{func.__name__} has required params: {param_names}"
        finally:
            self._cleanup_mocks()

    def test_main_function_exists(self):
        """Test that main entry point function exists."""
        self._mock_streamlit_and_pandas()

        try:
            from src.dashboard import app
            assert hasattr(app, 'main')
            assert callable(app.main)
        finally:
            self._cleanup_mocks()

    def test_app_config_is_called(self):
        """Test that app configuration is set up properly."""
        # Note: set_page_config is called at module level which is hard to test
        # without actually running streamlit. We verify the page title instead.
        self._mock_streamlit_and_pandas()

        try:
            from src.dashboard import app
            import inspect
            source = inspect.getsource(app)

            # Verify set_page_config is in the source with expected params
            assert "set_page_config" in source
            assert "MedPilot Dashboard" in source
        finally:
            self._cleanup_mocks()

    def test_sidebar_navigation_pages_match(self):
        """Test that sidebar navigation includes all expected pages."""
        self._mock_streamlit_and_pandas()

        try:
            from src.dashboard import app

            # Check main function code for expected page names in sidebar
            import inspect
            source = inspect.getsource(app.main)

            expected_pages = [
                "系统总览",
                "知识库浏览器",
                "记忆查看器",
                "问诊追踪",
                "知识库质量",
                "审计日志",
                "评估面板",
            ]

            for page in expected_pages:
                assert page in source, f"Page not found in navigation: {page}"
        finally:
            self._cleanup_mocks()
